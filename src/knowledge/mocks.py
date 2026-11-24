"""Mock tools with the final signatures, for the Workflow skeleton (no databases needed)."""
from .models import GraphResult, Outage, PolicyResult


def retrieve_policy(query: str, application: str | None = None) -> PolicyResult | None:
    return PolicyResult(
        text="Every credential reset requires explicit human engineer approval.",
        doc_id="POL-001", effective_date="2026-09-01", source="POL-001_password_reset_v2.md",
    )


def check_graph(application: str) -> GraphResult:
    return GraphResult(
        application=application, dependencies=["Identity Provider (SSO)"],
        active_outages=["Identity Provider (SSO)"],
        outages=[Outage(
            outage_id="OUT-2026-01", service="Identity Provider (SSO)",
            title="Identity Provider (SSO) Token Validation Degradation", severity="critical",
            started_at="2026-11-13T14:30:00Z", summary="Intermittent SSO authentication failures.",
        )],
    )


# --- SupplyGuard mocks (#73): same signatures as tools.py, read the support-data files directly ---
# Real data, no database: Workflow can build and test the skeleton before the stack runs.
# Not mocked: Neo4j traversal (the CSVs hold the same edges) and vector ranking (word overlap here).
import re  # noqa: E402
from datetime import date, timedelta  # noqa: E402

from . import data_quality as dq  # noqa: E402
from . import supply_graph  # noqa: E402
from .ingest_documents import chunks  # noqa: E402
from .models import (  # noqa: E402
    AffectedProduct, BOMResult, ClaimConflict, CustomerOrderAtRisk, DocumentResult, InventoryLocation,
    InventoryStatusResult, OpenPurchaseOrder, QuarantineLot, Reservation, SharedUpstream,
    SupplierGraphResult, SupplierOption,
)

_DOCUMENT_SCOPES = {
    "public": ["public"],
    "procurement": ["public", "internal", "procurement"],
    "finance": ["public", "internal", "procurement", "finance-confidential"],
}


def query_inventory(component_id: str, factory_id: str | None = None) -> InventoryStatusResult:
    cid = dq.canonical_component_id(component_id)
    factory = {loc["location_id"]: loc["factory_id"] or None for loc in dq.table("locations.csv")}
    rows = [r for r in dq.table("inventory.csv")
            if r["component_id"] == cid and (factory_id is None or factory[r["location_id"]] == factory_id)]
    locations = [InventoryLocation(
        location_id=r["location_id"], factory_id=factory[r["location_id"]], on_hand=int(r["on_hand"]),
        reserved=int(r["reserved"]), quarantined=int(r["quarantined"]), usable=int(r["usable"]),
        last_counted_date=r["last_counted_date"],
        stale_count=(dq.SCENARIO_DATE - date.fromisoformat(r["last_counted_date"])).days > dq.STALE_COUNT_DAYS,
    ) for r in sorted(rows, key=lambda r: r["location_id"])]
    ids = {loc.location_id for loc in locations}
    return InventoryStatusResult(
        component_id=cid,
        total_on_hand=sum(r.on_hand for r in locations), total_reserved=sum(r.reserved for r in locations),
        total_quarantined=sum(r.quarantined for r in locations), total_usable=sum(r.usable for r in locations),
        locations=locations,
        reservations=sorted((Reservation(location_id=r["location_id"], customer_order_id=r["customer_order_id"],
                                         reserved_qty=int(r["reserved_qty"]))
                             for r in dq.table("reservations.csv") if r["component_id"] == cid and r["location_id"] in ids),
                            key=lambda r: r.customer_order_id),
        quarantine_lots=[QuarantineLot(lot_id=r["lot_id"], location_id=r["location_id"], qty=int(r["qty"]),
                                       reason=r["reason"], release_expected=r["release_expected"])
                         for r in dq.table("quarantine_lots.csv") if r["component_id"] == cid and r["location_id"] in ids],
    )


def query_bom(component_id: str, horizon_days: int = 60) -> BOMResult:
    cid = dq.canonical_component_id(component_id)
    qty = {b["product_id"]: int(b["qty_per_unit"]) for b in dq.table("bill_of_materials.csv") if b["component_id"] == cid}
    products = [AffectedProduct(product_id=p["product_id"], name=p["name"], factory_id=p["factory_id"],
                                qty_per_unit=qty[p["product_id"]])
                for p in dq.table("products.csv") if p["product_id"] in qty]
    until = (dq.SCENARIO_DATE + timedelta(days=horizon_days)).isoformat()
    orders = sorted((o for o in dq.table("customer_orders.csv")
                     if o["product_id"] in qty and o["status"] == "open" and o["due_date"] <= until),
                    key=lambda o: (o["due_date"], o["order_id"]))
    weekly: dict[str, dict[str, int]] = {}
    for s in dq.table("production_schedule.csv"):
        if s["product_id"] in qty:
            week = weekly.setdefault(s["factory_id"], {})
            week[s["week_start"]] = week.get(s["week_start"], 0) + int(s["planned_units"]) * qty[s["product_id"]]
    return BOMResult(
        component_id=cid, products=sorted(products, key=lambda p: p.product_id), horizon_days=horizon_days,
        weekly_demand={f: dict(sorted(w.items())) for f, w in sorted(weekly.items())},
        open_orders=[CustomerOrderAtRisk(
            order_id=o["order_id"], customer_id=o["customer_id"], product_id=o["product_id"], qty=int(o["qty"]),
            due_date=o["due_date"], revenue_eur=float(o["revenue_eur"]), priority_tier=int(o["customer_priority_tier"]),
            late_penalty_pct_per_week=float(o["late_penalty_pct_per_week_capped5"])) for o in orders],
    )


