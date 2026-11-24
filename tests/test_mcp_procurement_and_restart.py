"""Unit and Integration Tests for Simulated Procurement MCP and Container Restart Idempotency.

Platform & Workflow Roles | Scope: mcp, platform, db
Validates:
- Issue #38: Simulated Procurement System & External Risk MCP Integration
- Issue #39: Container Restart Support & Checkpoint Persistence for Idempotency Test
"""

from pathlib import Path
import sys
import uuid
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.mcp.client import (
    check_inventory_balance_tool,
    create_purchase_order_tool,
    get_supplier_risk_tool,
)
from src.mcp.procurement_server import SimulatedProcurementSystem


def test_create_purchase_order_receipt_contract():
    """Verify purchase order creation returns valid receipt matching contracts."""
    action_id = str(uuid.uuid4())
    receipt = create_purchase_order_tool(
        action_id=action_id,
        supplier_id="S002",
        component_id="MC-17",
        quantity=2500,
        unit_price=8.50,
        delivery_date="2026-11-05",
    )

    assert receipt["action_id"] == action_id
    assert receipt["supplier_id"] == "S002"
    assert receipt["component_id"] == "MC-17"
    assert receipt["quantity"] == 2500
    assert receipt["total_amount"] == 21250.0
    assert receipt["status"] == "confirmed"
    assert receipt["order_id"].startswith("PO-SUP-")


def test_idempotent_order_execution_zero_duplicates():
    """Verify repeated execution with same action_id returns identical receipt without duplicating."""
    action_id = str(uuid.uuid4())

    first_receipt = create_purchase_order_tool(
        action_id=action_id,
        supplier_id="S002",
        component_id="MC-17",
        quantity=1000,
        unit_price=8.50,
    )

    # Simulate network retry or agent replay after container restart
    second_receipt = create_purchase_order_tool(
        action_id=action_id,
        supplier_id="S002",
        component_id="MC-17",
        quantity=1000,
        unit_price=8.50,
    )

    assert first_receipt["order_id"] == second_receipt["order_id"]
    assert first_receipt["created_at"] == second_receipt["created_at"]
    assert first_receipt["total_amount"] == second_receipt["total_amount"]


def test_get_supplier_risk_integration():
    """Verify supplier risk evaluation integrates regional alerts and upstream dependencies."""
    # Test Atlas Components (S001) which has upstream Taiwan wafer fab dependency
    risk_info = get_supplier_risk_tool("S001")
    assert risk_info["supplier_id"] == "S001"
    assert risk_info["risk_score"] >= 0.5
    assert "Taiwan" in risk_info["notes"] or "Veltro" in risk_info["notes"] or risk_info["geopolitical_risk"] in ["High", "Critical"]

    # Test Balkan MicroSystems (S002) in Romania
    balkan_risk = get_supplier_risk_tool("S002")
    assert balkan_risk["supplier_id"] == "S002"
    assert balkan_risk["country"] == "RO"


def test_inventory_balance_calculation():
    """Verify usable inventory equals on_hand minus reserved and quarantined."""
    balance = check_inventory_balance_tool("MC-17")
    assert balance["component_id"] == "MC-17"
    assert balance["on_hand"] >= balance["usable"]
    assert balance["usable"] == balance["on_hand"] - balance["reserved"] - balance["quarantined"]
