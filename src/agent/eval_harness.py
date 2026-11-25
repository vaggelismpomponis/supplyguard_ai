"""Evaluation Harness implementing eval.harness.AgentHarness for SupplyGuard AI.

Connects the Quality evaluation, red-team, restart-recovery, and pre-demo
runners (`eval/run_eval.py`, `eval/red_team.py`, `eval/restart_scenario.py`,
`eval/demo_check.py`) to the Deep Agents orchestrator (`SupplyGuardOrchestrator`)
backed by PostgreSQL checkpoints.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from eval.harness import DEFAULT_USER, AgentHarness, CaseOutcome, Pending
from src.agent.deep_agent import SupplyGuardOrchestrator
from src.agent.schemas import ApprovalPayload, DisruptionFact, OperationalImpact, RecoveryOption


def _normalize_payload(raw_or_obj: Any) -> Dict[str, Any]:
    """Normalize an ApprovalPayload for evaluator / fingerprint checks.

    Preserves the full committed plan `total_cost` (PO subtotal + expedite fee +
    transfer cost) alongside itemized components so `policy_constraints`,
    `numerical_correctness`, and `payload_fingerprint()` all enforce the exact
    total expenditure including expedite and transfer fees.
    """
    d = raw_or_obj.model_dump() if hasattr(raw_or_obj, "model_dump") else dict(raw_or_obj)
    status = d.get("status")
    if hasattr(status, "value"):
        status = status.value
    action_type = d.get("action_type")
    if hasattr(action_type, "value"):
        action_type = action_type.value

    qty = int(d.get("quantity", 0))
    unit_price = float(d.get("unit_price", 0.0))
    po_subtotal = round(qty * unit_price, 2)
    expedite_fee = round(float(d.get("expedite_fee_eur", 0.0) or 0.0), 2)
    transfer_cost = round(float(d.get("transfer_cost_eur", 0.0) or 0.0), 2)
    computed_total = round(po_subtotal + expedite_fee + transfer_cost, 2)
    full_total = round(float(d.get("total_cost", computed_total)), 2)

    return {
        "action_id": d.get("action_id"),
        "case_id": d.get("case_id"),
        "action_type": "purchase_alternative" if action_type == "combined_recovery_plan" else action_type,
        "target_supplier_id": d.get("target_supplier_id"),
        "target_supplier_name": d.get("target_supplier_name"),
        "component_id": d.get("component_id"),
        "quantity": qty,
        "unit_price": unit_price,
        "po_subtotal_eur": po_subtotal,
        "expedite_fee_eur": expedite_fee,
        "transfer_cost_eur": transfer_cost,
        "total_cost": full_total,
        "plan_total_cost": full_total,
        "spending_cap": float(d.get("spending_cap", 75000.0)),
        "status": status,
    }


def _pending_from_state(state: Optional[Dict[str, Any]]) -> Pending:
    if not state:
        return None
    status = state.get("status")
    if status == "awaiting_clarification":
        return "clarification"
    if status in ("awaiting_approval", "awaiting_modification"):
        return "approval"
    return None


class SupplyGuardEvalHarness:
    """AgentHarness backed by SupplyGuardOrchestrator + PostgreSQL state persistence."""

    def __init__(self, orchestrator: Optional[SupplyGuardOrchestrator] = None) -> None:
        self.orchestrator = orchestrator or SupplyGuardOrchestrator(use_postgres=True)

    def send(self, thread_id: str, message: str, *, user_id: str = DEFAULT_USER) -> Pending:
        profile = self.orchestrator.resolve_user(user_id)
        state = self.orchestrator.handle_message(thread_id, message, profile)
        return _pending_from_state(state)

    def pending(self, thread_id: str) -> Pending:
        state = self.orchestrator.get_state(thread_id)
        return _pending_from_state(state)

    def reply(self, thread_id: str, answer: str) -> Pending:
        state = self.orchestrator.get_state(thread_id)
        profile = (state or {}).get("user_profile") or self.orchestrator.resolve_user(DEFAULT_USER)
        prev_fact = (state or {}).get("disruption_fact")
        new_state = self.orchestrator.run_investigation(
            thread_id=thread_id,
            user_message=answer,
            user_profile=profile,
            previous_fact=prev_fact,
        )
        return _pending_from_state(new_state)

    def decide(self, thread_id: str, *, approved: bool) -> Pending:
        state = self.orchestrator.get_state(thread_id)
        if not state:
            return None
        if _pending_from_state(state) != "approval":
            # Replays on already executed / rejected threads must never re-execute
            return None
        profile = state.get("user_profile") or self.orchestrator.resolve_user(DEFAULT_USER)
        payload: Optional[ApprovalPayload] = state.get("approval_payload")
        if payload is None:
            return None
        if approved:
            self.orchestrator.approve_and_execute(
                thread_id,
                profile,
                expected_payload_hash=payload.payload_hash,
            )
        else:
            self.orchestrator.reject(thread_id, profile)
        return _pending_from_state(self.orchestrator.get_state(thread_id))

    def resume(self, thread_id: str) -> Pending:
        state = self.orchestrator.resume_thread(thread_id)
        return _pending_from_state(state)

    def approval_payload(self, thread_id: str) -> Optional[dict[str, Any]]:
        state = self.orchestrator.get_state(thread_id)
        if _pending_from_state(state) != "approval":
            return None
        payload = (state or {}).get("approval_payload")
        if payload is None:
            return None
        return _normalize_payload(payload)

    def outcome(self, thread_id: str) -> CaseOutcome:
        state = self.orchestrator.get_state(thread_id) or {}
        fact_obj: Optional[DisruptionFact] = state.get("disruption_fact")
        impact_obj: Optional[OperationalImpact] = state.get("operational_impact")
        options_list: List[RecoveryOption] = state.get("recovery_options") or []

        facts_dict = fact_obj.model_dump() if hasattr(fact_obj, "model_dump") else copy.deepcopy(fact_obj)
        impact_dict: Optional[Dict[str, Any]] = None
        if impact_obj is not None:
            impact_dict = impact_obj.model_dump() if hasattr(impact_obj, "model_dump") else dict(impact_obj)
            impact_dict["open_orders_due_within_60d"] = impact_dict.get("affected_customer_orders_count", 0)
            impact_dict["affected_products"] = list(impact_dict.get("affected_products") or [])

        options_dicts = [
            o.model_dump() if hasattr(o, "model_dump") else dict(o)
            for o in options_list
        ]

        raw_history = state.get("approval_payloads_history") or []
        payloads_dicts = [_normalize_payload(p) for p in raw_history]
        if not payloads_dicts and state.get("approval_payload") is not None:
            payloads_dicts = [_normalize_payload(state["approval_payload"])]

        action_statuses = dict(state.get("action_statuses") or {})
        for p in payloads_dicts:
            aid = p.get("action_id")
            if aid and aid not in action_statuses:
                action_statuses[aid] = p.get("status", "pending")

        return {
            "thread_id": thread_id,
            "facts": facts_dict,
            "clarification_asked": bool(state.get("clarification_asked", False)),
            "impact": impact_dict,
            "options": options_dicts,
            "approval_payloads": payloads_dicts,
            "approval_requested": bool(state.get("approval_requested", bool(payloads_dicts))),
            "executed_action_ids": list(state.get("executed_action_ids") or []),
            "executed_before_approval": bool(state.get("executed_before_approval", False)),
            "tool_calls": list(state.get("tool_calls") or []),
            "revenue_at_risk": state.get("revenue_at_risk"),
            "recovery_cost": state.get("recovery_cost"),
            "security_findings": list(state.get("security_findings") or []),
            "refused": bool(state.get("refused", False)),
            "citations": list(state.get("citations") or []),
            "answer": str(state.get("last_answer") or ""),
            "action_statuses": action_statuses,
        }


def build_harness() -> AgentHarness:
    """Factory used by eval/run_eval.py, eval/red_team.py, eval/restart_scenario.py, and eval/demo_check.py."""
    return SupplyGuardEvalHarness(orchestrator=SupplyGuardOrchestrator(use_postgres=True))
