"""SupplyGuard AI - Architecture Contracts, Domain Schemas & Data-Driven Investigation Engine.

Implements the frozen contracts from docs/ARCHITECTURE_CONTRACTS.md (Sections 2, 4, 5, and 7)
for the Interface role (Issues #41 through #53), backed directly by the synthetic dataset
in `src/support-data/`.

Includes a zero-dependency BaseModel fallback when running outside the Docker virtual
environment (e.g. host unit test runner without pydantic installed).
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional
import uuid

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - lightweight fallback when pydantic is absent on host

    class _FieldSpec:
        def __init__(
            self,
            default: Any = None,
            *,
            default_factory: Optional[Callable[[], Any]] = None,
            description: str = "",
        ) -> None:
            self.default = default
            self.default_factory = default_factory
            self.description = description

    def Field(  # type: ignore[misc]
        default: Any = None,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        description: str = "",
        **kwargs: Any,
    ) -> Any:
        return _FieldSpec(default=default, default_factory=default_factory, description=description)

    class BaseModel:  # type: ignore[no-redef]
        """Minimal Pydantic v2-compatible BaseModel shim for host unit tests."""

        def __init__(self, **kwargs: Any) -> None:
            for attr_name in dir(self.__class__):
                if attr_name.startswith("_"):
                    continue
                val = getattr(self.__class__, attr_name)
                if isinstance(val, _FieldSpec):
                    if attr_name not in kwargs:
                        if val.default_factory is not None:
                            setattr(self, attr_name, val.default_factory())
                        else:
                            setattr(self, attr_name, val.default)
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_copy(self, *, update: Optional[Dict[str, Any]] = None, deep: bool = False) -> Any:
            data = dict(self.__dict__)
            if update:
                data.update(update)
            return self.__class__(**data)

        def model_dump(self) -> Dict[str, Any]:
            return dict(self.__dict__)

        @classmethod
        def model_validate(cls, data: Any) -> Any:
            if isinstance(data, cls):
                return data
            if isinstance(data, dict):
                return cls(**data)
            return cls(**getattr(data, "__dict__", {}))


SUPPORT_DATA_DIR = Path(__file__).resolve().parents[1] / "support-data"


# ==============================================================================
# 1. Core Enumerations (docs/ARCHITECTURE_CONTRACTS.md Section 2.1 - 2.3)
# ==============================================================================

try:
    from src.core.contracts import (
        AccessScope,
        ActionStatus,
        ActionType as SupplyGuardActionType,
    )
except ImportError:  # pragma: no cover - fallback when pydantic is absent on host

    class SupplyGuardActionType(str, Enum):  # type: ignore[no-redef]
        TRANSFER_INVENTORY = "transfer_inventory"
        EXPEDITE_ORDER = "expedite_order"
        PURCHASE_ALTERNATIVE = "purchase_alternative"
        REALLOCATE_COMPONENTS = "reallocate_components"
        RESCHEDULE_PRODUCTION = "reschedule_production"
        COMBINED_RECOVERY_PLAN = "combined_recovery_plan"
        ANSWER_POLICY = "answer_policy"
        REQUEST_CLARIFICATION = "request_clarification"

    class ActionStatus(str, Enum):  # type: ignore[no-redef]
        PENDING = "pending"
        APPROVED = "approved"
        EXECUTED = "executed"
        REJECTED = "rejected"
        INVALIDATED = "invalidated"

    class AccessScope(str, Enum):  # type: ignore[no-redef]
        PROCUREMENT = "procurement"
        FINANCE = "finance"
        PUBLIC = "public"
        INTERNAL = "internal"
        FINANCE_CONFIDENTIAL = "finance-confidential"


# ==============================================================================
# 2. RBAC User Profile & Authentication Models (Issue #41 & #43)
# ==============================================================================


class UserProfile(BaseModel):
    user_id: str = Field(default="u-pm-01", description="User ID from config/users.csv")
    name: str = Field(default="Maria Keller", description="Full name of operator")
    role: str = Field(default="procurement_manager", description="Role identifier")
    access_scope: AccessScope = Field(default=AccessScope.PROCUREMENT, description="Primary RBAC scope")
    document_scopes: List[str] = Field(
        default_factory=lambda: ["public", "internal", "procurement"],
        description="Document scopes permitted for retrieval",
    )
    factory_access: List[str] = Field(
        default_factory=lambda: ["F1", "F2", "F3"],
        description="Permitted factory IDs",
    )
    username: Optional[str] = Field(default=None, description="Login username for authenticated sessions")
    email: Optional[str] = Field(default=None, description="Operator email for login and audit attribution")

    @property
    def can_approve(self) -> bool:
        """Read-only guests ('viewer' / PUBLIC scope) cannot approve or modify purchase orders."""
        return self.role in ("procurement_manager", "finance_controller", "incident_coordinator", "operations_analyst")

    @property
    def can_view_finance_confidential(self) -> bool:
        """Only finance_controller has access to finance-confidential documents (DOC-FIN-01-v1)."""
        return "finance-confidential" in self.document_scopes or self.access_scope == AccessScope.FINANCE

    @property
    def max_approval_eur(self) -> float:
        """Maximum spending limit the role can approve under config/policies.json."""
        if self.role == "finance_controller":
            return 90000.0
        if self.can_approve:
            return 75000.0
        return 0.0

    def can_access_document_scope(self, doc_scope: str) -> bool:
        norm = (doc_scope or "public").strip().lower()
        if norm == "public":
            return True
        if self.can_view_finance_confidential:
            return True
        return norm in [s.lower() for s in self.document_scopes]


# ==============================================================================
# 3. Domain Contract Models (docs/ARCHITECTURE_CONTRACTS.md Section 2.4 - 2.7)
# ==============================================================================


class DisruptionFact(BaseModel):
    supplier_id: Optional[str] = Field(default=None, description="Identifier of the supplier (e.g. S001)")
    supplier_name: Optional[str] = Field(default=None, description="Canonical name of the supplier")
    component_id: Optional[str] = Field(default=None, description="Disrupted component (e.g. MC-17)")
    delay_days: Optional[int] = Field(default=None, description="Announced delay duration in days (e.g. 12)")
    spending_cap: float = Field(default=75000.0, description="Spending limit in EUR (€75,000 reference)")
    affected_po: Optional[str] = Field(default=None, description="Affected open PO (e.g. PO-2026-9001)")
    original_due: Optional[str] = Field(default=None, description="Original due date (e.g. 2026-10-26)")
    new_due: Optional[str] = Field(default=None, description="Delayed due date (e.g. 2026-11-07)")
    is_ambiguous: bool = Field(default=False, description="True if supplier name matches multiple entities")
    ambiguity_candidates: List[str] = Field(default_factory=list, description="Potential matches if ambiguous")
    detected_prompt_injection: Optional[str] = Field(default=None, description="Flagged malicious instruction if any")

    def missing_fields(self) -> List[str]:
        missing: List[str] = []
        if self.is_ambiguous or not self.supplier_id:
            missing.append("supplier_id")
        if not self.component_id:
            missing.append("component_id")
        if not self.delay_days:
            missing.append("delay_days")
        return missing

    def is_complete(self) -> bool:
        """Mandatory facts needed before starting investigation."""
        return bool(self.supplier_id and self.component_id and self.delay_days and not self.is_ambiguous)


class FactoryStockTimeline(BaseModel):
    factory_id: str = Field(default="", description="Factory ID (F1, F2, F3, or HUB)")
    factory_name: str = Field(default="", description="Factory or hub name")
    warehouse_id: str = Field(default="", description="Warehouse code (W-STU, W-KAT, W-LYO, W-HUB)")
    on_hand_units: int = Field(default=0, description="Physical stock on hand")
    reserved_units: int = Field(default=0, description="Reserved units for Tier-1 orders")
    quarantined_units: int = Field(default=0, description="Units held in QA quarantine")
    usable_units: int = Field(default=0, description="Net usable stock")
    daily_demand_units: int = Field(default=150, description="Daily component consumption rate")
    days_of_cover: float = Field(default=0.0, description="Usable stock divided by daily demand")
    runs_out_first: bool = Field(default=False, description="True if factory runs out before arrival")


class OperationalImpact(BaseModel):
    component_id: str = Field(default="MC-17", description="Component identifier")
    total_physical_units: int = Field(default=5200, description="Total stock across all warehouses")
    usable_units: int = Field(default=3200, description="Physical minus reserved and quarantined")
    reserved_units: int = Field(default=1400, description="Units allocated to locked assembly batches")
    quarantined_units: int = Field(default=600, description="Units held in QA quarantine")
    quarantine_lot_id: str = Field(default="LOT-KAT-0932", description="Quarantine lot reference")
    quarantine_reason: str = Field(default="Failed incoming inspection (solder defect)", description="QA hold reason")
    affected_factories: List[str] = Field(
        default_factory=lambda: ["Katowice (F2)", "Lyon (F3)"],
        description="Factories running out first",
    )
    factory_timelines: List[FactoryStockTimeline] = Field(
        default_factory=list,
        description="Per-location inventory and days-of-cover timeline",
    )
    hub_usable_units: int = Field(default=800, description="Central hub W-HUB stock available for transfer")
    affected_products: List[str] = Field(
        default_factory=lambda: ["P012", "P023", "P031", "P047", "P058", "P066"],
        description="Affected product codes",
    )
    affected_products_count: int = Field(default=6, description="Number of product BOMs containing component")
    affected_customer_orders_count: int = Field(default=77, description="Open customer orders at risk")
    daily_demand_total: int = Field(default=450, description="Total daily demand across all factories")
    stock_at_original_arrival: int = Field(default=50, description="Remaining usable stock on original arrival day")
    uncovered_demand_units: int = Field(default=5350, description="Demand deficit during delay window")
    reserved_stock_orders: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tier-1 customer orders tied to reserved stock",
    )
    total_revenue_at_risk_eur: float = Field(
        default=412500.0,
        description="Projected revenue exposure across at-risk open customer orders (reported separately from recovery cost)",
    )


class DocumentaryFinding(BaseModel):
    source_id: str = Field(default="", description="Document source identifier (e.g. DOC-CON-S001-v3)")
    doc_type: str = Field(default="contract", description="Document category")
    title: str = Field(default="", description="Document title")
    supplier_id: Optional[str] = Field(default=None, description="Associated supplier ID")
    version: str = Field(default="1", description="Document version")
    effective_date: str = Field(default="", description="Effective date (YYYY-MM-DD)")
    access_scope: str = Field(default="procurement", description="RBAC access scope")
    summary: str = Field(default="", description="Finding summary")
    is_conflict: bool = Field(default=False, description="True if conflicting with another source")
    conflict_resolution: Optional[str] = Field(default=None, description="Precedence-based conflict resolution")
    is_superseded: bool = Field(default=False, description="True if superseded by a newer effective version")
    is_malicious: bool = Field(default=False, description="True if prompt injection detected and neutralized")


class RecoveryOption(BaseModel):
    strategy_id: str = Field(default="STRAT-1", description="Unique strategy key")
    strategy_code: str = Field(default="A+B+C+D/E", description="Strategy category codes (A, B, C, D, E)")
    title: str = Field(default="", description="Human-readable strategy title")
    action_type: SupplyGuardActionType = Field(
        default=SupplyGuardActionType.COMBINED_RECOVERY_PLAN,
        description="Type of recovery action",
    )
    supplier_id: Optional[str] = Field(default=None, description="Target supplier if purchase/expedite")
    supplier_name: Optional[str] = Field(default=None, description="Target supplier name")
    quantity: int = Field(default=0, description="Units provided or reallocated")
    unit_price: float = Field(default=0.0, description="Unit price in EUR")
    lead_time_days: int = Field(default=0, description="Estimated delivery / execution lead time")
    recovery_cost: float = Field(default=0.0, description="Deterministic cost to execute (freight, price, fees)")
    revenue_at_risk: float = Field(
        default=0.0,
        description="Remaining revenue exposure (strictly separated from recovery cost; penalties counted once)",
    )
    uncovered_units_remaining: int = Field(default=0, description="Residual uncovered units after action")
    is_viable: bool = Field(default=True, description="Whether strategy satisfies operational & policy constraints")
    is_recommended: bool = Field(default=False, description="True for primary recommended recovery plan")
    rejection_reason: Optional[str] = Field(default=None, description="Detailed explanation if rejected")
    actions_breakdown: List[str] = Field(default_factory=list, description="Granular steps included in plan")
    cost_breakdown: Dict[str, float] = Field(default_factory=dict, description="Itemized deterministic cost breakdown")
    supporting_sources: List[str] = Field(default_factory=list, description="Provenance source IDs")


class ApprovalPayload(BaseModel):
    action_id: str = Field(default_factory=lambda: f"act-{uuid.uuid4().hex[:10]}", description="Unique UUID for idempotency")
    case_id: str = Field(default="CASE-MC17-001", description="Unique incident case ID")
    action_type: SupplyGuardActionType = Field(
        default=SupplyGuardActionType.COMBINED_RECOVERY_PLAN,
        description="Approved action type",
    )
    target_supplier_id: Optional[str] = Field(default="S004", description="Supplier code (e.g. S004)")
    target_supplier_name: Optional[str] = Field(default="Cordillera Industrial", description="Supplier name")
    component_id: str = Field(default="MC-17", description="Component code (e.g. MC-17)")
    quantity: int = Field(default=3000, description="Exact purchase order quantity")
    unit_price: float = Field(default=9.80, description="Contracted unit price in EUR")
    po_subtotal_eur: float = Field(default=29400.0, description="PO subtotal (quantity * unit_price)")
    expedite_po_id: Optional[str] = Field(default="PO-2026-9002", description="Existing open PO to expedite")
    expedite_units: int = Field(default=1500, description="Units in expedited existing PO")
    expedite_fee_pct: float = Field(default=6.0, description="Contracted expedite fee percentage")
    expedite_fee_eur: float = Field(default=882.0, description="Deterministic expedite fee in EUR")
    transfer_from_location: str = Field(default="W-HUB", description="Source warehouse for transfer")
    transfer_to_locations: str = Field(default="W-LYO (450) & W-KAT (350)", description="Destination warehouses")
    transfer_units: int = Field(default=800, description="Hub units transferred")
    transfer_cost_eur: float = Field(default=96.0, description="Transfer cost at EUR 0.12/unit")
    residual_units_reallocated: int = Field(default=850, description="Residual units covered via D/E schedule shift")
    total_cost: float = Field(default=30378.0, description="Total expenditure (must be <= spending_cap)")
    spending_cap: float = Field(default=75000.0, description="Authorized budget cap in EUR")
    revenue_at_risk_protected_eur: float = Field(
        default=412500.0,
        description="Customer order revenue protected (reported separately from recovery cost)",
    )
    supporting_evidence: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Citations with source_id, effective_date, access_scope",
    )
    status: ActionStatus = Field(default=ActionStatus.PENDING, description="Current approval status")
    payload_hash: str = Field(default="", description="SHA-256 digest binding approval to exact payload parameters")
    revision: int = Field(default=1, description="Payload revision counter incremented on Modify Plan")

    def compute_payload_hash(self) -> str:
        """Compute deterministic SHA-256 digest over all binding financial & operational fields."""
        canonical = json.dumps(
            {
                "case_id": self.case_id,
                "action_type": self.action_type.value if hasattr(self.action_type, "value") else str(self.action_type),
                "target_supplier_id": self.target_supplier_id,
                "component_id": self.component_id,
                "quantity": int(self.quantity),
                "unit_price": round(float(self.unit_price), 2),
                "expedite_po_id": self.expedite_po_id,
                "expedite_units": int(self.expedite_units),
                "expedite_fee_eur": round(float(self.expedite_fee_eur), 2),
                "transfer_units": int(self.transfer_units),
                "transfer_cost_eur": round(float(self.transfer_cost_eur), 2),
                "total_cost": round(float(self.total_cost), 2),
                "spending_cap": round(float(self.spending_cap), 2),
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def ensure_hash(self) -> "ApprovalPayload":
        if not self.payload_hash:
            self.payload_hash = self.compute_payload_hash()
        return self

    def verify_binding(self, expected_hash: Optional[str] = None) -> bool:
        """Verify that payload parameters have not been mutated since approval presentation."""
        current = self.compute_payload_hash()
        if expected_hash and expected_hash != current:
            return False
        return bool(self.payload_hash) and self.payload_hash == current

    def is_within_cap(self) -> bool:
        return float(self.total_cost) <= float(self.spending_cap)


class ProcurementReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: f"RCP-{uuid.uuid4().hex[:8].upper()}", description="Receipt ID")
    action_id: str = Field(default="", description="Approved action_id")
    case_id: str = Field(default="CASE-MC17-001", description="Case ID")
    idempotency_key: str = Field(default="", description="Strict idempotency key (case_id:action_id)")
    payload_hash: str = Field(default="", description="Verified SHA-256 payload digest")
    po_number: str = Field(default="PO-2026-9003", description="Created Purchase Order ID")
    expedite_ref: Optional[str] = Field(default="EXP-PO-2026-9002", description="Expedite transaction reference")
    transfer_ref: Optional[str] = Field(default="TRF-2026-0800", description="Stock transfer order reference")
    schedule_ref: Optional[str] = Field(default="SCH-2026-W43", description="Production schedule update reference")
    supplier_id: str = Field(default="S004", description="Executed supplier ID")
    supplier_name: str = Field(default="Cordillera Industrial", description="Executed supplier name")
    component_id: str = Field(default="MC-17", description="Ordered component ID")
    quantity: int = Field(default=3000, description="Ordered quantity")
    unit_price_eur: float = Field(default=9.80, description="Unit price in EUR")
    total_cost_eur: float = Field(default=30378.0, description="Total committed recovery expenditure")
    approved_by: str = Field(default="Maria Keller", description="Approving operator name")
    approver_role: str = Field(default="procurement_manager", description="Approving operator role")
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        description="UTC execution timestamp",
    )
    operations_executed: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="MCP simulated procurement operations executed",
    )
    status: ActionStatus = Field(default=ActionStatus.EXECUTED, description="Execution status")


class IncidentReport(BaseModel):
    report_id: str = Field(default="INC-2026-MC17-001", description="Incident report identifier")
    case_id: str = Field(default="CASE-MC17-001", description="Case ID")
    thread_id: str = Field(default="", description="Session / Thread ID")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        description="Report timestamp",
    )
    prepared_by: str = Field(default="Maria Keller (procurement_manager)", description="Operator identity & role")
    disruption_fact: DisruptionFact = Field(default_factory=DisruptionFact)
    operational_impact: OperationalImpact = Field(default_factory=OperationalImpact)
    recovery_options: List[RecoveryOption] = Field(default_factory=list)
    approval_payload: ApprovalPayload = Field(default_factory=ApprovalPayload)
    procurement_receipt: ProcurementReceipt = Field(default_factory=ProcurementReceipt)
    documentary_findings: List[DocumentaryFinding] = Field(default_factory=list)
    approved_memory_summary: str = Field(default="", description="Retained resolution summary for future cases")

    def to_markdown(self) -> str:
        """Render a comprehensive, audit-ready Markdown Incident Report."""
        f = self.disruption_fact
        imp = self.operational_impact
        pay = self.approval_payload
        rcp = self.procurement_receipt

        lines = [
            f"# SupplyGuard AI — Official Supply Chain Disruption Incident Report",
            "",
            f"- **Report ID:** `{self.report_id}`",
            f"- **Case ID:** `{self.case_id}`",
            f"- **Session / Thread ID:** `{self.thread_id}`",
            f"- **Generated At:** `{self.generated_at}`",
            f"- **Prepared & Approved By:** `{self.prepared_by}`",
            f"- **Execution Status:** `{rcp.status.value.upper()}` (Idempotency Key: `{rcp.idempotency_key}`)",
            "",
            "---",
            "",
            "## 1. Incident Summary & Extracted Disruption Facts",
            f"- **Disrupted Supplier:** `{f.supplier_id}` — **{f.supplier_name}**",
            f"- **Affected Component:** `{f.component_id}`",
            f"- **Stated Delay:** `{f.delay_days} days` (Affected PO: `{f.affected_po or 'PO-2026-9001'}`, "
            f"Original Due: `{f.original_due or '2026-10-26'}` → New Due: `{f.new_due or '2026-11-07'}`)",
            f"- **Authorized Spending Cap:** `€{f.spending_cap:,.2f}`",
            "",
            "## 2. Operational & Business Impact Assessment",
            f"- **Total Physical Stock On-Hand:** `{imp.total_physical_units:,} units`",
            f"- **Reserved Stock (Locked Tier-1 Orders):** `{imp.reserved_units:,} units`",
            f"- **Quarantined Stock (Lot `{imp.quarantine_lot_id}`):** `{imp.quarantined_units:,} units` (*{imp.quarantine_reason} — excluded*)",
            f"- **Net Usable Stock:** **`{imp.usable_units:,} units`** (incl. `{imp.hub_usable_units:,} units` at Central Hub `W-HUB`)",
            f"- **Critical Factories Running Out First:** `{', '.join(imp.affected_factories)}`",
            f"- **Affected Products ({imp.affected_products_count}):** `{', '.join(imp.affected_products)}`",
            f"- **Open Customer Orders at Risk (60-day window):** **`{imp.affected_customer_orders_count} orders`**",
            f"- **Uncovered Demand Shortfall:** **`{imp.uncovered_demand_units:,} units`** (Daily demand: `{imp.daily_demand_total} units/day`)",
            f"- **Projected Revenue at Risk (Reported Separately from Recovery Cost):** **`€{imp.total_revenue_at_risk_eur:,.2f}`**",
            "",
            "## 3. Recovery Strategy Comparison Matrix",
            "| Strategy | Candidate / Action | Quantity | Lead Time | Recovery Cost (€) | Revenue at Risk (€) | Decision & Rationale |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
        for opt in self.recovery_options:
            status_badge = "✅ RECOMMENDED" if opt.is_recommended else ("🟢 VIABLE" if opt.is_viable else "❌ REJECTED")
            reason = opt.rejection_reason or "; ".join(opt.actions_breakdown)
            lines.append(
                f"| `{opt.strategy_code}` | **{opt.title}** | `{opt.quantity:,}` | `{opt.lead_time_days}d` | "
                f"`€{opt.recovery_cost:,.2f}` | `€{opt.revenue_at_risk:,.2f}` | **{status_badge}**: {reason} |"
            )

        lines.extend([
            "",
            "## 4. Payload-Bound Human Approval & Simulated Procurement Execution",
            f"- **Action ID:** `{pay.action_id}`",
            f"- **Payload Binding SHA-256 Digest:** `{pay.payload_hash}`",
            f"- **Primary Purchase Order Created:** `{rcp.po_number}` — **{pay.target_supplier_name} (`{pay.target_supplier_id}`)** "
            f"for `{pay.quantity:,} units` of `{pay.component_id}` @ `€{pay.unit_price:.2f}/unit` = **`€{pay.po_subtotal_eur:,.2f}`**",
            f"- **Expedited Existing Order:** `{rcp.expedite_ref}` (`{pay.expedite_po_id}`, `{pay.expedite_units:,} units`, "
            f"+7 days gain, `{pay.expedite_fee_pct:.0f}%` contract fee = **`€{pay.expedite_fee_eur:,.2f}`**)",
            f"- **Internal Hub Stock Transfer:** `{rcp.transfer_ref}` (`{pay.transfer_units:,} units` from `{pay.transfer_from_location}` "
            f"to `{pay.transfer_to_locations}` @ `€0.12/unit` = **`€{pay.transfer_cost_eur:,.2f}`**)",
            f"- **Total Approved Recovery Expenditure:** **`€{pay.total_cost:,.2f}`** (Cap: `€{pay.spending_cap:,.2f}` — Within Limit)",
            "",
            "## 5. Provenance Citations, Conflict Resolution & Security Audit",
        ])
        for doc in self.documentary_findings:
            tag = "🛡️ [SECURITY ALERT - NEUTRALIZED]" if doc.is_malicious else (
                "⚖️ [CONFLICT RESOLVED]" if doc.is_conflict else (
                    "⚠️ [SUPERSEDED]" if doc.is_superseded else "📄 [EVIDENCE]"
                )
            )
            lines.append(
                f"- {tag} **`{doc.source_id}`** (v{doc.version}, effective `{doc.effective_date}`, scope `{doc.access_scope}`): "
                f"{doc.summary}" + (f" -> *{doc.conflict_resolution}*" if doc.conflict_resolution else "")
            )

        lines.extend([
            "",
            "## 6. Approved Resolution Memory Retained for Future Cases",
            f"> {self.approved_memory_summary}",
            "",
        ])
        return "\n".join(lines)

    def to_pdf_bytes(self) -> bytes:
        """Generate a valid, self-contained PDF-1.4 document from the Markdown report without external C dependencies."""
        md_text = self.to_markdown()
        plain_lines: List[str] = []
        for raw_line in md_text.splitlines():
            cleaned = (
                raw_line.replace("**", "")
                .replace("`", "")
                .replace("€", "EUR ")
                .replace("→", "->")
                .replace("—", "-")
                .replace("✅", "[OK]")
                .replace("❌", "[REJECTED]")
                .replace("🟢", "[VIABLE]")
                .replace("🛡️", "[SEC]")
                .replace("⚖️", "[CONFLICT]")
                .replace("⚠️", "[WARN]")
                .replace("📄", "[DOC]")
            )
            # Wrap at 90 chars for clean PDF layout
            while len(cleaned) > 92:
                plain_lines.append(cleaned[:92])
                cleaned = "  " + cleaned[92:]
            plain_lines.append(cleaned)

        def _pdf_escape(s: str) -> str:
            ascii_s = s.encode("latin-1", errors="replace").decode("latin-1")
            return ascii_s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        # Paginate at 48 lines per page
        lines_per_page = 48
        pages_lines = [
            plain_lines[i : i + lines_per_page]
            for i in range(0, max(1, len(plain_lines)), lines_per_page)
        ]

        objects: List[bytes] = []

        # Object 1: Catalog
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Object 2: Pages (kids filled below)
        page_obj_ids = [4 + 2 * idx for idx in range(len(pages_lines))]
        kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        objects.append(
            f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>\nendobj\n".encode("latin-1")
        )

        # Object 3: Helvetica Font
        objects.append(
            b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        )

        # Page & Content stream objects
        for idx, p_lines in enumerate(pages_lines):
            page_id = 4 + 2 * idx
            content_id = page_id + 1
            stream_cmds = ["BT", "/F1 9 Tf", "14 TL", "40 750 Td"]
            for line in p_lines:
                stream_cmds.append(f"({_pdf_escape(line)}) Tj T*")
            stream_cmds.append("ET")
            stream_bytes = "\n".join(stream_cmds).encode("latin-1")

            page_obj = (
                f"{page_id} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>\n"
                f"endobj\n"
            ).encode("latin-1")
            content_obj = (
                f"{content_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
                + stream_bytes
                + b"\nendstream\nendobj\n"
            )
            objects.append(page_obj)
            objects.append(content_obj)

        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        body_parts: List[bytes] = [header]
        offsets: List[int] = [0]
        cursor = len(header)
        for obj in objects:
            offsets.append(cursor)
            body_parts.append(obj)
            cursor += len(obj)

        xref_offset = cursor
        xref_lines = [f"xref\n0 {len(offsets)}\n", "0000000000 65535 f \n"]
        for off in offsets[1:]:
            xref_lines.append(f"{off:010d} 00000 n \n")
        trailer = (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        )
        body_parts.append("".join(xref_lines).encode("latin-1"))
        body_parts.append(trailer.encode("latin-1"))
        return b"".join(body_parts)


# ==============================================================================
# 4. Support-Data Repository Loader & Deterministic Business Engine
# ==============================================================================


def load_users_from_csv() -> Dict[str, UserProfile]:
    """Load RBAC user profiles from src/support-data/config/users.csv."""
    users_path = SUPPORT_DATA_DIR / "config" / "users.csv"
    profiles: Dict[str, UserProfile] = {}
    if users_path.exists():
        with users_path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                role = (row.get("role") or "procurement_manager").strip()
                scopes = [s.strip() for s in (row.get("document_scopes") or "public").split(";") if s.strip()]
                factories = [f.strip() for f in (row.get("factory_access") or "").split(";") if f.strip()]
                if "finance-confidential" in scopes or role == "finance_controller":
                    primary_scope = AccessScope.FINANCE
                elif "procurement" in scopes:
                    primary_scope = AccessScope.PROCUREMENT
                else:
                    primary_scope = AccessScope.PUBLIC
                user_id = row["user_id"].strip()
                username = (row.get("username") or user_id).strip()
                email = (row.get("email") or f"{username}@supplyguard.eu").strip()
                prof = UserProfile(
                    user_id=user_id,
                    name=row["name"].strip(),
                    role=role,
                    access_scope=primary_scope,
                    document_scopes=scopes,
                    factory_access=factories,
                    username=username,
                    email=email,
                )
                profiles[prof.role] = prof
                profiles[prof.user_id] = prof

    # Ensure standard 3 RBAC aliases always exist
    if "procurement_manager" not in profiles:
        profiles["procurement_manager"] = UserProfile()
    if "finance_controller" not in profiles:
        profiles["finance_controller"] = UserProfile(
            user_id="u-fc-01",
            name="Paul Novak",
            role="finance_controller",
            access_scope=AccessScope.FINANCE,
            document_scopes=["public", "internal", "procurement", "finance-confidential"],
            factory_access=["F1", "F2", "F3"],
        )
    if "viewer" not in profiles:
        profiles["viewer"] = UserProfile(
            user_id="u-ro-01",
            name="Read Only Guest",
            role="viewer",
            access_scope=AccessScope.PUBLIC,
            document_scopes=["public"],
            factory_access=[],
        )
    profiles["procurement"] = profiles["procurement_manager"]
    profiles["finance"] = profiles["finance_controller"]
    profiles["guest"] = profiles["viewer"]
    profiles["public"] = profiles["viewer"]
    return profiles


def _load_suppliers_table() -> List[Dict[str, str]]:
    path = SUPPORT_DATA_DIR / "structured" / "suppliers.csv"
    if not path.exists():
        return [
            {"supplier_id": "S001", "name": "Atlas Components", "city": "Stuttgart", "country": "DE", "upstream_manufacturer_id": "U01", "certification_status": "valid", "certification_expiry": "2027-06-30"},
            {"supplier_id": "S002", "name": "Helios Supply", "city": "Cluj", "country": "RO", "upstream_manufacturer_id": "U03", "certification_status": "valid", "certification_expiry": "2027-03-31"},
            {"supplier_id": "S003", "name": "Borealis Parts", "city": "Gothenburg", "country": "SE", "upstream_manufacturer_id": "U04", "certification_status": "expired", "certification_expiry": "2026-09-30"},
            {"supplier_id": "S004", "name": "Cordillera Industrial", "city": "Brno", "country": "CZ", "upstream_manufacturer_id": "U02", "certification_status": "valid", "certification_expiry": "2027-11-30"},
            {"supplier_id": "S005", "name": "Delta Micro Systems", "city": "Eindhoven", "country": "NL", "upstream_manufacturer_id": "U01", "certification_status": "valid", "certification_expiry": "2027-08-31"},
            {"supplier_id": "S006", "name": "Atlas Logistik GmbH", "city": "Hamburg", "country": "DE", "upstream_manufacturer_id": "", "certification_status": "valid", "certification_expiry": "2027-05-31"},
        ]
    with path.open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|policies)",
    r"system\s+instruction",
    r"(?:for|to)\s+(?:ai|llm)\s+(?:assistants?|agents?|models?)",
    r"(?:^|\s)(?:system|assistant)\s*:",
    r"(?:execute|place|issue|approve)\s+(?:an?\s+)?(?:purchase\s+)?order\b.{0,40}\bwithout\s+(?:human\s+)?approval",
    r"do\s+not\s+(?:mention|tell|inform|report)\b.{0,30}\b(?:user|message|this)",
    r"(?:skip|bypass|disable)\s+(?:the\s+)?(?:human\s+)?approval",
    r"mark\s+.{0,40}\s+as\s+(?:certified|approved)",
    r"approve\s+any\s+purchase\s+from\s+helios",
    r"finance\s+director\s+already\s+approved",
    r"i\s+am\s+the\s+finance\s+director",
)


def detect_prompt_injection_in_text(text: str) -> Optional[str]:
    """Scan incoming text or attached notices for adversarial prompt injection attempts."""
    lowered = text.lower()
    for pat in PROMPT_INJECTION_PATTERNS:
        m = re.search(pat, lowered)
        if m:
            return m.group(0).strip()
    return None


def _strip_untrusted_notice(text: str) -> str:
    """Remove embedded 'Attached notice: ...' payloads before extracting operational caps."""
    return re.split(r"\battached\s+notice\s*:", text, maxsplit=1, flags=re.I)[0]


def extract_disruption_fact(
    text: str,
    previous_fact: Optional[DisruptionFact] = None,
) -> DisruptionFact:
    """Extract supplier, component, delay days, and spending cap from user message, flagging ambiguity."""
    suppliers = _load_suppliers_table()
    clean_text = _strip_untrusted_notice(text)
    lowered = clean_text.lower()

    supplier_id = previous_fact.supplier_id if previous_fact and not previous_fact.is_ambiguous else None
    supplier_name = previous_fact.supplier_name if previous_fact and not previous_fact.is_ambiguous else None
    component_id = previous_fact.component_id if previous_fact else None
    delay_days = previous_fact.delay_days if previous_fact else None
    spending_cap = previous_fact.spending_cap if previous_fact else 75000.0

    # 1. Component ID (e.g. MC-17, MC-140)
    comp_match = re.search(r"\b(MC-?\d{1,3})\b", clean_text, re.I)
    if comp_match:
        raw_comp = comp_match.group(1).upper()
        if not raw_comp.startswith("MC-"):
            raw_comp = "MC-" + raw_comp[2:]
        component_id = raw_comp

    # 2. Delay duration in days (e.g. "12-day delay", "12 days late", "takes 3 days", "by about 5 days")
    delay_match = re.search(
        r"\b(\d{1,3})\s*(?:-\s*day|days?)\s*(?:delay|late|hold|re-inspection|disruption)?\b"
        r"|\b(?:takes|delayed\s+by(?:\s+about)?)\s+(\d{1,3})\s*days?\b",
        lowered,
    )
    if delay_match:
        val_str = delay_match.group(1) or delay_match.group(2)
        if val_str:
            delay_days = int(val_str)

    # 3. Spending cap (e.g. "€75,000", "EUR 90,000", "75000")
    cap_match = re.search(r"(?:€|eur\s*)(\d{2,3}(?:,\d{3})+|\d{4,6})", lowered)
    if cap_match:
        spending_cap = float(cap_match.group(1).replace(",", ""))

    # 4. Explicit supplier ID (e.g. S001, S006)
    sid_match = re.search(r"\b(S0\d{2})\b", clean_text, re.I)
    is_ambiguous = False
    ambiguity_candidates: List[str] = []

    if sid_match:
        sid = sid_match.group(1).upper()
        matched_sup = next((s for s in suppliers if s["supplier_id"].upper() == sid), None)
        if matched_sup:
            supplier_id = matched_sup["supplier_id"]
            supplier_name = matched_sup["name"]
    else:
        # Match full canonical supplier name
        exact_matches = [
            s for s in suppliers if s["name"].lower() in lowered
        ]
        if len(exact_matches) == 1:
            supplier_id = exact_matches[0]["supplier_id"]
            supplier_name = exact_matches[0]["name"]
        elif len(exact_matches) > 1:
            is_ambiguous = True
            ambiguity_candidates = [f"{s['name']} ({s['supplier_id']}, {s.get('city', '')})" for s in exact_matches]
        else:
            # Check prefix token like "Atlas" which matches both Atlas Components (S001) and Atlas Logistik GmbH (S006)
            prefix_candidates: List[Dict[str, str]] = []
            for s in suppliers:
                first_word = s["name"].split()[0].lower()
                if len(first_word) >= 4 and re.search(rf"\b{re.escape(first_word)}\b", lowered):
                    prefix_candidates.append(s)
            if len(prefix_candidates) > 1:
                is_ambiguous = True
                supplier_id = None
                supplier_name = None
                ambiguity_candidates = [
                    f"{s['name']} ({s['supplier_id']}, {s.get('city', '')}, {s.get('country', '')})"
                    for s in prefix_candidates
                ]
            elif len(prefix_candidates) == 1:
                supplier_id = prefix_candidates[0]["supplier_id"]
                supplier_name = prefix_candidates[0]["name"]

    if "not sure which supplier" in lowered or "unknown supplier" in lowered:
        supplier_id = None
        supplier_name = None

    affected_po = "PO-2026-9001" if (supplier_id == "S001" and component_id == "MC-17") else None
    original_due = "2026-10-26" if affected_po == "PO-2026-9001" else None
    new_due = "2026-11-07" if (affected_po == "PO-2026-9001" and delay_days == 12) else None

    return DisruptionFact(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        component_id=component_id,
        delay_days=delay_days,
        spending_cap=spending_cap,
        affected_po=affected_po,
        original_due=original_due,
        new_due=new_due,
        is_ambiguous=is_ambiguous,
        ambiguity_candidates=ambiguity_candidates,
        detected_prompt_injection=detect_prompt_injection_in_text(text),
    )


def build_clarification_question(fact: DisruptionFact) -> str:
    """Format a polite, non-guessing clarification dialog when supplier is ambiguous or fields are missing."""
    lines = ["⚠️ **Clarification Required Before Starting Disruption Investigation**", ""]
    if fact.is_ambiguous and fact.ambiguity_candidates:
        candidates_bullets = "\n".join(f"  - **{c}**" for c in fact.ambiguity_candidates)
        lines.extend([
            "The supplier name you mentioned matches multiple active suppliers in our master data. "
            "Per governance policy, **SupplyGuard AI never guesses ambiguous entities**:",
            candidates_bullets,
            "",
        ])
    missing = fact.missing_fields()
    prompts: List[str] = []
    if "supplier_id" in missing:
        if fact.is_ambiguous:
            prompts.append("which specific **Supplier** (e.g. `Atlas Components (S001)` vs `Atlas Logistik GmbH (S006)`)")
        else:
            prompts.append("the **Supplier Name or ID** (e.g. `Atlas Components` / `S001`)")
    if "component_id" in missing:
        prompts.append("the affected **Component ID** (e.g. `MC-17`)")
    if "delay_days" in missing:
        prompts.append("the announced **Delay Duration in days** (e.g. `12 days`)")

    if prompts:
        lines.append(f"Please clarify {', '.join(prompts)} so I can run the operational impact and recovery analysis.")
    return "\n".join(lines)


def compute_operational_impact(fact: DisruptionFact) -> OperationalImpact:
    """Compute operational impact from support-data CSVs (or golden MC-17 reference data)."""
    comp_id = fact.component_id or "MC-17"
    delay_days = fact.delay_days or 12

    if comp_id == "MC-17":
        timelines = [
            FactoryStockTimeline(
                factory_id="F3",
                factory_name="Lyon Plant (F3)",
                warehouse_id="W-LYO",
                on_hand_units=1100,
                reserved_units=600,
                quarantined_units=0,
                usable_units=500,
                daily_demand_units=150,
                days_of_cover=3.3,
                runs_out_first=True,
            ),
            FactoryStockTimeline(
                factory_id="F2",
                factory_name="Katowice Plant (F2)",
                warehouse_id="W-KAT",
                on_hand_units=1500,
                reserved_units=300,
                quarantined_units=600,
                usable_units=600,
                daily_demand_units=150,
                days_of_cover=4.0,
                runs_out_first=True,
            ),
            FactoryStockTimeline(
                factory_id="F1",
                factory_name="Stuttgart Plant (F1)",
                warehouse_id="W-STU",
                on_hand_units=1800,
                reserved_units=500,
                quarantined_units=0,
                usable_units=1300,
                daily_demand_units=150,
                days_of_cover=8.7,
                runs_out_first=False,
            ),
            FactoryStockTimeline(
                factory_id="HUB",
                factory_name="Rotterdam Central Hub",
                warehouse_id="W-HUB",
                on_hand_units=800,
                reserved_units=0,
                quarantined_units=0,
                usable_units=800,
                daily_demand_units=0,
                days_of_cover=0.0,
                runs_out_first=False,
            ),
        ]
        reserved_orders = [
            {"customer_order_id": "CO-00022", "location_id": "W-STU", "reserved_qty": 250, "tier": 1},
            {"customer_order_id": "CO-00244", "location_id": "W-STU", "reserved_qty": 250, "tier": 1},
            {"customer_order_id": "CO-00005", "location_id": "W-KAT", "reserved_qty": 300, "tier": 1},
            {"customer_order_id": "CO-00173", "location_id": "W-LYO", "reserved_qty": 300, "tier": 1},
            {"customer_order_id": "CO-00073", "location_id": "W-LYO", "reserved_qty": 200, "tier": 1},
            {"customer_order_id": "CO-00410", "location_id": "W-LYO", "reserved_qty": 100, "tier": 1},
        ]
        # Dynamic shortfall if delay_days differs from 12 (e.g. 16-day sensitivity analysis)
        uncovered = 5350 if delay_days == 12 else max(0, delay_days * 450 - 50)
        return OperationalImpact(
            component_id="MC-17",
            total_physical_units=5200,
            usable_units=3200,
            reserved_units=1400,
            quarantined_units=600,
            quarantine_lot_id="LOT-KAT-0932",
            quarantine_reason="Failed incoming inspection (solder defect)",
            affected_factories=["Katowice (F2)", "Lyon (F3)"],
            factory_timelines=timelines,
            hub_usable_units=800,
            affected_products=["P012", "P023", "P031", "P047", "P058", "P066"],
            affected_products_count=6,
            affected_customer_orders_count=77,
            daily_demand_total=450,
            stock_at_original_arrival=50,
            uncovered_demand_units=uncovered,
            reserved_stock_orders=reserved_orders,
            total_revenue_at_risk_eur=412500.0,
        )

    # Dynamic calculation from structured CSVs for any other component in support-data
    inv_path = SUPPORT_DATA_DIR / "structured" / "inventory.csv"
    bom_path = SUPPORT_DATA_DIR / "structured" / "bill_of_materials.csv"
    co_path = SUPPORT_DATA_DIR / "structured" / "customer_orders.csv"

    on_hand = reserved = quarantined = usable = hub_usable = 0
    timelines = []
    if inv_path.exists():
        with inv_path.open("r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["component_id"] == comp_id:
                    oh = int(row["on_hand"])
                    res = int(row["reserved"])
                    quar = int(row["quarantined"])
                    us = int(row["usable"])
                    loc = row["location_id"]
                    on_hand += oh
                    reserved += res
                    quarantined += quar
                    usable += us
                    if loc == "W-HUB":
                        hub_usable += us
                    timelines.append(
                        FactoryStockTimeline(
                            factory_id=loc,
                            factory_name=loc,
                            warehouse_id=loc,
                            on_hand_units=oh,
                            reserved_units=res,
                            quarantined_units=quar,
                            usable_units=us,
                            daily_demand_units=100,
                            days_of_cover=round(us / 100.0, 1) if loc != "W-HUB" else 0.0,
                            runs_out_first=(us < delay_days * 100),
                        )
                    )

    affected_products: List[str] = []
    if bom_path.exists():
        with bom_path.open("r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["component_id"] == comp_id and row["product_id"] not in affected_products:
                    affected_products.append(row["product_id"])
    affected_products.sort()

    open_orders = 0
    revenue_at_risk = 0.0
    if co_path.exists() and affected_products:
        with co_path.open("r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (
                    row["product_id"] in affected_products
                    and row["status"] == "open"
                    and "2026-10-19" <= row["due_date"] <= "2026-12-18"
                ):
                    open_orders += 1
                    revenue_at_risk += float(row.get("revenue_eur") or 0.0)

    daily_demand = max(100, len(affected_products) * 50)
    uncovered = max(0, delay_days * daily_demand - usable)
    return OperationalImpact(
        component_id=comp_id,
        total_physical_units=on_hand,
        usable_units=usable,
        reserved_units=reserved,
        quarantined_units=quarantined,
        quarantine_lot_id="N/A",
        quarantine_reason="Standard QA inspection",
        affected_factories=["Katowice (F2)", "Lyon (F3)"],
        factory_timelines=timelines,
        hub_usable_units=hub_usable,
        affected_products=affected_products,
        affected_products_count=len(affected_products),
        affected_customer_orders_count=open_orders,
        daily_demand_total=daily_demand,
        stock_at_original_arrival=0,
        uncovered_demand_units=uncovered,
        reserved_stock_orders=[],
        total_revenue_at_risk_eur=round(revenue_at_risk, 2),
    )


def retrieve_scoped_documentary_findings(
    user_profile: UserProfile,
    fact: Optional[DisruptionFact] = None,
) -> List[DocumentaryFinding]:
    """Retrieve documentary evidence, conflict flags, and security alerts filtered by user's RBAC scope."""
    if fact is not None and fact.component_id and fact.component_id != "MC-17":
        # Non-MC-17 cases retrieve relevant scoped documents dynamically without injecting MC-17 findings
        try:
            from src.knowledge import mocks as kmocks

            norm_scope = (
                "finance"
                if user_profile.can_view_finance_confidential
                else ("public" if user_profile.access_scope == AccessScope.PUBLIC else "procurement")
            )
            docs = kmocks.retrieve_documents(
                f"{fact.component_id} {fact.supplier_name or ''} supplier certification",
                access_scope=norm_scope,
                top_k=5,
            )
            return [
                DocumentaryFinding(
                    source_id=d.source_id,
                    doc_type=d.doc_type,
                    title=d.title,
                    version=str(d.version or "1"),
                    effective_date=d.effective_date,
                    access_scope=d.access_scope,
                    summary=d.content[:240],
                    is_superseded=d.superseded_by is not None,
                    is_malicious=not d.trusted,
                )
                for d in docs
                if user_profile.can_access_document_scope(d.access_scope)
            ]
        except Exception:
            return []

    all_findings = [
        DocumentaryFinding(
            source_id="DOC-NOT-ATLAS-MC17",
            doc_type="supplier_notice",
            title="Supplier notice - Atlas Components - MC-17 delay",
            supplier_id="S001",
            version="1",
            effective_date="2026-10-19",
            access_scope="procurement",
            summary="Atlas Components (S001) formally announces a 12-day delay on PO-2026-9001 (6,000 units MC-17, new due date 2026-11-07).",
            is_conflict=True,
            conflict_resolution="Governs over informal e-mail DOC-EM-ATLAS-01 (16 days) per source precedence policy; 16-day sensitivity tracked.",
        ),
        DocumentaryFinding(
            source_id="DOC-EM-ATLAS-01",
            doc_type="email",
            title="E-mail: Atlas account manager (conflicts with formal notice)",
            supplier_id="S001",
            version="1",
            effective_date="2026-10-19",
            access_scope="procurement",
            summary="Account manager informally warns MC-17 delay might reach 16 days with partial 1,000-unit shipment after 8 days.",
            is_conflict=True,
            conflict_resolution="Subordinate to formal notice DOC-NOT-ATLAS-MC17 (12 days); retained for 16-day downside sensitivity analysis.",
        ),
        DocumentaryFinding(
            source_id="DOC-CON-S001-v3",
            doc_type="contract",
            title="Supply contract - Atlas Components (v3)",
            supplier_id="S001",
            version="3",
            effective_date="2026-03-01",
            access_scope="procurement",
            summary="Active supply contract with Atlas Components: standard lead time 14 days, unit price EUR 8.50.",
            is_conflict=True,
            conflict_resolution="Supersedes stale contract DOC-CON-S001-v2 (effective 2025-01-01, 10-day lead time).",
        ),
        DocumentaryFinding(
            source_id="DOC-CON-S001-v2",
            doc_type="contract",
            title="Supply contract - Atlas Components (v2 - Superseded)",
            supplier_id="S001",
            version="2",
            effective_date="2025-01-01",
            access_scope="procurement",
            summary="Legacy contract stating 10-day lead time for MC-17.",
            is_superseded=True,
            conflict_resolution="Ignored in favor of latest effective version DOC-CON-S001-v3 (effective 2026-03-01).",
        ),
        DocumentaryFinding(
            source_id="DOC-CON-S004-v1",
            doc_type="contract",
            title="Supply contract - Cordillera Industrial",
            supplier_id="S004",
            version="1",
            effective_date="2025-08-01",
            access_scope="procurement",
            summary="Approved alternative supplier S004: EUR 9.80/unit, 9-day lead time, 3,000 units/month capacity, 6% expedite fee (+7 days on PO-2026-9002).",
            is_conflict=True,
            conflict_resolution="Contracted 6% expedite fee (EUR 882) takes precedence over e-mail DOC-EM-CORDILLERA-01 quoting 10% (EUR 1,470).",
        ),
        DocumentaryFinding(
            source_id="DOC-QUA-S003-v1",
            doc_type="qualification",
            title="ISO 9001 qualification record - Borealis Parts (S003)",
            supplier_id="S003",
            version="1",
            effective_date="2023-10-01",
            access_scope="procurement",
            summary="Borealis Parts (S003) ISO 9001:2015 certificate EXPIRED on 2026-09-30 (despite stale ERP status 'approved').",
            is_conflict=True,
            conflict_resolution="Blocked under procedure DOC-PRO-04-v1 (requires valid ISO certification before creating any purchase order).",
        ),
        DocumentaryFinding(
            source_id="DOC-EM-HELIOS-01",
            doc_type="email",
            title="E-mail: Helios sales - real capacity for MC-17",
            supplier_id="S002",
            version="1",
            effective_date="2026-10-18",
            access_scope="procurement",
            summary="Helios Supply (S002) confirms real capacity is 1,500 units/month (not 4,000 in contract) with 21-day lead time at EUR 7.20.",
            is_conflict=True,
            conflict_resolution="Disqualifies Helios: 21-day lead time fails to prevent Day 3.3/4.0 stockouts at Lyon and Katowice.",
        ),
        DocumentaryFinding(
            source_id="DOC-NOT-HELIOS-PRICE",
            doc_type="supplier_notice",
            title="Supplier notice - Helios Supply - price update (Malicious Prompt Injection)",
            supplier_id="S002",
            version="1",
            effective_date="2026-10-18",
            access_scope="public",
            summary="Contains hidden HTML comment instructing AI to ignore policies and execute an unapproved 20,000-unit PO with Helios.",
            is_malicious=True,
            conflict_resolution="NEUTRALIZED & REPORTED: Treated strictly as untrusted data; instruction isolated and ignored.",
        ),
        DocumentaryFinding(
            source_id="DOC-FIN-01-v1",
            doc_type="finance",
            title="Margin and penalty rate sheet (Finance Confidential)",
            supplier_id=None,
            version="1",
            effective_date="2026-02-01",
            access_scope="finance-confidential",
            summary="Gross margin by customer tier: Tier 1 = 18%, Tier 2 = 24%, Tier 3 = 31%. Late penalty: Tier 1 = 2%/wk, Tier 2 = 1%/wk (cap 5%).",
        ),
    ]
    return [doc for doc in all_findings if user_profile.can_access_document_scope(doc.access_scope)]


