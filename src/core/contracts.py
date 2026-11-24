"""Core domain schemas and architecture contracts for SupplyGuard AI.

Platform & Workflow Roles | Scope: core, workflow, platform
Agreed schemas for agent coordination, subagents, simulated procurement,
MCP protocols, and state persistence.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# 1. Action Types & Lifecycle Status
# ==============================================================================

class ActionType(str, Enum):
    """Enumeration of recovery and workflow actions."""
    TRANSFER_INVENTORY = "transfer_inventory"         # Move usable stock between internal factories
    EXPEDITE_ORDER = "expedite_order"                 # Expedite existing purchase order delivery
    PURCHASE_ALTERNATIVE = "purchase_alternative"     # Create purchase order with qualified alternate supplier
    REALLOCATE_COMPONENTS = "reallocate_components"   # Prioritize component allocations to tier-1 customers
    RESCHEDULE_PRODUCTION = "reschedule_production"   # Shift production runs across the 12-week schedule
    ANSWER_POLICY = "answer_policy"                   # Informative query response from documentary evidence
    REQUEST_CLARIFICATION = "request_clarification"   # Pause to prompt user for ambiguous/missing facts


class ActionStatus(str, Enum):
    """Lifecycle status for state-changing actions."""
    PENDING = "pending"       # Strategy formulated, awaiting human approval
    APPROVED = "approved"     # Explicitly approved by authorized operator
    EXECUTED = "executed"     # Successfully executed in simulated procurement; cannot be re-executed
    REJECTED = "rejected"     # Rejected by operator; alternative plan required


class AccessScope(str, Enum):
    """Role-Based Access Control scopes."""
    PROCUREMENT = "procurement"  # Procurement managers: standard operational & contract docs
    FINANCE = "finance"          # Finance controllers: margin, price & penalty-confidential docs
    PUBLIC = "public"            # Read-only guests: public announcements and high-level case status


# ==============================================================================
# 2. Domain Entities & Incident Extraction
# ==============================================================================

class DisruptionFact(BaseModel):
    """Extracted disruption facts from user incident messages."""
    supplier_id: Optional[str] = Field(default=None, description="Identifier of the supplier (e.g. S001)")
    supplier_name: Optional[str] = Field(default=None, description="Canonical name of the supplier")
    component_id: Optional[str] = Field(default=None, description="Disrupted component (e.g. MC-17)")
    delay_days: Optional[int] = Field(default=None, description="Announced delay duration in days (e.g. 12)")
    spending_cap: float = Field(default=75000.0, description="Spending limit in EUR (€75,000 reference)")
    is_ambiguous: bool = Field(default=False, description="True if supplier name matches multiple entities")
    ambiguity_candidates: List[str] = Field(default_factory=list, description="Potential matches if ambiguous")

    def is_complete(self) -> bool:
        """Mandatory facts needed before starting investigation."""
        return bool(self.supplier_id and self.component_id and self.delay_days and not self.is_ambiguous)


class OperationalImpact(BaseModel):
    """Operational impact synthesis across inventory, BOMs, and schedules."""
    component_id: str = Field(description="Component identifier")
    total_physical_units: int = Field(description="Total stock across all warehouses (e.g. 5,200)")
    usable_units: int = Field(description="Physical minus reserved and quarantined (e.g. 3,200)")
    reserved_units: int = Field(description="Units allocated to locked assembly batches (e.g. 1,400)")
    quarantined_units: int = Field(description="Units held in QA quarantine (e.g. 600)")
    affected_factories: List[str] = Field(description="Factories running out first (e.g. ['Katowice', 'Lyon'])")
    affected_products_count: int = Field(description="Number of product BOMs containing component (e.g. 6)")
    affected_customer_orders_count: int = Field(description="Open customer orders at risk (e.g. 77)")
    uncovered_demand_units: int = Field(description="Demand deficit during delay window (e.g. 5,350)")


class RecoveryOption(BaseModel):
    """Evaluated recovery strategy option."""
    strategy_id: str = Field(description="Unique strategy key (e.g. STRAT-A)")
    action_type: ActionType = Field(description="Type of recovery action")
    supplier_id: Optional[str] = Field(default=None, description="Target supplier if purchase/expedite")
    supplier_name: Optional[str] = Field(default=None, description="Target supplier name")
    quantity: int = Field(description="Units provided or reallocated")
    lead_time_days: int = Field(description="Estimated delivery / execution lead time")
    recovery_cost: float = Field(description="Deterministic cost to execute (freight, price difference)")
    revenue_at_risk: float = Field(description="Protected or remaining revenue exposure")
    is_viable: bool = Field(description="Whether the strategy satisfies operational & policy constraints")
    rejection_reason: Optional[str] = Field(default=None, description="Detailed explanation if rejected")


class ApprovalPayload(BaseModel):
    """Payload presented for human-in-the-loop approval."""
    action_id: str = Field(description="Unique UUID for strict idempotency tracking")
    case_id: str = Field(description="Unique incident case ID")
    action_type: ActionType = Field(description="Approved action type")
    target_supplier_id: Optional[str] = Field(default=None, description="Supplier code (e.g. S002)")
    target_supplier_name: Optional[str] = Field(default=None, description="Supplier name")
    component_id: str = Field(description="Component code (e.g. MC-17)")
    quantity: int = Field(description="Exact purchase or transfer quantity")
    unit_price: float = Field(description="Contracted unit price in EUR")
    total_cost: float = Field(description="Total expenditure (must be <= spending_cap)")
    spending_cap: float = Field(default=75000.0, description="Authorized budget cap")
    supporting_evidence: List[Dict[str, str]] = Field(default_factory=list, description="Citations and sources")
    status: ActionStatus = Field(default=ActionStatus.PENDING, description="Current approval status")


# ==============================================================================
# 3. Procurement & External Risk MCP Contracts
# ==============================================================================

class PurchaseOrderRequest(BaseModel):
    """Request payload for simulated procurement order creation."""
    action_id: str = Field(description="Idempotency key from approved action")
    supplier_id: str = Field(description="Target supplier identifier (e.g. S002)")
    component_id: str = Field(description="Component identifier (e.g. MC-17)")
    quantity: int = Field(description="Quantity ordered")
    unit_price: float = Field(description="Price per unit in EUR")
    delivery_date: str = Field(description="Target delivery date ISO string")


class PurchaseOrderReceipt(BaseModel):
    """Receipt returned by the simulated procurement system upon order creation."""
    order_id: str = Field(description="Generated purchase order ID (e.g. PO-SUP-2026-9999)")
    action_id: str = Field(description="Matched idempotency key")
    supplier_id: str = Field(description="Supplier ID")
    component_id: str = Field(description="Component ID")
    quantity: int = Field(description="Confirmed quantity")
    total_amount: float = Field(description="Total monetary transaction amount in EUR")
    status: str = Field(default="confirmed", description="PO confirmation status")
    created_at: str = Field(description="Timestamp of creation")


class SupplierRiskInfo(BaseModel):
    """External supplier and geographical risk information."""
    supplier_id: str
    supplier_name: str
    country: str
    risk_score: float = Field(description="Risk score 0.0 - 1.0 (higher = riskier)")
    geopolitical_risk: str = Field(description="Low / Medium / High / Critical")
    logistics_status: str = Field(description="Normal / Congested / Disrupted")
    notes: Optional[str] = None
