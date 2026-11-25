"""Multi-tier supply chain graph in Neo4j (KAN-07).

Run: python -m src.knowledge.supply_graph   (idempotent: MERGE on ids, properties overwritten)

Model (every node and relationship keeps sourceId and effectiveDate):
  (:Upstream)<-[:SOURCES_FROM]-(:Supplier)-[:SUPPLIES]->(:Component)
  (:Component)-[:USED_IN {qtyPerUnit}]->(:Product)-[:PRODUCED_AT]->(:Factory)
  (:Product)-[:ORDERED_BY {openOrders}]->(:Customer)

Reads src/support-data/graph/*.csv in Python, so no file copy into the Neo4j import folder is
needed. SUPPLIES is enriched with capacity, MOQ and approval from structured/supplier_components.csv,
and Supplier with certificationStatus from structured/suppliers.csv.
"""
import csv
from pathlib import Path
from typing import Any

from .common import neo4j_driver

DATA = Path(__file__).resolve().parents[1] / "support-data"
GRAPH = DATA / "graph"
STRUCTURED = DATA / "structured"

CONSTRAINTS = [
    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
    for label, key in [
        ("Supplier", "supplierId"), ("Upstream", "upstreamId"), ("Component", "componentId"),
        ("Product", "productId"), ("Factory", "factoryId"), ("Customer", "customerId"),
    ]
]


