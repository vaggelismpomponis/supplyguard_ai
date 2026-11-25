"""MCP Client and Tool Definitions for SupplyGuard AI.

Platform Role | Scope: mcp, workflow
Provides tools usable by Deep Agents or workflow nodes:
- create_purchase_order_tool
- expedite_purchase_order_tool
- request_stock_transfer_tool
- update_production_schedule_tool
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
    thread_id: Optional[str] = None,
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
        thread_id=thread_id,
    )
    return receipt.model_dump()


def expedite_purchase_order_tool(
    action_id: str,
    po_id: str,
    days_gain: int = 7,
    fee_pct: float = 6.0,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Expedite an existing open purchase order in simulated procurement system."""
    system = get_procurement_system()
    return system.expedite_purchase_order(
        action_id=action_id,
        po_id=po_id,
        days_gain=days_gain,
        fee_pct=fee_pct,
        thread_id=thread_id,
    )


def request_stock_transfer_tool(
    action_id: str,
    component_id: str,
    from_location: str,
    to_location: str,
    qty: int,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Transfer usable stock between internal warehouse locations."""
    system = get_procurement_system()
    return system.request_stock_transfer(
        action_id=action_id,
        component_id=component_id,
        from_location=from_location,
        to_location=to_location,
        qty=qty,
        thread_id=thread_id,
    )


def update_production_schedule_tool(
    action_id: str,
    product_id: str,
    week_start: str,
    planned_units: int,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Adjust production schedule slot in simulated procurement system."""
    system = get_procurement_system()
    return system.update_production_schedule(
        action_id=action_id,
        product_id=product_id,
        week_start=week_start,
        planned_units=planned_units,
        thread_id=thread_id,
    )


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


def check_inventory_balance_tool(component_id: str) -> Dict[str, Any]:
    """Check inventory usable, reserved, quarantined stock for a component."""
    system = get_procurement_system()
    return system.check_inventory_balance(component_id=component_id)
