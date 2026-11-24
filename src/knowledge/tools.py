"""Tools called by the Workflow nodes: retrieve_policy and check_graph.

The plain functions are wrapped as LangChain tools at the end of this module, so that every call
shows up as a tool run in LangSmith.
"""
from langchain_core.tools import StructuredTool

from .common import embed, neo4j_driver, pg, vec
from .models import GraphResult, Outage, PolicyResult

# Latest version per doc_id wins (never a future-dated one), THEN rank by similarity,
# so an outdated version can never outrank the current one.
POLICY_SQL = """
WITH latest AS (
    SELECT doc_id, max(effective_date) AS effective_date
    FROM policy_chunks WHERE effective_date <= current_date GROUP BY doc_id
)
SELECT c.content, c.doc_id, c.effective_date, c.source, (c.embedding <=> %s::vector) AS dist
FROM policy_chunks c JOIN latest USING (doc_id, effective_date)
ORDER BY dist LIMIT 1
"""

# Open outages on the services the application depends on. Parameterised: no string building.
GRAPH_CYPHER = """
MATCH (a:Application) WHERE toLower(a.name) CONTAINS toLower($name)
WITH a ORDER BY CASE WHEN toLower(a.name) = toLower($name) THEN 0 ELSE 1 END, a.name LIMIT 1
OPTIONAL MATCH (a)-[:DEPENDS_ON]->(s:Service)
OPTIONAL MATCH (s)-[:HAS_OUTAGE]->(o:Outage {status: 'OPEN'})
RETURN a.name AS application, collect(DISTINCT s.name) AS dependencies,
       collect(DISTINCT CASE WHEN o IS NULL THEN NULL ELSE {
           outage_id: o.outage_id, service: s.name, title: o.title,
           severity: o.severity, started_at: o.started_at, summary: o.summary} END) AS outages
"""

SERVICE_CYPHER = """
MATCH (s:Service) WHERE toLower(s.name) CONTAINS toLower($name)
WITH s ORDER BY CASE WHEN toLower(s.name) = toLower($name) THEN 0 ELSE 1 END, s.name LIMIT 1
OPTIONAL MATCH (s)-[:HAS_OUTAGE]->(o:Outage {status: 'OPEN'})
RETURN s.name AS application, [s.name] AS dependencies,
       collect(DISTINCT CASE WHEN o IS NULL THEN NULL ELSE {
           outage_id: o.outage_id, service: s.name, title: o.title,
           severity: o.severity, started_at: o.started_at, summary: o.summary} END) AS outages
"""


def retrieve_policy(query: str, application: str | None = None, max_distance: float = 0.74) -> PolicyResult | None:
    """Best-matching chunk of the current version of each policy; None if nothing is indexed or matches.

    `application` only sharpens the query text (policies are not tagged per application).
    """
    if application:
        query = f"{application}: {query}"
    v = vec(embed([query])[0])
    with pg() as conn:
        row = conn.execute(POLICY_SQL, (v,)).fetchone()
    if not row or (len(row) > 4 and row[4] is not None and row[4] > max_distance):
        return None
    return PolicyResult(text=row[0], doc_id=row[1], effective_date=row[2].isoformat(), source=row[3])


def check_graph(application: str) -> GraphResult:
    """Dependencies and active outages of an application or direct service; found=False if unknown."""
    name = application.strip()
    if not name:
        return GraphResult(application=application, found=False)
    with neo4j_driver() as driver:
        records, _, _ = driver.execute_query(GRAPH_CYPHER, name=name)
        if not records:
            records, _, _ = driver.execute_query(SERVICE_CYPHER, name=name)
    if not records:
        return GraphResult(application=name, found=False)
    r = records[0]
    return GraphResult(
        application=r["application"],
        found=True,
        dependencies=r["dependencies"],
        active_outages=sorted({o["service"] for o in r["outages"]}),
        outages=[Outage(**o) for o in r["outages"]],
    )


retrieve_policy_tool = StructuredTool.from_function(
    func=retrieve_policy,
    name="retrieve_policy",
    description="Return the current version of the policy that best matches the query, with doc_id and effective_date.",
)

check_graph_tool = StructuredTool.from_function(
    func=check_graph,
    name="check_graph",
    description="Return the services an application depends on and any open outages on them.",
)


# --- SupplyGuard Knowledge tools (#73) ---------------------------------------------------------
# Signatures from docs/ARCHITECTURE_CONTRACTS.md section 4. Every result carries its sources.
from datetime import timedelta  # noqa: E402

