"""KAN-09: historical cases and approved memories. Integration tests need DATABASE_URL."""
import os

import pytest

from src.knowledge import incident_memory as im

needs_pg = pytest.mark.skipif("DATABASE_URL" not in os.environ, reason="no Postgres")


def test_severity_buckets():
    assert [im.severity(d) for d in (None, 3, 7, 8, 12, 14, 15, 30)] == [
        None, "minor", "minor", "moderate", "moderate", "moderate", "major", "major"]


def test_component_type_strips_type_suffix():
    assert im.component_type("Relay type E83") == "Relay"
    assert im.component_type("Motor controller board 48V") == "Motor controller board 48V"


def test_records_cover_300_cases_and_40_memories_with_filters_filled():
    rows = im.records()
    assert sum(r["kind"] == "historical_case" for r in rows) == 300
    assert sum(r["kind"] == "approved_memory" for r in rows) == 40
    assert len({r["memory_id"] for r in rows}) == 340
    assert all(r["component_type"] and r["severity"] and r["content"] for r in rows)


@pytest.fixture(scope="module")
def indexed():
    return im.ingest()


@needs_pg
def test_ingest_is_idempotent(indexed):
    assert indexed == im.ingest() == 340
    with im.pg() as c:
        assert c.execute("SELECT count(*) FROM incident_memories").fetchone()[0] == 340


@needs_pg
def test_search_filters_by_component_type_and_severity(indexed):
    hits = im.search("supplier delay expedite", component_type="Relay", severity="major", k=10)
    assert hits and all(h["component_type"] == "Relay" and h["severity"] == "major" for h in hits)


@needs_pg
def test_search_returns_approved_memories_with_provenance(indexed):
    hits = im.search("upstream shortage transfer inventory", kind="approved_memory", k=3)
    assert len(hits) == 3 and all(h["memory_id"].startswith("MEM-") and h["case_id"] for h in hits)
