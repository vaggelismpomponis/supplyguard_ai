"""Tests for the SupplyGuard AgentHarness (src/agent/eval_harness.py)."""

from __future__ import annotations

import uuid

from eval.dataset import load_examples
from eval.evaluators import evaluate
from eval.harness import AgentHarness, drive, payload_fingerprint
from src.agent.deep_agent import SupplyGuardOrchestrator
from src.agent.eval_harness import SupplyGuardEvalHarness, _normalize_payload, build_harness
from src.agent.schemas import DisruptionFact, OperationalImpact, build_approval_payload


def test_build_harness_satisfies_protocol():
    h = build_harness()
    assert isinstance(h, AgentHarness)


def test_eval_harness_golden_and_idempotency():
    h = SupplyGuardEvalHarness(orchestrator=SupplyGuardOrchestrator(use_postgres=False))
    examples = {e["metadata"]["id"]: e for e in load_examples()}
    golden = examples["EV-0001"]
    tid = f"test-harness-gold-{uuid.uuid4().hex[:8]}"

    drive(
        h,
        tid,
        golden["inputs"]["message"],
        user_id=golden["inputs"]["user_id"],
        approval_decision="approved",
    )
    # Replay decide should be a no-op
    assert h.decide(tid, approved=True) is None

    outcome = h.outcome(tid)
    results = evaluate(outcome, golden["outputs"])
    assert all(r["score"] == 1 for r in results), results
    assert len(outcome["executed_action_ids"]) == 1


def test_normalize_payload_includes_expedite_and_transfer_fees_in_total_cost():
    fact = DisruptionFact(supplier_id="S001", supplier_name="Atlas Components", component_id="MC-17", delay_days=12)
    impact = OperationalImpact()
    payload = build_approval_payload(fact, impact, quantity=3000)

    normalized = _normalize_payload(payload)
    assert normalized["po_subtotal_eur"] == 29400.0
    assert normalized["expedite_fee_eur"] == 882.0
    assert normalized["transfer_cost_eur"] == 96.0
    assert normalized["total_cost"] == 30378.0

    # Changing expedite fee alters total_cost and payload_fingerprint
    fp_base = payload_fingerprint(normalized)
    modified = dict(normalized, total_cost=30966.0, expedite_fee_eur=1470.0)
    assert payload_fingerprint(modified) != fp_base