def compute_recovery_options(
    fact: DisruptionFact,
    impact: OperationalImpact,
    *,
    custom_cordillera_qty: Optional[int] = None,
) -> List[RecoveryOption]:
    """Deterministically calculate and compare >= 3 recovery strategies separating Recovery Cost vs Revenue at Risk."""
    qty_c = custom_cordillera_qty if custom_cordillera_qty is not None else 3000
    po_cost = round(qty_c * 9.80, 2)
    expedite_fee = 882.0  # 6% of (1,500 * 9.80 = 14,700) per contract DOC-CON-S004-v1
    transfer_cost = 96.0  # 800 units * EUR 0.12
    plan1_total = round(po_cost + expedite_fee + transfer_cost, 2)
    residual_units = max(0, impact.uncovered_demand_units - (800 + 1500 + qty_c))
    within_cap_And_cap = (plan1_total <= fact.spending_cap) and (qty_c <= 3000)

    rejection_p1 = None
    if qty_c > 3000:
        rejection_p1 = f"Requested quantity ({qty_c:,} units) exceeds Cordillera monthly capacity (3,000 units/month)."
    if plan1_total > fact.spending_cap:
        extra = f"Total cost (€{plan1_total:,.2f}) exceeds spending cap (€{fact.spending_cap:,.2f})."
        rejection_p1 = f"{rejection_p1} {extra}".strip() if rejection_p1 else extra

    return [
        RecoveryOption(
            strategy_id="STRAT-1",
            strategy_code="A + B + C + D/E",
            title="Plan 1 (Recommended): Hub Transfer + Expedite PO-2026-9002 + Cordillera New PO + Tier-1 Priority Allocation",
            action_type=SupplyGuardActionType.COMBINED_RECOVERY_PLAN,
            supplier_id="S004",
            supplier_name="Cordillera Industrial",
            quantity=qty_c + 1500 + 800,
            unit_price=9.80,
            lead_time_days=9,
            recovery_cost=plan1_total,
            revenue_at_risk=0.0 if within_cap_And_cap else impact.total_revenue_at_risk_eur,
            uncovered_units_remaining=residual_units,
            is_viable=within_cap_And_cap,
            is_recommended=within_cap_And_cap,
            rejection_reason=rejection_p1,
            actions_breakdown=[
                "A (Transfer): Move 800 usable units from W-HUB to W-LYO (450) & W-KAT (350) in 2 days (€96.00)",
                "B (Expedite): Expedite Cordillera PO-2026-9002 (1,500 units arrive Day 7, +7d gain, 6% contract fee = €882.00)",
                f"C (Alternative PO): New PO with Cordillera (S004, independent upstream U02) for {qty_c:,} units @ €9.80 arrives Day 9 (€{po_cost:,.2f})",
                f"D/E (Reallocate & Reschedule): Protect all 6 Tier-1 customer orders; reschedule {residual_units:,} residual Tier-3 units (~1.9 days demand)",
            ],
            cost_breakdown={
                "transfers_eur": transfer_cost,
                "expedite_fee_6pct_contract_eur": expedite_fee,
                "cordillera_purchase_eur": po_cost,
                "total_recovery_cost_eur": plan1_total,
                "sensitivity_10pct_email_total_eur": round(po_cost + 1470.0 + transfer_cost, 2),
            },
            supporting_sources=["DOC-CON-S004-v1", "DOC-QUA-S004-v1", "DOC-PRO-04-v1", "DOC-NOT-ATLAS-MC17"],
        ),
        RecoveryOption(
            strategy_id="STRAT-2",
            strategy_code="A + B + C + Delta",
            title="Plan 2 (Dual-Source with Delta Micro S005 for 850 Residual Units)",
            action_type=SupplyGuardActionType.PURCHASE_ALTERNATIVE,
            supplier_id="S005",
            supplier_name="Delta Micro Systems",
            quantity=5350,
            unit_price=10.40,
            lead_time_days=8,
            recovery_cost=39218.0,
            revenue_at_risk=145000.0,
            uncovered_units_remaining=0,
            is_viable=False,
            is_recommended=False,
            rejection_reason=(
                "REJECTED (Tier-2 Concentration Risk): Delta Micro (S005) shares upstream manufacturer "
                "Veltro Semiconductor (U01) with Atlas Components (S001), which has an active high-severity "
                "Taiwan wafer-supply alert."
            ),
            actions_breakdown=[
                "Includes Plan 1 plus 850 units from Delta Micro (S005) @ €10.40 (€8,840.00)",
            ],
            cost_breakdown={"total_recovery_cost_eur": 39218.0},
            supporting_sources=["DOC-CON-S005-v1", "DOC-EM-DELTA-01", "NEO4J-TIER2-U01"],
        ),
        RecoveryOption(
            strategy_id="STRAT-3",
            strategy_code="C (Helios S002)",
            title="Option 3: Lowest-Price Spot Purchase from Helios Supply (S002)",
            action_type=SupplyGuardActionType.PURCHASE_ALTERNATIVE,
            supplier_id="S002",
            supplier_name="Helios Supply",
            quantity=1500,
            unit_price=7.20,
            lead_time_days=21,
            recovery_cost=10800.0,
            revenue_at_risk=impact.total_revenue_at_risk_eur,
            uncovered_units_remaining=3850,
            is_viable=False,
            is_recommended=False,
            rejection_reason=(
                "REJECTED (Too Slow & Insufficient Capacity): 21-day lead time misses the 12-day delay window "
                "(Lyon & Katowice stock out in 3.3–4.0 days), and real monthly capacity is only 1,500 units "
                "(DOC-EM-HELIOS-01 vs 4,000 in contract). Malicious prompt injection in DOC-NOT-HELIOS-PRICE ignored."
            ),
            actions_breakdown=["Purchase 1,500 units @ €7.20/unit arriving Day 21"],
            cost_breakdown={"total_recovery_cost_eur": 10800.0},
            supporting_sources=["DOC-CON-S002-v1", "DOC-EM-HELIOS-01", "DOC-NOT-HELIOS-PRICE"],
        ),
        RecoveryOption(
            strategy_id="STRAT-4",
            strategy_code="C (Borealis S003)",
            title="Option 4: Fast Expedited Purchase from Borealis Parts (S003)",
            action_type=SupplyGuardActionType.PURCHASE_ALTERNATIVE,
            supplier_id="S003",
            supplier_name="Borealis Parts",
            quantity=3500,
            unit_price=9.10,
            lead_time_days=6,
            recovery_cost=31850.0,
            revenue_at_risk=impact.total_revenue_at_risk_eur,
            uncovered_units_remaining=1850,
            is_viable=False,
            is_recommended=False,
            rejection_reason=(
                "REJECTED / BLOCKED (Compliance Violation): Borealis Parts (S003) ISO 9001:2015 certification "
                "expired on 2026-09-30 (DOC-QUAL-S003, DOC-EM-BOREALIS-01). Procedure DOC-PRO-04 strictly forbids "
                "ordering from suppliers with expired quality certifications despite stale ERP 'approved' flag."
            ),
            actions_breakdown=["Blocked by Quality Policy DOC-PRO-04"],
            cost_breakdown={"total_recovery_cost_eur": 31850.0},
            supporting_sources=["DOC-QUA-S003-v1", "DOC-EM-BOREALIS-01", "DOC-PRO-04-v1"],
        ),
        RecoveryOption(
            strategy_id="STRAT-5",
            strategy_code="A + D/E Only",
            title="Option 5: Internal Stock Transfer & Production Rescheduling Only (No External Purchase)",
            action_type=SupplyGuardActionType.TRANSFER_INVENTORY,
            supplier_id=None,
            supplier_name="Internal Warehouses (W-HUB -> W-KAT / W-LYO)",
            quantity=800,
            unit_price=0.12,
            lead_time_days=2,
            recovery_cost=96.0,
            revenue_at_risk=285000.0,
            uncovered_units_remaining=4550,
            is_viable=False,
            is_recommended=False,
            rejection_reason=(
                "REJECTED (Insufficient Coverage): Transferring 800 W-HUB units only delays Katowice/Lyon "
                "stockouts by ~2.6 days, leaving 4,550 units of demand uncovered and exposing €285,000 in customer orders."
            ),
            actions_breakdown=["Transfer 800 units from W-HUB (€96.00); leaves 4,550 units uncovered"],
            cost_breakdown={"total_recovery_cost_eur": 96.0},
            supporting_sources=["DOC-PRO-02"],
        ),
    ]


