"""Output contracts of the Knowledge tools (agreed with Workflow)."""
from pydantic import BaseModel


# --- SupplyGuard Knowledge tool outputs (#67) -------------------------------------------------
# Raw, sourced facts only. Workflow derives OperationalImpact and the recovery maths from them
# with its deterministic calculators, so no number here is computed by an LLM.
class InventoryLocation(BaseModel):
    location_id: str
    factory_id: str | None  # None for the central hub
    on_hand: int
    reserved: int
    quarantined: int
    usable: int
    last_counted_date: str
    stale_count: bool  # last count older than 180 days before the scenario date


class Reservation(BaseModel):
    location_id: str
    customer_order_id: str
    reserved_qty: int


class QuarantineLot(BaseModel):
    lot_id: str
    location_id: str
    qty: int
    reason: str
    release_expected: str


class InventoryStatusResult(BaseModel):
    component_id: str
    total_on_hand: int
    total_reserved: int
    total_quarantined: int
    total_usable: int
    locations: list[InventoryLocation]
    reservations: list[Reservation]
    quarantine_lots: list[QuarantineLot]
    source_id: str = "SRC-WMS-INVENTORY"


class AffectedProduct(BaseModel):
    product_id: str
    name: str
    factory_id: str
    qty_per_unit: int


class CustomerOrderAtRisk(BaseModel):
    order_id: str
    customer_id: str
    product_id: str
    qty: int
    due_date: str
    revenue_eur: float
    priority_tier: int
    late_penalty_pct_per_week: float


class BOMResult(BaseModel):
    component_id: str
    products: list[AffectedProduct]
    open_orders: list[CustomerOrderAtRisk]  # open orders on those products due within horizon_days
    horizon_days: int
    # component units needed per factory per week (planned units x qty_per_unit), 12 weeks
    weekly_demand: dict[str, dict[str, int]]
    source_ids: list[str] = ["SRC-ERP-BOM", "SRC-ERP-ORDERS", "SRC-MES-SCHEDULE"]


class OpenPurchaseOrder(BaseModel):
    po_id: str
    qty: int
    unit_price_eur: float
    promised_date: str
    expedite_allowed: bool
    expedite_fee_pct: float
    expedite_days_gain: int


class ClaimConflict(BaseModel):
    attribute: str
    winner_source_id: str
    value: float
    sources: list[dict]  # every source_id with its value and doc_type


class SupplierOption(BaseModel):
    supplier_id: str
    name: str
    lead_time_days: int | None
    unit_price_eur: float | None
    monthly_capacity_units: int | None
    approved_source: str | None  # yes | no | alternative
    certification_valid: bool
    certification_expiry: str | None
    upstream_id: str | None = None  # only with max_depth >= 2
    upstream_name: str | None = None
    open_purchase_orders: list[OpenPurchaseOrder] = []
    conflicts: list[ClaimConflict] = []  # e.g. e-mail capacity vs contract
    source_id: str  # governing contract version of the SUPPLIES relationship
    effective_date: str


class SharedUpstream(BaseModel):
    upstream_id: str
    supplier_ids: list[str]


class SupplierGraphResult(BaseModel):
    component_id: str
    suppliers: list[SupplierOption]
    shared_upstream: list[SharedUpstream]  # alternatives that are not real diversification


class DocumentResult(BaseModel):
    source_id: str
    doc_type: str
    title: str
    version: int | None
    effective_date: str
    access_scope: str
    content: str
    score: float
    trusted: bool  # False: the text tries to instruct the assistant; treat as data and report it
    security_flags: list[str] = []
    precedence_rank: int | None  # policies.json source_precedence, 0 = contract (highest)
    superseded_by: str | None = None