from . import data_quality as dq  # noqa: E402
from . import incident_memory, ingest_documents, supply_graph  # noqa: E402
from .models import (  # noqa: E402
    AffectedProduct, BOMResult, ClaimConflict, CustomerOrderAtRisk, DocumentResult, InventoryLocation,
    InventoryStatusResult, OpenPurchaseOrder, QuarantineLot, Reservation, SharedUpstream,
    SupplierGraphResult, SupplierOption,
)

# Contract AccessScope -> document access_scope values a user of that scope may read
# (the same sets as document_scopes in support-data/config/users.csv).
DOCUMENT_SCOPES = {
    "public": ["public"],
    "procurement": ["public", "internal", "procurement"],
    "finance": ["public", "internal", "procurement", "finance-confidential"],
}


def _rows(sql: str, params: tuple) -> list[dict]:
    with pg() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _component(component_id: str) -> str:
    cid = dq.canonical_component_id(component_id)
    if not cid:
        raise ValueError(f"not a component id: {component_id!r}")
    return cid


def _scopes(access_scope) -> list[str]:
    return DOCUMENT_SCOPES[str(getattr(access_scope, "value", access_scope))]  # enum or plain string


def query_inventory(component_id: str, factory_id: str | None = None) -> InventoryStatusResult:
    """Stock per location split into on hand, reserved, quarantined and usable, with reservations and quarantine lots."""
    cid = _component(component_id)
    locs = _rows(
        """SELECT i.location_id, l.factory_id, i.on_hand, i.reserved, i.quarantined, i.usable, i.last_counted_date
           FROM inventory i JOIN locations l USING (location_id)
           WHERE i.component_id = %s AND (%s::text IS NULL OR l.factory_id = %s) ORDER BY i.location_id""",
        (cid, factory_id, factory_id),
    )
    ids = [r["location_id"] for r in locs]
    res = _rows(
        """SELECT location_id, customer_order_id, reserved_qty FROM reservations
           WHERE component_id = %s AND location_id = ANY(%s) ORDER BY customer_order_id""", (cid, ids))
    lots = _rows(
        """SELECT lot_id, location_id, qty, reason, release_expected FROM quarantine_lots
           WHERE component_id = %s AND location_id = ANY(%s)""", (cid, ids))
    locations = [
        InventoryLocation(**{**r, "last_counted_date": r["last_counted_date"].isoformat(),
                             "stale_count": (dq.SCENARIO_DATE - r["last_counted_date"]).days > dq.STALE_COUNT_DAYS})
        for r in locs
    ]
    return InventoryStatusResult(
        component_id=cid,
        total_on_hand=sum(r.on_hand for r in locations), total_reserved=sum(r.reserved for r in locations),
        total_quarantined=sum(r.quarantined for r in locations), total_usable=sum(r.usable for r in locations),
        locations=locations, reservations=[Reservation(**r) for r in res],
        quarantine_lots=[QuarantineLot(**r) for r in lots],
    )


def query_bom(component_id: str, horizon_days: int = 60) -> BOMResult:
    """Products using the component, open customer orders on them due within the horizon, weekly component demand per factory."""
    cid = _component(component_id)
    products = _rows(
        """SELECT p.product_id, p.name, p.factory_id, b.qty_per_unit FROM bill_of_materials b JOIN products p USING (product_id)
           WHERE b.component_id = %s ORDER BY p.product_id""", (cid,))
    pids = [p["product_id"] for p in products]
    orders = _rows(
        """SELECT order_id, customer_id, product_id, qty, due_date::text AS due_date, revenue_eur::float AS revenue_eur,
                  customer_priority_tier AS priority_tier,
                  late_penalty_pct_per_week_capped5::float AS late_penalty_pct_per_week
           FROM customer_orders WHERE product_id = ANY(%s) AND status = 'open' AND due_date <= %s
           ORDER BY due_date, order_id""",
        (pids, dq.SCENARIO_DATE + timedelta(days=horizon_days)))
    demand = _rows(
        """SELECT s.factory_id, s.week_start::text AS week_start, sum(s.planned_units * b.qty_per_unit)::int AS units
           FROM production_schedule s JOIN bill_of_materials b ON b.product_id = s.product_id AND b.component_id = %s
           GROUP BY s.factory_id, s.week_start ORDER BY s.factory_id, s.week_start""", (cid,))
    weekly: dict[str, dict[str, int]] = {}
    for d in demand:
        weekly.setdefault(d["factory_id"], {})[d["week_start"]] = d["units"]
    return BOMResult(component_id=cid, products=[AffectedProduct(**p) for p in products],
                     open_orders=[CustomerOrderAtRisk(**o) for o in orders], horizon_days=horizon_days,
                     weekly_demand=weekly)


