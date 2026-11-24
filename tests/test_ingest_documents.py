"""KAN-08: document ingestion. Integration tests need DATABASE_URL (Postgres) and chromadb installed."""
import csv
import os

import pytest

from src.knowledge import ingest_documents as idoc

needs_pg = pytest.mark.skipif("DATABASE_URL" not in os.environ, reason="no Postgres")


def test_all_212_documents_chunked_with_provenance_matching_the_index():
    rows = idoc.chunks()
    with open(idoc.DOCUMENTS / "documents_index.csv", encoding="utf-8", newline="") as f:
        index = {r["source_id"]: r for r in csv.DictReader(f)}
    assert len(index) == 212 and {r["source_id"] for r in rows} == set(index)
    for r in rows:
        expected = index[r["source_id"]]
        assert r["access_scope"] == expected["access_scope"]
        assert r["effective_date"] == expected["effective_date"]
        assert r["path"] == expected["path"]


def test_only_the_planted_document_is_flagged_as_injection():
    flagged = {r["source_id"] for r in idoc.chunks() if not r["trusted"]}
    assert flagged == {"DOC-NOT-HELIOS-PRICE"}


def test_procedure_that_only_describes_injection_is_not_flagged():
    assert all(r["trusted"] for r in idoc.chunks() if r["source_id"] == "DOC-PRO-11-v1")


def test_chroma_metadata_has_no_none_values():
    for r in idoc.chunks():
        assert None not in idoc.chroma_metadata(r).values()


@pytest.fixture(scope="module")
def ingested(tmp_path_factory):
    os.environ.setdefault("CHROMA_PATH", str(tmp_path_factory.mktemp("chroma")))
    return idoc.ingest()


@needs_pg
def test_ingest_is_idempotent_and_stores_match(ingested):
    assert ingested == 212
    idoc.ingest()
    with idoc.pg() as c:
        n_pg = c.execute("SELECT count(*) FROM policy_chunks").fetchone()[0]
    assert n_pg == len(idoc.chunks()) == idoc.chroma_client().get_collection(idoc.COLLECTION).count()


@needs_pg
@pytest.mark.parametrize("backend", ["pgvector", "chroma"])
def test_search_respects_access_scope(ingested, backend):
    viewer = idoc.search("finance margin price penalty", ["public"], backend=backend, k=20)
    assert viewer and {r["access_scope"] for r in viewer} == {"public"}
    every_scope = ["public", "internal", "procurement", "finance-confidential"]
    assert {r["access_scope"] for r in idoc.search("finance sheet margin", every_scope, backend=backend, k=50)} <= set(every_scope)
    # HNSW search is approximate, so check the finance-only scope rather than a top-k cut over everything
    finance = idoc.search("finance sheet margin", ["finance-confidential"], backend=backend, k=5)
    assert finance and {r["source_id"] for r in finance} == {"DOC-FIN-01-v1"}