def query_supplier_graph(component_id: str, max_depth: int = 2) -> SupplierGraphResult:
    cid = dq.canonical_component_id(component_id)
    suppliers = {s["supplier_id"]: s for s in dq.table("suppliers.csv")}
    upstream = {u["upstream_id"]: u["name"] for u in dq.table("upstream_manufacturers.csv")}
    contract = {}  # rel_supplies.csv carries the governing contract and its date
    for r in supply_graph.read(supply_graph.GRAPH / "rel_supplies.csv"):
        if r["END_ID"] == cid:
            contract[r["START_ID"]] = (r["sourceId"], r["effectiveDate"])
    conflicts: dict[str, list[ClaimConflict]] = {}
    for c in dq.conflicting_claims():
        conflicts.setdefault(c["supplier_id"], []).append(ClaimConflict(
            attribute=c["attribute"], winner_source_id=c["winner"], value=c["value"], sources=c["sources"]))
    deep = max_depth >= 2
    options = []
    for sc in sorted((r for r in dq.table("supplier_components.csv") if r["component_id"] == cid),
                     key=lambda r: r["supplier_id"]):
        s = suppliers[sc["supplier_id"]]
        u = s["upstream_manufacturer_id"] or None
        options.append(SupplierOption(
            supplier_id=s["supplier_id"], name=s["name"], lead_time_days=int(sc["lead_time_days"]),
            unit_price_eur=float(sc["unit_price_eur"]), monthly_capacity_units=int(sc["monthly_capacity_units"]),
            approved_source=sc["approved_source"], certification_valid=dq.certification_valid(s["supplier_id"]),
            certification_expiry=s["certification_expiry"] or None,
            upstream_id=u if deep else None, upstream_name=upstream.get(u) if deep else None,
            open_purchase_orders=[OpenPurchaseOrder(
                po_id=p["po_id"], qty=int(p["qty"]), unit_price_eur=float(p["unit_price_eur"]),
                promised_date=p["promised_date"], expedite_allowed=p["expedite_allowed"] == "yes",
                expedite_fee_pct=float(p["expedite_fee_pct"] or 0), expedite_days_gain=int(p["expedite_days_gain"] or 0))
                for p in dq.table("purchase_orders.csv")
                if p["supplier_id"] == s["supplier_id"] and p["component_id"] == cid and p["status"] == "open"],
            conflicts=conflicts.get(s["supplier_id"], []),
            source_id=contract.get(s["supplier_id"], ("", ""))[0], effective_date=contract.get(s["supplier_id"], ("", ""))[1],
        ))
    shared = [SharedUpstream(upstream_id=g["upstream_id"], supplier_ids=g["supplier_ids"])
              for g in dq.shared_upstream(cid)] if deep else []
    return SupplierGraphResult(component_id=cid, suppliers=options, shared_upstream=shared)


def retrieve_documents(query: str, access_scope: str = "procurement", top_k: int = 5) -> list[DocumentResult]:
    allowed = _DOCUMENT_SCOPES[str(getattr(access_scope, "value", access_scope))]
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    prec = dq.document_precedence()
    scored = []
    for c in chunks():
        if c["access_scope"] not in allowed:
            continue
        text = set(re.findall(r"[a-z0-9]+", f"{c['title']} {c['content']}".lower()))
        scored.append((len(words & text) / (len(words) or 1), c))
    docs = [DocumentResult(
        source_id=c["source_id"], doc_type=c["doc_type"], title=c["title"], version=c["version"],
        effective_date=c["effective_date"], access_scope=c["access_scope"], content=c["content"], score=score,
        trusted=c["trusted"], security_flags=c["security_flags"], precedence_rank=prec[c["source_id"]]["rank"],
        superseded_by=prec[c["source_id"]]["superseded_by"],
    ) for score, c in sorted(scored, key=lambda x: -x[0])[:top_k]]
    return sorted(docs, key=lambda d: (d.superseded_by is not None, -d.score))