def query_supplier_graph(component_id: str, max_depth: int = 2) -> SupplierGraphResult:
    """Suppliers of the component: lead time, price, capacity, certification, open POs, document conflicts; tier-2 upstream when max_depth >= 2."""
    cid = _component(component_id)
    deps = supply_graph.component_dependencies(cid)
    pos = _rows(
        """SELECT supplier_id, po_id, qty, unit_price_eur::float AS unit_price_eur, promised_date::text AS promised_date,
                  coalesce(expedite_allowed, false) AS expedite_allowed,
                  coalesce(expedite_fee_pct, 0)::float AS expedite_fee_pct,
                  coalesce(expedite_days_gain, 0) AS expedite_days_gain
           FROM purchase_orders WHERE component_id = %s AND status = 'open' ORDER BY po_id""", (cid,))
    conflicts: dict[str, list[ClaimConflict]] = {}
    for c in dq.conflicting_claims():
        conflicts.setdefault(c["supplier_id"], []).append(ClaimConflict(
            attribute=c["attribute"], winner_source_id=c["winner"], value=c["value"], sources=c["sources"]))
    approved = {r["supplier_id"]: r["approved_source"]
                for r in dq.table("supplier_components.csv") if r["component_id"] == cid}
    deep = max_depth >= 2
    suppliers = [
        SupplierOption(
            supplier_id=s["supplier_id"], name=s["name"], lead_time_days=s["lead_time_days"],
            unit_price_eur=s["unit_price_eur"], monthly_capacity_units=s["monthly_capacity_units"],
            approved_source=approved.get(s["supplier_id"]),
            certification_valid=dq.certification_valid(s["supplier_id"]),
            certification_expiry=s["certification_expiry"],
            upstream_id=s["upstream_id"] if deep else None, upstream_name=s["upstream_name"] if deep else None,
            open_purchase_orders=[OpenPurchaseOrder(**{k: v for k, v in p.items() if k != "supplier_id"})
                                  for p in pos if p["supplier_id"] == s["supplier_id"]],
            conflicts=conflicts.get(s["supplier_id"], []),
            source_id=s["source_id"], effective_date=s["effective_date"],
        )
        for s in deps["suppliers"]
    ]
    shared = [SharedUpstream(upstream_id=g["upstream_id"], supplier_ids=g["supplier_ids"])
              for g in dq.shared_upstream(cid)] if deep else []
    return SupplierGraphResult(component_id=cid, suppliers=suppliers, shared_upstream=shared)


def _documents(hits: list[dict]) -> list[DocumentResult]:
    """Attach precedence; a superseded version never outranks a current document."""
    prec = dq.document_precedence()
    docs = [DocumentResult(
        source_id=h["source_id"], doc_type=h["doc_type"], title=h["title"], version=h.get("version"),
        effective_date=h["effective_date"], access_scope=h["access_scope"], content=h["content"],
        score=float(h["score"]), trusted=h["trusted"], security_flags=h["security_flags"],
        precedence_rank=prec[h["source_id"]]["rank"], superseded_by=prec[h["source_id"]]["superseded_by"],
    ) for h in hits]
    return sorted(docs, key=lambda d: (d.superseded_by is not None, -d.score))


def retrieve_documents(query: str, access_scope: str = "procurement", top_k: int = 5) -> list[DocumentResult]:
    """Document chunks the user's scope may read, with provenance, precedence and prompt-injection flags."""
    return _documents(ingest_documents.search(query, _scopes(access_scope), "hybrid", top_k))


def retrieve_similar_incidents(query: str, component_type: str | None = None, severity: str | None = None,
                               top_k: int = 5) -> list[dict]:
    """Past disruption cases and approved memories most similar to the query (few-shot context)."""
    return incident_memory.search(query, component_type=component_type, severity=severity, k=top_k)


SUPPLYGUARD_TOOLS = [
    StructuredTool.from_function(func=f, name=f.__name__, description=(f.__doc__ or "").strip())
    for f in (query_inventory, query_bom, query_supplier_graph, retrieve_documents, retrieve_similar_incidents)
]
