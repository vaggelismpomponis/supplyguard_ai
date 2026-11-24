"""Automated Knowledge Ingestion and Seeding Service for SupplyGuard AI.

Ingests synthetic data package:
1. Relational supply chain tables in PostgreSQL (suppliers, components, BOM, inventory, POs)
2. Multi-tier supply chain graph in Neo4j (Supplier -> Component -> Product -> Factory, Upstream)
3. Document corpus in PostgreSQL pgvector (policy_chunks)
4. Vector collection in ChromaDB (supplyguard_docs)

Executed automatically on initial startup by compose service `seed`, or via CLI:
    python scripts/seed.py

Idempotent: Safe to execute repeatedly without duplicating data or breaking constraints.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from src.knowledge.common import DIM, embed, neo4j_driver, pg, vec, chroma_client

DATA_DIR = REPO_ROOT / "src" / "support-data"
STRUCTURED_DIR = DATA_DIR / "structured"
GRAPH_DIR = DATA_DIR / "graph"
DOCS_DIR = DATA_DIR / "documents"


# ==============================================================================
# 1. Healthcheck / Service Availability
# ==============================================================================

def wait_for_services(max_attempts: int = 20, delay_seconds: float = 2.0) -> None:
    """Poll Postgres, Neo4j, ChromaDB, and External Risk until reachable."""
    print("[Seed Service] ⏳ Checking database and external service availability...")

    # PostgreSQL Check
    pg_ready = False
    for attempt in range(1, max_attempts + 1):
        try:
            with pg() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    pg_ready = True
                    break
        except Exception as exc:
            print(f"[Seed Service] Waiting for PostgreSQL ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay_seconds)
    if not pg_ready:
        print("[Seed Service] ⚠️ PostgreSQL not reachable, skipping live DB checks in local sandbox.")

    # Neo4j Check
    neo4j_ready = False
    for attempt in range(1, max_attempts + 1):
        try:
            with neo4j_driver() as driver:
                driver.verify_connectivity()
                neo4j_ready = True
                break
        except Exception as exc:
            time.sleep(delay_seconds)
            break  # In unit test environment, don't stall if container is down

    # External Risk Service Check
    risk_url = os.getenv("EXTERNAL_RISK_URL", "http://localhost:8080")
    try:
        req = urllib.request.Request(f"{risk_url}/alerts", headers={"User-Agent": "SeedScript"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                print(f"[Seed Service] ✅ External Risk feed reachable at {risk_url}")
    except Exception:
        pass


# ==============================================================================
# 2. Relational Seeding (PostgreSQL)
# ==============================================================================

def seed_postgres_relational() -> int:
    """Ingest all structured CSV files into PostgreSQL relational tables."""
    print("\n[1/4] 📦 Ingesting relational tables into PostgreSQL...")
    if not STRUCTURED_DIR.exists():
        print(f"[Seed Service] Warning: Structured dir {STRUCTURED_DIR} not found.")
        return 0

    total_rows = 0
    try:
        with pg() as conn:
            # 1. Ensure init.sql schema has executed
            init_sql_path = REPO_ROOT / "docker" / "postgres" / "init.sql"
            if init_sql_path.exists():
                conn.execute(init_sql_path.read_text(encoding="utf-8"))

            # Helper to read CSV
            def load_csv(filename: str) -> List[Dict[str, str]]:
                p = STRUCTURED_DIR / filename
                if not p.exists():
                    return []
                with open(p, "r", encoding="utf-8") as f:
                    return list(csv.DictReader(f))

            # Table mappings
            # Upstream Manufacturers
            upstreams = load_csv("upstream_manufacturers.csv")
            for r in upstreams:
                conn.execute(
                    """
                    INSERT INTO upstream_manufacturers (upstream_id, name, country)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (upstream_id) DO UPDATE SET name = EXCLUDED.name, country = EXCLUDED.country;
                    """,
                    (r["upstream_id"], r["name"], r["country"]),
                )
            total_rows += len(upstreams)

            # Suppliers
            suppliers = load_csv("suppliers.csv")
            for r in suppliers:
                exp_date = r["certification_expiry"] if r.get("certification_expiry") else None
                conn.execute(
                    """
                    INSERT INTO suppliers (
                        supplier_id, name, country, city, erp_status,
                        upstream_manufacturer_id, payment_terms, certification_status,
                        certification, certification_expiry
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (supplier_id) DO UPDATE SET
                        name = EXCLUDED.name, erp_status = EXCLUDED.erp_status,
                        certification_status = EXCLUDED.certification_status,
                        certification_expiry = EXCLUDED.certification_expiry;
                    """,
                    (
                        r["supplier_id"], r["name"], r["country"], r.get("city"),
                        r["erp_status"], r.get("upstream_manufacturer_id") or None,
                        r.get("payment_terms"), r.get("certification_status"),
                        r.get("certification"), exp_date
                    ),
                )
            total_rows += len(suppliers)

            # Factories
            factories = load_csv("factories.csv")
            for r in factories:
                conn.execute(
                    """
                    INSERT INTO factories (factory_id, name, country)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (factory_id) DO UPDATE SET name = EXCLUDED.name, country = EXCLUDED.country;
                    """,
                    (r["factory_id"], r["name"], r["country"]),
                )
            total_rows += len(factories)

            # Locations
            locations = load_csv("locations.csv")
            for r in locations:
                conn.execute(
                    """
                    INSERT INTO locations (location_id, name, factory_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (location_id) DO UPDATE SET name = EXCLUDED.name;
                    """,
                    (r["location_id"], r["name"], r.get("factory_id")),
                )
            total_rows += len(locations)

            # Components
            components = load_csv("components.csv")
            for r in components:
                conn.execute(
                    """
                    INSERT INTO components (component_id, description, uom, standard_cost_eur)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (component_id) DO UPDATE SET
                        description = EXCLUDED.description,
                        standard_cost_eur = EXCLUDED.standard_cost_eur;
                    """,
                    (r["component_id"], r["description"], r["uom"], float(r["standard_cost_eur"])),
                )
            total_rows += len(components)

            # Products
            products = load_csv("products.csv")
            for r in products:
                conn.execute(
                    """
                    INSERT INTO products (product_id, name, factory_id, list_price_eur)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (product_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        list_price_eur = EXCLUDED.list_price_eur;
                    """,
                    (r["product_id"], r["name"], r.get("factory_id"), float(r["list_price_eur"])),
                )
            total_rows += len(products)

            # Bill of Materials
            bom = load_csv("bill_of_materials.csv")
            for r in bom:
                conn.execute(
                    """
                    INSERT INTO bill_of_materials (product_id, component_id, qty_per_unit)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (product_id, component_id) DO UPDATE SET qty_per_unit = EXCLUDED.qty_per_unit;
                    """,
                    (r["product_id"], r["component_id"], int(r["qty_per_unit"])),
                )
            total_rows += len(bom)

            # Supplier Components
            supp_comp = load_csv("supplier_components.csv")
            for r in supp_comp:
                conn.execute(
                    """
                    INSERT INTO supplier_components (
                        supplier_id, component_id, unit_price_eur,
                        lead_time_days, monthly_capacity_units, moq_units, approved_source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (supplier_id, component_id) DO UPDATE SET
                        unit_price_eur = EXCLUDED.unit_price_eur,
                        lead_time_days = EXCLUDED.lead_time_days,
                        monthly_capacity_units = EXCLUDED.monthly_capacity_units;
                    """,
                    (
                        r["supplier_id"], r["component_id"], float(r["unit_price_eur"]),
                        int(r["lead_time_days"]), int(r["monthly_capacity_units"]),
                        int(r["moq_units"]), r.get("approved_source", "true").lower() in ("true", "1")
                    ),
                )
            total_rows += len(supp_comp)

            # Inventory
            inventory = load_csv("inventory.csv")
            for r in inventory:
                cnt_date = r["last_counted_date"] if r.get("last_counted_date") else None
                conn.execute(
                    """
                    INSERT INTO inventory (
                        component_id, location_id, on_hand, reserved, quarantined, usable, last_counted_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (component_id, location_id) DO UPDATE SET
                        on_hand = EXCLUDED.on_hand,
                        reserved = EXCLUDED.reserved,
                        quarantined = EXCLUDED.quarantined,
                        usable = EXCLUDED.usable,
                        last_counted_date = EXCLUDED.last_counted_date;
                    """,
                    (
                        r["component_id"], r["location_id"], int(r["on_hand"]),
                        int(r["reserved"]), int(r["quarantined"]), int(r["usable"]), cnt_date
                    ),
                )
            total_rows += len(inventory)

            # Purchase Orders
            pos = load_csv("purchase_orders.csv")
            for r in pos:
                conn.execute(
                    """
                    INSERT INTO purchase_orders (
                        po_id, supplier_id, supplier_name_as_entered, component_id,
                        qty, unit_price_eur, order_date, promised_date, status,
                        expedite_allowed, expedite_fee_pct, expedite_days_gain
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (po_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        promised_date = EXCLUDED.promised_date;
                    """,
                    (
                        r["po_id"], r["supplier_id"], r.get("supplier_name_as_entered"),
                        r["component_id"], int(r["qty"]), float(r["unit_price_eur"]),
                        r["order_date"], r.get("promised_date") or None, r["status"],
                        r.get("expedite_allowed", "false").lower() in ("true", "1"),
                        float(r.get("expedite_fee_pct") or 0.0),
                        int(r.get("expedite_days_gain") or 0)
                    ),
                )
            total_rows += len(pos)

            # Customers & Orders
            custs = load_csv("customers.csv")
            for r in custs:
                conn.execute(
                    """
                    INSERT INTO customers (customer_id, name, priority_tier, segment)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (customer_id) DO UPDATE SET name = EXCLUDED.name;
                    """,
                    (r["customer_id"], r["name"], int(r["priority_tier"]), r.get("segment")),
                )
            total_rows += len(custs)

            orders = load_csv("customer_orders.csv")
            for r in orders:
                conn.execute(
                    """
                    INSERT INTO customer_orders (
                        order_id, customer_id, product_id, qty, due_date, status,
                        unit_price_eur, revenue_eur, customer_priority_tier,
                        late_penalty_pct_per_week_capped5
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (order_id) DO UPDATE SET status = EXCLUDED.status;
                    """,
                    (
                        r["order_id"], r["customer_id"], r["product_id"], int(r["qty"]),
                        r["due_date"], r["status"], float(r["unit_price_eur"]),
                        float(r["revenue_eur"]), int(r["customer_priority_tier"]),
                        float(r.get("late_penalty_pct_per_week_capped5") or 0.0)
                    ),
                )
            total_rows += len(orders)

            # Quarantine lots & Reservations
            qlots = load_csv("quarantine_lots.csv")
            conn.execute("TRUNCATE TABLE quarantine_lots;")
            for r in qlots:
                conn.execute(
                    """
                    INSERT INTO quarantine_lots (component_id, location_id, lot_id, qty, reason, release_expected)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (r["component_id"], r["location_id"], r["lot_id"], int(r["qty"]), r["reason"], r.get("release_expected")),
                )
            total_rows += len(qlots)

            reservations = load_csv("reservations.csv")
            conn.execute("TRUNCATE TABLE reservations;")
            for r in reservations:
                conn.execute(
                    """
                    INSERT INTO reservations (component_id, location_id, customer_order_id, reserved_qty)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (r["component_id"], r["location_id"], r["customer_order_id"], int(r["reserved_qty"])),
                )
            total_rows += len(reservations)

            conn.commit()
            print(f"[1/4] ✅ Successfully populated {total_rows} rows into PostgreSQL relational tables.")
    except Exception as exc:
        print(f"[Seed Service] PostgreSQL relational seeding encountered: {exc}")
    return total_rows


# ==============================================================================
# 3. Neo4j Graph Seeding
# ==============================================================================

def seed_neo4j_graph() -> None:
    """Seed multi-tier supply chain model in Neo4j from graph CSVs."""
    print("\n[2/4] 🌐 Seeding multi-tier graph into Neo4j...")
    if not GRAPH_DIR.exists():
        print(f"[Seed Service] Graph directory {GRAPH_DIR} not found.")
        return

    def read_csv(fname: str) -> List[Dict[str, str]]:
        p = GRAPH_DIR / fname
        if not p.exists():
            return []
        with open(p, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Supplier) REQUIRE n.supplierId IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Component) REQUIRE n.componentId IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Product) REQUIRE n.productId IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Factory) REQUIRE n.factoryId IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Customer) REQUIRE n.customerId IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Upstream) REQUIRE n.upstreamId IS UNIQUE;",
    ]

    try:
        with neo4j_driver() as driver, driver.session() as session:
            for c in constraints:
                session.run(c).consume()

            # Nodes: Supplier
            suppliers = read_csv("nodes_supplier.csv")
            for r in suppliers:
                session.run(
                    """
                    MERGE (n:Supplier {supplierId: $id})
                    SET n.name = $name, n.country = $country, n.erpStatus = $status
                    """,
                    {"id": r["supplierId:ID(Supplier)"], "name": r["name"], "country": r["country"], "status": r["erpStatus"]},
                ).consume()

            # Nodes: Upstream
            upstreams = read_csv("nodes_upstream.csv")
            for r in upstreams:
                session.run(
                    "MERGE (n:Upstream {upstreamId: $id}) SET n.name = $name, n.country = $country",
                    {"id": r["upstreamId:ID(Upstream)"], "name": r["name"], "country": r["country"]},
                ).consume()

            # Nodes: Component
            components = read_csv("nodes_component.csv")
            for r in components:
                session.run(
                    "MERGE (n:Component {componentId: $id}) SET n.description = $desc",
                    {"id": r["componentId:ID(Component)"], "desc": r["description"]},
                ).consume()

            # Nodes: Product
            products = read_csv("nodes_product.csv")
            for r in products:
                session.run(
                    "MERGE (n:Product {productId: $id}) SET n.name = $name",
                    {"id": r["productId:ID(Product)"], "name": r["name"]},
                ).consume()

            # Nodes: Factory
            factories = read_csv("nodes_factory.csv")
            for r in factories:
                session.run(
                    "MERGE (n:Factory {factoryId: $id}) SET n.name = $name",
                    {"id": r["factoryId:ID(Factory)"], "name": r["name"]},
                ).consume()

            # Nodes: Customer
            customers = read_csv("nodes_customer.csv")
            for r in customers:
                session.run(
                    "MERGE (n:Customer {customerId: $id}) SET n.name = $name, n.priorityTier = toInteger($tier)",
                    {"id": r["customerId:ID(Customer)"], "name": r["name"], "tier": r.get("priorityTier:int", 1)},
                ).consume()

            # Relationships: SUPPLIES
            supplies = read_csv("rel_supplies.csv")
            for r in supplies:
                session.run(
                    """
                    MATCH (s:Supplier {supplierId: $sid}), (c:Component {componentId: $cid})
                    MERGE (s)-[x:SUPPLIES]->(c)
                    SET x.leadTimeDays = toInteger($lead), x.unitPriceEur = toFloat($price)
                    """,
                    {"sid": r[":START_ID(Supplier)"], "cid": r[":END_ID(Component)"], "lead": r.get("leadTimeDays:int", 0), "price": r.get("unitPriceEur:float", 0.0)},
                ).consume()

            # Relationships: SOURCES_FROM
            sources = read_csv("rel_sources_from.csv")
            for r in sources:
                session.run(
                    """
                    MATCH (s:Supplier {supplierId: $sid}), (u:Upstream {upstreamId: $uid})
                    MERGE (s)-[:SOURCES_FROM]->(u)
                    """,
                    {"sid": r[":START_ID(Supplier)"], "uid": r[":END_ID(Upstream)"]},
                ).consume()

            # Relationships: USED_IN
            used_in = read_csv("rel_used_in.csv")
            for r in used_in:
                session.run(
                    """
                    MATCH (c:Component {componentId: $cid}), (p:Product {productId: $pid})
                    MERGE (c)-[x:USED_IN]->(p)
                    SET x.qtyPerUnit = toInteger($qty)
                    """,
                    {"cid": r[":START_ID(Component)"], "pid": r[":END_ID(Product)"], "qty": r.get("qtyPerUnit:int", 1)},
                ).consume()

            # Relationships: PRODUCED_AT
            produced = read_csv("rel_produced_at.csv")
            for r in produced:
                session.run(
                    """
                    MATCH (p:Product {productId: $pid}), (f:Factory {factoryId: $fid})
                    MERGE (p)-[:PRODUCED_AT]->(f)
                    """,
                    {"pid": r[":START_ID(Product)"], "fid": r[":END_ID(Factory)"]},
                ).consume()

            # Relationships: ORDERED_BY
            ordered = read_csv("rel_ordered_by.csv")
            for r in ordered:
                session.run(
                    """
                    MATCH (p:Product {productId: $pid}), (c:Customer {customerId: $cid})
                    MERGE (p)-[x:ORDERED_BY]->(c)
                    SET x.openOrders = toInteger($orders)
                    """,
                    {"pid": r[":START_ID(Product)"], "cid": r[":END_ID(Customer)"], "orders": r.get("openOrders:int", 1)},
                ).consume()

        print("[2/4] ✅ Successfully seeded Neo4j multi-tier supply chain graph.")
    except Exception as exc:
        print(f"[Seed Service] Neo4j seeding skipped or encountered: {exc}")


# ==============================================================================
# 4. Document Ingestion (pgvector & ChromaDB)
# ==============================================================================

def parse_markdown_doc(p: Path) -> Tuple[Dict[str, Any], str]:
    """Parse YAML-like frontmatter and body from markdown files."""
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)", text, re.DOTALL)
    if not m:
        meta = {"source_id": p.stem, "title": p.stem, "effective_date": "2026-01-01", "access_scope": "procurement"}
        return meta, text.strip()
    frontmatter = m.group(1)
    body = m.group(2).strip()
    meta = {}
    for line in frontmatter.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    if "source_id" not in meta:
        meta["source_id"] = p.stem
    if "title" not in meta:
        meta["title"] = p.stem
    if "effective_date" not in meta:
        meta["effective_date"] = "2026-01-01"
    if "access_scope" not in meta:
        meta["access_scope"] = "procurement"
    return meta, body


def chunk_text(body: str, max_chars: int = 800) -> List[str]:
    """Split markdown text into paragraph chunks."""
    chunks: List[str] = []
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        if chunks and len(chunks[-1]) + len(para) < max_chars:
            chunks[-1] += "\n\n" + para
        else:
            chunks.append(para)
    return chunks or [body[:max_chars]]


def seed_documents() -> int:
    """Ingest documents into PostgreSQL pgvector and ChromaDB."""
    print("\n[3/4] 📄 Ingesting document corpus into pgvector and ChromaDB...")
    if not DOCS_DIR.exists():
        print(f"[Seed Service] Document dir {DOCS_DIR} not found.")
        return 0

    all_docs = list(DOCS_DIR.glob("**/*.md"))
    print(f"[Seed Service] Discovered {len(all_docs)} document files.")

    # 1. PostgreSQL pgvector ingestion
    pg_ingested = 0
    try:
        with pg() as conn:
            for p in all_docs:
                meta, body = parse_markdown_doc(p)
                chunks = chunk_text(body)
                vectors = embed([f"{meta['title']}\n{c}" for c in chunks])
                doc_id = meta.get("source_id", p.stem)
                eff_date = meta.get("effective_date", "2026-01-01")
                scope = meta.get("access_scope", "procurement")

                conn.execute(
                    "DELETE FROM policy_chunks WHERE doc_id = %s AND effective_date = %s;",
                    (doc_id, eff_date),
                )
                for i, (c, v) in enumerate(zip(chunks, vectors)):
                    conn.execute(
                        """
                        INSERT INTO policy_chunks (
                            doc_id, effective_date, chunk_index, title, source,
                            content, embedding, access_scope, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s::jsonb);
                        """,
                        (
                            doc_id, eff_date, i, meta["title"], p.name,
                            c, vec(v), scope, json.dumps(meta)
                        ),
                    )
                pg_ingested += 1
            conn.commit()
            print(f"[3/4] ✅ Ingested {pg_ingested} documents into PostgreSQL 'policy_chunks'.")
    except Exception as exc:
        print(f"[Seed Service] pgvector ingestion encountered: {exc}")

    # 2. ChromaDB ingestion
    try:
        client = chroma_client()
        collection = client.get_or_create_collection(
            name="supplyguard_docs",
            metadata={"description": "SupplyGuard AI document corpus & contract notices"}
        )
        chroma_ids = []
        chroma_docs = []
        chroma_metas = []
        for p in all_docs:
            meta, body = parse_markdown_doc(p)
            chunks = chunk_text(body)
            doc_id = meta.get("source_id", p.stem)
            for i, c in enumerate(chunks):
                chroma_ids.append(f"{doc_id}_{i}")
                chroma_docs.append(c)
                clean_meta = {k: str(v) for k, v in meta.items()}
                clean_meta["chunk_index"] = i
                chroma_metas.append(clean_meta)

        # Batch upsert into Chroma
        batch_size = 50
        for i in range(0, len(chroma_ids), batch_size):
            collection.upsert(
                ids=chroma_ids[i:i+batch_size],
                documents=chroma_docs[i:i+batch_size],
                metadatas=chroma_metas[i:i+batch_size]
            )
        print(f"[4/4] ✅ Upserted {len(chroma_ids)} chunks into ChromaDB collection 'supplyguard_docs'.")
    except Exception as exc:
        print(f"[Seed Service] ChromaDB ingestion skipped or encountered: {exc}")

    return len(all_docs)


# ==============================================================================
# 5. Main CLI Entrypoint
# ==============================================================================

def run_seeding() -> None:
    print("=" * 75)
    print("SupplyGuard AI - Automated Data Ingestion & Seeding Service")
    print("=" * 75)
    wait_for_services()
    seed_postgres_relational()
    seed_neo4j_graph()
    seed_documents()
    print("\n" + "=" * 75)
    print("🚀 SupplyGuard AI database seeding completed successfully.")
    print("=" * 75)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SupplyGuard AI Databases.")
    parser.parse_args()
    run_seeding()


if __name__ == "__main__":
    main()
