"""KAN-07: Neo4j supply chain graph. Integration tests need NEO4J_PASSWORD and a running Neo4j."""
import os

import pytest

from src.knowledge import supply_graph as sg

needs_neo4j = pytest.mark.skipif("NEO4J_PASSWORD" not in os.environ, reason="no Neo4j")


def test_rows_strip_admin_headers_and_keep_provenance():
    data = sg.rows()
    assert len(data["suppliers"]) == 60 and len(data["supplies"]) == 876
    rel = next(r for r in data["supplies"] if r["START_ID"] == "S001" and r["END_ID"] == "MC-17")
    assert rel["leadTimeDays"] == "14" and rel["sourceId"] == "DOC-CON-S001-v3"
    assert rel["monthlyCapacityUnits"] == 9000 and rel["approvedSource"] == "yes"
    assert all(r["sourceId"] and r["effectiveDate"] for rows in data.values() for r in rows)


def test_rows_show_atlas_and_delta_share_veltro():
    upstream = {r["START_ID"]: r["END_ID"] for r in sg.rows()["depends"]}
    assert upstream["S001"] == upstream["S005"] == "U01"  # Atlas and Delta -> Veltro Semiconductor


def test_borealis_certification_is_expired_despite_erp_status():
    borealis = next(s for s in sg.rows()["suppliers"] if s["supplierId"] == "S003")
    assert borealis["erpStatus"] == "approved" and borealis["certificationStatus"] == "expired"


@pytest.fixture(scope="module")
def graph():
    sg.load()
    sg.load()  # second run must not duplicate anything


@needs_neo4j
def test_load_is_idempotent(graph):
    with sg.neo4j_driver() as d, d.session() as s:
        assert s.run("MATCH (n:Supplier) RETURN count(n) AS n").single()["n"] == 60
        assert s.run("MATCH ()-[r:SUPPLIES]->() RETURN count(r) AS n").single()["n"] == 876


@needs_neo4j
def test_mc17_dependencies_tier1_and_tier2(graph):
    deps = sg.component_dependencies("MC-17")
    by_id = {s["supplier_id"]: s for s in deps["suppliers"]}
    assert set(by_id) == {"S001", "S002", "S003", "S004", "S005"}
    assert by_id["S001"]["upstream_name"] == "Veltro Semiconductor"
    assert {p["factory_id"] for p in deps["products"]} == {"F1", "F2", "F3"}
    assert len(deps["products"]) == 6


@needs_neo4j
def test_shared_upstream_reveals_delta(graph):
    assert [s["supplier_id"] for s in sg.shared_upstream("S001")] == ["S005"]
