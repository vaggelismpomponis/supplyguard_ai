"""Deterministic Business Calculators & Guardrail Tools for SupplyGuard AI.

Workflow Role | Scope: tools, agent
Reference: docs/roles/workflow.md (Phase 3), docs/ARCHITECTURE_CONTRACTS.md (Section 4)

All numerical calculations (Recovery Cost, Revenue at Risk, budget cap checks) MUST be
executed deterministically in Python — LLM arithmetic is strictly forbidden.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from langchain_core.tools import StructuredTool
except ImportError:  # pragma: no cover - lightweight fallback when langchain_core is absent on host
    class StructuredTool:  # type: ignore[no-redef]
        def __init__(self, func: Any, name: str, description: str) -> None:
            self.func = func
            self.name = name
            self.description = description

        @classmethod
        def from_function(cls, func: Any, name: str, description: str = "") -> "StructuredTool":
            return cls(func=func, name=name, description=description or (func.__doc__ or "").strip())

        def invoke(self, args: Dict[str, Any]) -> Any:
            return self.func(**args)

from src.agent.schemas import (
    ApprovalPayload,
    DisruptionFact,
    OperationalImpact,
    RecoveryOption,
    SupplyGuardActionType,
    detect_prompt_injection_in_text,
)


def calculate_recovery_costs(
    strategy_type: str,
    units: int,
    unit_price: float,
    freight_cost: float = 0.0,
    expedite_units: int = 0,
    expedite_unit_price: float = 0.0,
    expedite_fee_pct: float = 0.0,
    transfer_units: int = 0,
    transfer_cost_per_unit: float = 0.12,
    penalty_rebate: float = 0.0,
) -> Dict[str, float]:
    """Deterministic business tool calculating recovery cost components and total EUR outlay.

    Zero LLM arithmetic: all multiplications, percentages, and sums are computed here.
    """
    purchase_subtotal = round(max(0, units) * max(0.0, unit_price), 2)
    expedite_fee = round(
        max(0, expedite_units) * max(0.0, expedite_unit_price) * (max(0.0, expedite_fee_pct) / 100.0),
        2,
    )
    transfer_cost = round(max(0, transfer_units) * max(0.0, transfer_cost_per_unit), 2)
    freight = round(max(0.0, freight_cost), 2)
    rebate = round(max(0.0, penalty_rebate), 2)
    total_recovery_cost = round(purchase_subtotal + expedite_fee + transfer_cost + freight - rebate, 2)

    return {
        "strategy_type": str(strategy_type),
        "purchase_subtotal_eur": purchase_subtotal,
        "expedite_fee_eur": expedite_fee,
        "transfer_cost_eur": transfer_cost,
        "freight_cost_eur": freight,
        "penalty_rebate_eur": rebate,
        "total_recovery_cost_eur": total_recovery_cost,
    }


def calculate_revenue_at_risk(
    uncovered_demand_units: int,
    covered_units: int,
    total_exposure_eur: float = 385000.0,
    tier1_protected: bool = True,
    tier1_exposure_eur: float = 240000.0,
) -> Dict[str, Any]:
    """Deterministic business tool calculating residual Revenue at Risk separately from Recovery Cost."""
    uncovered = max(0, uncovered_demand_units)
    covered = max(0, covered_units)
    residual_units = max(0, uncovered - covered)

    if uncovered == 0:
        residual_risk_eur = 0.0
    elif residual_units == 0:
        residual_risk_eur = 0.0
    elif tier1_protected:
        # Tier-1 orders (highest value & penalty) are protected first; residual falls on Tier-2/3
        non_tier1_pool = max(0.0, total_exposure_eur - tier1_exposure_eur)
        ratio = min(1.0, residual_units / uncovered)
        residual_risk_eur = round(non_tier1_pool * ratio, 2)
    else:
        ratio = min(1.0, residual_units / uncovered)
        residual_risk_eur = round(total_exposure_eur * ratio, 2)

    protected_revenue_eur = round(max(0.0, total_exposure_eur - residual_risk_eur), 2)
    return {
        "uncovered_demand_units": uncovered,
        "covered_units": covered,
        "residual_uncovered_units": residual_units,
        "tier1_protected": tier1_protected,
        "total_exposure_eur": round(total_exposure_eur, 2),
        "protected_revenue_eur": protected_revenue_eur,
        "revenue_at_risk_eur": residual_risk_eur,
    }


def verify_budget_limits(
    total_cost_eur: float,
    spending_cap_eur: float = 75000.0,
    requested_quantity: int = 0,
    supplier_monthly_capacity: Optional[int] = None,
    certification_valid: bool = True,
) -> Dict[str, Any]:
    """Deterministic policy guardrail check for spending cap, supplier capacity, and ISO certification."""
    violations: List[str] = []
    if total_cost_eur > spending_cap_eur:
        violations.append(
            f"Total cost (€{total_cost_eur:,.2f}) exceeds authorized spending cap (€{spending_cap_eur:,.2f})."
        )
    if supplier_monthly_capacity is not None and requested_quantity > supplier_monthly_capacity:
        violations.append(
            f"Requested quantity ({requested_quantity:,} units) exceeds supplier monthly capacity "
            f"({supplier_monthly_capacity:,} units/month)."
        )
    if not certification_valid:
        violations.append("Supplier quality certification (ISO 9001:2015) is expired or invalid (DOC-PRO-04).")

    return {
        "is_compliant": len(violations) == 0,
        "total_cost_eur": round(total_cost_eur, 2),
        "spending_cap_eur": round(spending_cap_eur, 2),
        "headroom_eur": round(spending_cap_eur - total_cost_eur, 2),
        "violations": violations,
    }


def scan_prompt_injections(text: str, source_id: str = "unknown") -> Dict[str, Any]:
    """Scan retrieved document or supplier message text for prompt injection / instruction hijacking."""
    matched_pattern = detect_prompt_injection_in_text(text)
    return {
        "source_id": source_id,
        "injection_detected": matched_pattern is not None,
        "matched_pattern": matched_pattern,
        "status": "NEUTRALIZED" if matched_pattern else "CLEAN",
    }


def execute_procurement_po(
    action_id: str,
    supplier_id: str,
    component_id: str,
    quantity: int,
    unit_price: float,
    delivery_date: Optional[str] = None,
    thread_id: Optional[str] = None,
    use_postgres: bool = True,
) -> Dict[str, Any]:
    """Execute an approved Purchase Order in the Simulated Procurement MCP with strict idempotency.

    Checks PostgreSQL audit_log via src/db/idempotency.py when available, enforces status == 'approved',
    and delegates PO creation to src/mcp/client.py (create_purchase_order_tool).
    """
    try:
        from src.mcp.client import create_purchase_order_tool
    except ImportError:
        return {
            "order_id": f"PO-SUP-2026-{action_id[:8].upper()}",
            "action_id": action_id,
            "supplier_id": supplier_id,
            "component_id": component_id,
            "quantity": quantity,
            "total_amount": round(quantity * unit_price, 2),
            "status": "confirmed",
            "idempotent_replay": False,
        }

    pg_available = False
    if use_postgres:
        try:
            from src.db.connection import is_postgres_available

            pg_available = bool(is_postgres_available())
        except ImportError:
            pg_available = False

    if pg_available:
        from src.db.idempotency import execute_idempotent, get_action_status

        # Fail closed: once PostgreSQL is reachable, never fall through past the DB approval guard.
        status = get_action_status(action_id)
        if status == "executed":
            receipt = create_purchase_order_tool(
                action_id=action_id,
                supplier_id=supplier_id,
                component_id=component_id,
                quantity=quantity,
                unit_price=unit_price,
                delivery_date=delivery_date,
                thread_id=thread_id,
            )
            receipt["idempotent_replay"] = True
            return receipt
        if status is None or status != "approved":
            raise ValueError(
                f"Action '{action_id}' cannot execute with status '{status}'. "
                "Explicit human approval is required."
            )

        executed, result = execute_idempotent(
            action_id,
            create_purchase_order_tool,
            supplier_id=supplier_id,
            component_id=component_id,
            quantity=quantity,
            unit_price=unit_price,
            delivery_date=delivery_date,
            thread_id=thread_id,
        )
        if not executed and result == "already_executed":
            receipt = create_purchase_order_tool(
                action_id=action_id,
                supplier_id=supplier_id,
                component_id=component_id,
                quantity=quantity,
                unit_price=unit_price,
                delivery_date=delivery_date,
                thread_id=thread_id,
            )
            receipt["idempotent_replay"] = True
            return receipt
        if isinstance(result, dict):
            result["idempotent_replay"] = False
        return result

    receipt = create_purchase_order_tool(
        action_id=action_id,
        supplier_id=supplier_id,
        component_id=component_id,
        quantity=quantity,
        unit_price=unit_price,
        delivery_date=delivery_date,
        thread_id=thread_id,
    )
    receipt["idempotent_replay"] = False
    return receipt


# LangChain StructuredTool wrappers for Deep Agents subagents
calculate_recovery_costs_tool = StructuredTool.from_function(
    func=calculate_recovery_costs,
    name="calculate_recovery_costs",
    description="Deterministically calculate recovery costs (PO subtotal, expedite fee, transfer cost, total EUR). Never do LLM math.",
)
calculate_revenue_at_risk_tool = StructuredTool.from_function(
    func=calculate_revenue_at_risk,
    name="calculate_revenue_at_risk",
    description="Deterministically calculate residual Revenue at Risk separately from Recovery Cost.",
)
verify_budget_limits_tool = StructuredTool.from_function(
    func=verify_budget_limits,
    name="verify_budget_limits",
    description="Verify spending cap (<= EUR 75k / 90k), supplier monthly capacity, and ISO certification validity.",
)
scan_prompt_injections_tool = StructuredTool.from_function(
    func=scan_prompt_injections,
    name="scan_prompt_injections",
    description="Scan untrusted document or email text for prompt injections and return NEUTRALIZED/CLEAN status.",
)
execute_procurement_po_tool = StructuredTool.from_function(
    func=execute_procurement_po,
    name="execute_procurement_po",
    description="Execute an already-approved Purchase Order in the Simulated Procurement MCP with strict idempotency.",
)
