"""MCP Client and Tool Definitions for SupplyGuard AI.

Platform Role | Scope: mcp, workflow
Provides tools usable by Deep Agents or workflow nodes:
- create_purchase_order_tool
- get_supplier_risk_tool
- check_inventory_balance_tool
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from src.core.contracts import PurchaseOrderReceipt, SupplierRiskInfo
from src.mcp.procurement_server import get_procurement_system


def create_purchase_order_tool(
    action_id: str,
    supplier_id: str,
    component_id: str,
    quantity: int,
    unit_price: float,
    delivery_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute purchase order in simulated procurement system."""
    system = get_procurement_system()
    receipt: PurchaseOrderReceipt = system.create_purchase_order(
        action_id=action_id,
        supplier_id=supplier_id,
        component_id=component_id,
        quantity=quantity,
        unit_price=unit_price,
        delivery_date=delivery_date,
    )
    return receipt.model_dump()


def get_supplier_risk_tool(
    supplier_id: str,
    supplier_name: Optional[str] = None,
    country: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch external risk feed and evaluation for a supplier."""
    system = get_procurement_system()
    risk: SupplierRiskInfo = system.get_supplier_risk(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        country=country,
    )
    return risk.model_dump()


def check_inventory_balance_tool(component_id: str) -> Dict[str, int]:
    """Check inventory usable, reserved, quarantined stock for a component."""
    system = get_procurement_system()
    return system.check_inventory_balance(component_id=component_id)
