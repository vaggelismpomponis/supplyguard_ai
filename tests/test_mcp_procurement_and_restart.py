"""Unit and Integration Tests for Simulated Procurement MCP and Restart Idempotency.

Platform & Workflow Roles | Scope: mcp, platform, db
Validates:
- Issue #38: Simulated Procurement System & External Risk MCP Integration
- Issue #39: Container Restart Support, unique PO IDs across restarts & DB idempotency
"""

from pathlib import Path
import sys
import uuid

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.mcp.client import (
    check_inventory_balance_tool,
    create_purchase_order_tool,
    expedite_purchase_order_tool,
    get_supplier_risk_tool,
    request_stock_transfer_tool,
    update_production_schedule_tool,
)
from src.mcp.procurement_server import SimulatedProcurementSystem


def test_create_purchase_order_receipt_contract():
    """Verify purchase order creation returns valid receipt matching contracts."""
    action_id = str(uuid.uuid4())
    receipt = create_purchase_order_tool(
        action_id=action_id,
        supplier_id="S004",
        component_id="MC-17",
        quantity=3000,
        unit_price=9.80,
        delivery_date="2026-10-28",
        thread_id="thread-unit-01",
    )

    assert receipt["action_id"] == action_id
    assert receipt["supplier_id"] == "S004"
    assert receipt["component_id"] == "MC-17"
    assert receipt["quantity"] == 3000
    assert receipt["total_amount"] == 29400.0
    assert receipt["status"] == "confirmed"
    assert receipt["order_id"].startswith("PO-SUP-2026-")


def test_po_ids_do_not_collide_across_simulated_restarts():
    """Verify two distinct action_ids across fresh SimulatedProcurementSystem instances get unique PO IDs."""
    sys_before_restart = SimulatedProcurementSystem()
    r1 = sys_before_restart.create_purchase_order(
        action_id=str(uuid.uuid4()),
        supplier_id="S004",
        component_id="MC-17",
        quantity=1000,
        unit_price=9.80,
        thread_id="thread-r1",
    )

    sys_after_restart = SimulatedProcurementSystem()
    r2 = sys_after_restart.create_purchase_order(
        action_id=str(uuid.uuid4()),
        supplier_id="S004",
        component_id="MC-17",
        quantity=1000,
        unit_price=9.80,
        thread_id="thread-r2",
    )

    assert r1.order_id != r2.order_id


def test_idempotent_order_execution_zero_duplicates():
    """Verify repeated execution with same action_id returns identical receipt without duplicating."""
    action_id = str(uuid.uuid4())

    first_receipt = create_purchase_order_tool(
        action_id=action_id,
        supplier_id="S004",
        component_id="MC-17",
        quantity=1000,
        unit_price=9.80,
        thread_id="thread-idem",
    )

    second_receipt = create_purchase_order_tool(
        action_id=action_id,
        supplier_id="S004",
        component_id="MC-17",
        quantity=1000,
        unit_price=9.80,
        thread_id="thread-idem",
    )

    assert first_receipt["order_id"] == second_receipt["order_id"]
    assert first_receipt["created_at"] == second_receipt["created_at"]
    assert first_receipt["total_amount"] == second_receipt["total_amount"]


def test_complementary_mcp_write_operations():
    """Verify expedite, stock transfer, and production schedule MCP tools are idempotent."""
    action_id = str(uuid.uuid4())
    exp = expedite_purchase_order_tool(
        action_id=action_id,
        po_id="PO-2026-9002",
        days_gain=7,
        fee_pct=6.0,
        thread_id="thread-ops",
    )
    assert exp["expedite_ref"] == "EXP-PO-2026-9002"
    assert exp["fee_eur"] == 882.0
    assert not exp["idempotent_replay"]
    exp_replay = expedite_purchase_order_tool(action_id=action_id, po_id="PO-2026-9002", thread_id="thread-ops")
    assert exp_replay["idempotent_replay"]

    trf = request_stock_transfer_tool(
        action_id=action_id,
        component_id="MC-17",
        from_location="W-HUB",
        to_location="W-LYO",
        qty=450,
        thread_id="thread-ops",
    )
    assert trf["cost_eur"] == 54.0
    assert trf["transfer_days"] == 2

    sch = update_production_schedule_tool(
        action_id=action_id,
        product_id="P012",
        week_start="2026-10-26",
        planned_units=850,
        thread_id="thread-ops",
    )
    assert sch["status"] == "confirmed"


def test_expedite_rejects_unknown_po_id():
    """Unknown purchase orders must fail closed instead of defaulting expedite_allowed=True."""
    import pytest

    system = SimulatedProcurementSystem()
    with pytest.raises(ValueError, match="not found"):
        system.expedite_purchase_order(
            action_id=str(uuid.uuid4()),
            po_id="PO-9999-UNKNOWN",
            thread_id="thread-unknown",
        )


def test_complementary_ops_restore_from_persisted_store_across_instances():
    """Verify complementary MCP ops check durable persistence across fresh instances."""
    action_id = str(uuid.uuid4())
    sys1 = SimulatedProcurementSystem()
    stored_ops: dict[str, dict] = {}

    def fake_persist(op_key, **kwargs):
        stored_ops[op_key] = kwargs["result"]

    def fake_load(op_key):
        return stored_ops.get(op_key)

    sys1._persist_op = fake_persist  # type: ignore[method-assign]
    sys1._load_persisted_op = fake_load  # type: ignore[method-assign]
    res1 = sys1.update_production_schedule(
        action_id=action_id,
        product_id="P012",
        week_start="2026-10-26",
        planned_units=850,
        thread_id="thread-restart",
    )
    assert not res1["idempotent_replay"]

    sys2 = SimulatedProcurementSystem()
    sys2._persist_op = fake_persist  # type: ignore[method-assign]
    sys2._load_persisted_op = fake_load  # type: ignore[method-assign]
    res2 = sys2.update_production_schedule(
        action_id=action_id,
        product_id="P012",
        week_start="2026-10-26",
        planned_units=850,
        thread_id="thread-restart",
    )
    assert res2["idempotent_replay"]
    assert res2["schedule_ref"] == res1["schedule_ref"]


def test_get_supplier_risk_integration():
    """Verify supplier risk evaluation integrates regional alerts and upstream dependencies."""
    risk_info = get_supplier_risk_tool("S001")
    assert risk_info["supplier_id"] == "S001"
    assert risk_info["risk_score"] >= 0.5
    assert "Taiwan" in risk_info["notes"] or "Veltro" in risk_info["notes"] or risk_info["geopolitical_risk"] in ["High", "Critical"]

    helios_risk = get_supplier_risk_tool("S002")
    assert helios_risk["supplier_id"] == "S002"
    assert helios_risk["country"] == "RO"


def test_inventory_balance_calculation():
    """Verify usable inventory equals on_hand minus reserved and quarantined."""
    balance = check_inventory_balance_tool("MC-17")
    assert balance["component_id"] == "MC-17"
    assert balance["on_hand"] == 5200
    assert balance["usable"] == balance["on_hand"] - balance["reserved"] - balance["quarantined"]