def read(path: Path) -> list[dict[str, str]]:
    """CSV rows with neo4j-admin header suffixes stripped: 'supplierId:ID(Supplier)' -> 'supplierId'."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [{k.split(":")[0] if not k.startswith(":") else k.split("(")[0][1:]: v for k, v in r.items()} for r in rows]


def rows() -> dict[str, list[dict[str, Any]]]:
    cert = {r["supplier_id"]: r["certification_status"] for r in read(STRUCTURED / "suppliers.csv")}
    capacity = {(r["supplier_id"], r["component_id"]): r for r in read(STRUCTURED / "supplier_components.csv")}
    suppliers = read(GRAPH / "nodes_supplier.csv")
    for s in suppliers:
        s["certificationStatus"] = cert.get(s["supplierId"])
    supplies = read(GRAPH / "rel_supplies.csv")
    for r in supplies:
        sc = capacity.get((r["START_ID"], r["END_ID"]), {})
        r["monthlyCapacityUnits"] = int(sc["monthly_capacity_units"]) if sc.get("monthly_capacity_units") else None
        r["moqUnits"] = int(sc["moq_units"]) if sc.get("moq_units") else None
        r["approvedSource"] = sc.get("approved_source")  # yes | no | alternative
    return {
        "suppliers": suppliers,
        "upstreams": read(GRAPH / "nodes_upstream.csv"),
        "components": read(GRAPH / "nodes_component.csv"),
        "products": read(GRAPH / "nodes_product.csv"),
        "factories": read(GRAPH / "nodes_factory.csv"),
        "customers": read(GRAPH / "nodes_customer.csv"),
        "supplies": supplies,
        "depends": read(GRAPH / "rel_sources_from.csv"),
        "used_in": read(GRAPH / "rel_used_in.csv"),
        "produced_at": read(GRAPH / "rel_produced_at.csv"),
        "ordered_by": read(GRAPH / "rel_ordered_by.csv"),
    }


PROV = "x.sourceId = r.sourceId, x.effectiveDate = date(r.effectiveDate)"
STATEMENTS = [
    f"""UNWIND $suppliers AS r MERGE (x:Supplier {{supplierId: r.supplierId}})
        SET x.name = r.name, x.country = r.country, x.erpStatus = r.erpStatus,
            x.certificationStatus = r.certificationStatus,
            x.certificationExpiry = date(r.certificationExpiry), {PROV}""",
    f"UNWIND $upstreams AS r MERGE (x:Upstream {{upstreamId: r.upstreamId}}) SET x.name = r.name, x.country = r.country, {PROV}",
    f"UNWIND $components AS r MERGE (x:Component {{componentId: r.componentId}}) SET x.description = r.description, {PROV}",
    f"UNWIND $products AS r MERGE (x:Product {{productId: r.productId}}) SET x.name = r.name, {PROV}",
    f"UNWIND $factories AS r MERGE (x:Factory {{factoryId: r.factoryId}}) SET x.name = r.name, {PROV}",
    f"UNWIND $customers AS r MERGE (x:Customer {{customerId: r.customerId}}) SET x.name = r.name, x.priorityTier = toInteger(r.priorityTier), {PROV}",
    f"""UNWIND $supplies AS r MATCH (a:Supplier {{supplierId: r.START_ID}}), (b:Component {{componentId: r.END_ID}})
        MERGE (a)-[x:SUPPLIES]->(b)
        SET x.leadTimeDays = toInteger(r.leadTimeDays), x.unitPriceEur = toFloat(r.unitPriceEur),
            x.monthlyCapacityUnits = r.monthlyCapacityUnits, x.moqUnits = r.moqUnits,
            x.approvedSource = r.approvedSource, {PROV}""",
    f"""UNWIND $depends AS r MATCH (a:Supplier {{supplierId: r.START_ID}}), (b:Upstream {{upstreamId: r.END_ID}})
        MERGE (a)-[x:SOURCES_FROM]->(b) SET {PROV}""",
    f"""UNWIND $used_in AS r MATCH (a:Component {{componentId: r.START_ID}}), (b:Product {{productId: r.END_ID}})
        MERGE (a)-[x:USED_IN]->(b) SET x.qtyPerUnit = toInteger(r.qtyPerUnit), {PROV}""",
    f"""UNWIND $produced_at AS r MATCH (a:Product {{productId: r.START_ID}}), (b:Factory {{factoryId: r.END_ID}})
        MERGE (a)-[x:PRODUCED_AT]->(b) SET {PROV}""",
    f"""UNWIND $ordered_by AS r MATCH (a:Product {{productId: r.START_ID}}), (b:Customer {{customerId: r.END_ID}})
        MERGE (a)-[x:ORDERED_BY]->(b) SET x.openOrders = toInteger(r.openOrders), {PROV}""",
]


def load() -> None:
    data = rows()
    with neo4j_driver() as driver, driver.session() as session:
        for c in CONSTRAINTS:
            session.run(c).consume()
        for q in STATEMENTS:
            session.run(q, **data).consume()


# --- queries for the Workflow tools (handoff) --------------------------------------------------
def component_dependencies(component_id: str) -> dict[str, Any]:
    """Tier-1 suppliers of a component with their tier-2 upstream manufacturer, and downstream impact."""
    with neo4j_driver() as driver, driver.session() as session:
        suppliers = session.run(
            """MATCH (s:Supplier)-[r:SUPPLIES]->(:Component {componentId: $c})
               OPTIONAL MATCH (s)-[d:SOURCES_FROM]->(u:Upstream)
               RETURN s.supplierId AS supplier_id, s.name AS name, s.certificationStatus AS certification_status,
                      toString(s.certificationExpiry) AS certification_expiry, r.leadTimeDays AS lead_time_days,
                      r.unitPriceEur AS unit_price_eur, r.monthlyCapacityUnits AS monthly_capacity_units,
                      u.upstreamId AS upstream_id, u.name AS upstream_name,
                      r.sourceId AS source_id, toString(r.effectiveDate) AS effective_date
               ORDER BY supplier_id""",
            c=component_id,
        ).data()
        downstream = session.run(
            """MATCH (:Component {componentId: $c})-[u:USED_IN]->(p:Product)-[:PRODUCED_AT]->(f:Factory)
               OPTIONAL MATCH (p)-[o:ORDERED_BY]->(cu:Customer)
               RETURN p.productId AS product_id, p.name AS product, f.factoryId AS factory_id, f.name AS factory,
                      u.qtyPerUnit AS qty_per_unit,
                      collect({customer_id: cu.customerId, priority_tier: cu.priorityTier, open_orders: o.openOrders}) AS customers
               ORDER BY product_id""",
            c=component_id,
        ).data()
    for p in downstream:  # OPTIONAL MATCH with no customer yields one all-null entry
        p["customers"] = [c for c in p["customers"] if c["customer_id"]]
    return {"component_id": component_id, "suppliers": suppliers, "products": downstream}


def shared_upstream(supplier_id: str) -> list[dict[str, Any]]:
    """Other suppliers that depend on the same upstream manufacturer: switching to them is not diversification."""
    with neo4j_driver() as driver, driver.session() as session:
        return session.run(
            """MATCH (s:Supplier {supplierId: $s})-[:SOURCES_FROM]->(u:Upstream)
                     <-[d:SOURCES_FROM]-(o:Supplier)
               RETURN o.supplierId AS supplier_id, o.name AS name, u.upstreamId AS upstream_id,
                      u.name AS upstream_name, d.sourceId AS source_id ORDER BY supplier_id""",
            s=supplier_id,
        ).data()


if __name__ == "__main__":
    load()
    print("loaded supply chain graph into Neo4j")
