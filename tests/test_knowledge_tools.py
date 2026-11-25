"""#73 / #78: Knowledge tools and mocks against the MC-17 golden scenario.

Mock tests read the support-data files only. Tool tests need DATABASE_URL and NEO4J_PASSWORD; they
load the knowledge base themselves and check that tools and mocks agree.
"""
import json
import os

import pytest

from src.knowledge import mocks
from src.knowledge.ingest_documents import DOCUMENTS

GOLDEN = json.loads((DOCUMENTS.parent / "evaluation" / "golden_scenario.json").read_text(encoding="utf-8"))
needs_stack = pytest.mark.skipif(
    "DATABASE_URL" not in os.environ or "NEO4J_PASSWORD" not in os.environ, reason="no seeded stack")


def check_inventory(inv):
    g = GOLDEN["mc17_inventory"]
    assert (inv.total_on_hand, inv.total_reserved, inv.total_quarantined, inv.total_usable) == (
        g["on_hand"], g["reserved"], g["quarantined"], g["usable"])
    assert {loc.location_id: loc.usable for loc in inv.locations} == GOLDEN["usable_by_location"]
    assert {(r.location_id, r.customer_order_id, r.reserved_qty) for r in inv.reservations} == {
        (r["location_id"], r["customer_order_id"], r["reserved_qty"]) for r in GOLDEN["reserved_stock_orders"]}
    assert [lot.lot_id for lot in inv.quarantine_lots] == ["LOT-KAT-0932"]


def check_bom(bom):
    assert [p.product_id for p in bom.products] == GOLDEN["affected_products"]
    assert len(bom.open_orders) == GOLDEN["open_orders_due_within_60d_on_affected_products"]
    first_week = GOLDEN["scenario_date"]
    assert {f: w[first_week] / 7 for f, w in bom.weekly_demand.items()} == GOLDEN["daily_demand_per_factory"]


def check_suppliers(graph):
    by_id = {s.supplier_id: s for s in graph.suppliers}
    assert set(by_id) == {"S001", "S002", "S003", "S004", "S005"}
    assert not by_id["S003"].certification_valid  # Borealis: ISO 9001 expired
    assert [s.supplier_ids for s in graph.shared_upstream] == [["S001", "S005"]]  # Atlas + Delta -> Veltro
    expedite = by_id["S004"].open_purchase_orders[0]
    assert (expedite.po_id, expedite.qty, expedite.expedite_fee_pct, expedite.expedite_days_gain) == ("PO-2026-9002", 1500, 6, 7)
    assert (by_id["S004"].lead_time_days, by_id["S004"].monthly_capacity_units, by_id["S004"].unit_price_eur) == (9, 3000, 9.8)
    assert by_id["S002"].conflicts[0].attribute == "monthly_capacity_units"  # Helios e-mail 1,500 vs contract 4,000
    assert by_id["S001"].source_id == "DOC-CON-S001-v3"


# --- mocks: no database ------------------------------------------------------------------------
def test_mock_inventory_matches_golden():
    check_inventory(mocks.query_inventory("MC-17"))


def test_mock_inventory_accepts_non_canonical_id_and_factory_filter():
    inv = mocks.query_inventory("MC017", factory_id="F2")
    assert [loc.location_id for loc in inv.locations] == ["W-KAT"] and inv.total_quarantined == 600


def test_mock_bom_matches_golden():
    check_bom(mocks.query_bom("MC-17"))


def test_mock_supplier_graph_matches_golden():
    check_suppliers(mocks.query_supplier_graph("MC-17"))


def test_mock_documents_respect_scope_and_demote_superseded():
    assert {d.access_scope for d in mocks.retrieve_documents("finance margin price", "public", 20)} == {"public"}
    docs = mocks.retrieve_documents("Atlas Components supply contract lead time", "procurement", 10)
    ids = [d.source_id for d in docs]
    assert ids.index("DOC-CON-S001-v3") < ids.index("DOC-CON-S001-v2")


# --- real tools: seeded stack ------------------------------------------------------------------
@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Load the knowledge base first: other suites may have reset the databases."""
    if not os.getenv("CHROMA_HOST"):
        os.environ.setdefault("CHROMA_PATH", str(tmp_path_factory.mktemp("chroma")))
    from src.knowledge import incident_memory, ingest_documents, load_structured, supply_graph, tools

    load_structured.load()
    supply_graph.load()
    ingest_documents.ingest()
    incident_memory.ingest()
    return tools


@needs_stack
def test_tools_match_golden_and_mocks(tools):
    for name, check in [("query_inventory", check_inventory), ("query_bom", check_bom), ("query_supplier_graph", check_suppliers)]:
        real, mock = getattr(tools, name)("MC-17"), getattr(mocks, name)("MC-17")
        check(real)
        assert real == mock, name


@needs_stack
def test_retrieve_documents_scope_precedence_and_injection(tools):
    viewer = tools.retrieve_documents("Helios MC-17 price update", "public", 10)
    assert viewer and {d.access_scope for d in viewer} == {"public"}
    helios = next(d for d in viewer if d.source_id == "DOC-NOT-HELIOS-PRICE")
    assert not helios.trusted and helios.security_flags == ["prompt_injection"]
    finance = tools.retrieve_documents("finance sheet margin", "finance", 50)
    assert "finance-confidential" in {d.access_scope for d in finance}


@needs_stack
def test_similar_incidents_are_filtered(tools):
    hits = tools.retrieve_similar_incidents("delay on a component, expedite", severity="moderate", top_k=5)
    assert hits and all(h["severity"] == "moderate" for h in hits)