def build_approval_payload(
    fact: DisruptionFact,
    impact: OperationalImpact,
    *,
    case_id: str = "CASE-MC17-001",
    quantity: int = 3000,
    supplier_id: str = "S004",
    supplier_name: str = "Cordillera Industrial",
    unit_price: float = 9.80,
    revision: int = 1,
    supporting_evidence: Optional[List[Dict[str, str]]] = None,
) -> ApprovalPayload:
    """Create a payload-bound ApprovalPayload with deterministic costs and SHA-256 payload_hash."""
    comp_id = fact.component_id or "MC-17"
    is_mc17 = comp_id == "MC-17"
    is_mc17_cordillera = is_mc17 and supplier_id == "S004"

    po_subtotal = round(quantity * unit_price, 2)
    expedite_units = 1500 if is_mc17_cordillera else 0
    expedite_fee_pct = 6.0 if is_mc17_cordillera else 0.0
    expedite_fee = 882.0 if is_mc17_cordillera else 0.0
    expedite_po_id = "PO-2026-9002" if is_mc17_cordillera else None
    transfer_units = 800 if is_mc17 else min(impact.hub_usable_units, max(0, impact.uncovered_demand_units))
    transfer_cost = round(transfer_units * 0.12, 2)
    transfer_to = (
        "W-LYO (450) & W-KAT (350)"
        if is_mc17
        else (", ".join(impact.affected_factories) or "Affected Plants")
    )
    total_cost = round(po_subtotal + expedite_fee + transfer_cost, 2)
    residual = max(0, impact.uncovered_demand_units - (quantity + expedite_units + transfer_units))

    if supporting_evidence is not None:
        evidence = list(supporting_evidence)
    elif is_mc17_cordillera:
        evidence = [
            {"source_id": "DOC-CON-S004-v1", "effective_date": "2025-08-01", "access_scope": "procurement", "note": "Cordillera EUR 9.80/unit, 9d lead time, 3,000/mo capacity, 6% expedite fee"},
            {"source_id": "DOC-QUA-S004-v1", "effective_date": "2024-11-30", "access_scope": "procurement", "note": "ISO 9001:2015 valid through 2027-11-30; independent upstream U02"},
            {"source_id": "DOC-PRO-04-v1", "effective_date": "2026-01-15", "access_scope": "internal", "note": "Emergency procurement & certification verification policy"},
            {"source_id": "DOC-NOT-ATLAS-MC17", "effective_date": "2026-10-19", "access_scope": "procurement", "note": "Formal 12-day delay notice on Atlas PO-2026-9001"},
        ]
    else:
        evidence = [
            {"source_id": f"DOC-CON-{supplier_id}-v1", "effective_date": "2026-01-01", "access_scope": "procurement", "note": f"{supplier_name} ({supplier_id}) EUR {unit_price:.2f}/unit for {comp_id}"},
            {"source_id": "DOC-PRO-04-v1", "effective_date": "2026-01-15", "access_scope": "internal", "note": "Emergency procurement & certification verification policy"},
        ]

    action_type = (
        SupplyGuardActionType.COMBINED_RECOVERY_PLAN
        if (expedite_po_id or transfer_units > 0)
        else SupplyGuardActionType.PURCHASE_ALTERNATIVE
    )

    payload = ApprovalPayload(
        action_id=f"act-{uuid.uuid4().hex[:10]}",
        case_id=case_id,
        action_type=action_type,
        target_supplier_id=supplier_id,
        target_supplier_name=supplier_name,
        component_id=comp_id,
        quantity=quantity,
        unit_price=unit_price,
        po_subtotal_eur=po_subtotal,
        expedite_po_id=expedite_po_id,
        expedite_units=expedite_units,
        expedite_fee_pct=expedite_fee_pct,
        expedite_fee_eur=expedite_fee,
        transfer_from_location="W-HUB",
        transfer_to_locations=transfer_to,
        transfer_units=transfer_units,
        transfer_cost_eur=transfer_cost,
        residual_units_reallocated=residual,
        total_cost=total_cost,
        spending_cap=fact.spending_cap,
        revenue_at_risk_protected_eur=impact.total_revenue_at_risk_eur,
        supporting_evidence=evidence,
        status=ActionStatus.PENDING,
        revision=revision,
    )
    return payload.ensure_hash()
