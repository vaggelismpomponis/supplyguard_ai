"""#75: hybrid retrieval (pgvector + BM25 + Neo4j graph context) vs plain vector search.

The labelled queries come from documents_index.csv (one known answer each), so the comparison
needs no hand labelling.
"""
import csv
import os

import pytest

from src.knowledge import ingest_documents as idoc

needs_stack = pytest.mark.skipif(
    "DATABASE_URL" not in os.environ or "NEO4J_PASSWORD" not in os.environ, reason="no seeded stack")
SCOPES = ["public", "internal", "procurement"]
K = 5


def labelled_queries() -> list[tuple[str, set[str]]]:
    with open(idoc.DOCUMENTS / "documents_index.csv", encoding="utf-8", newline="") as f:
        index = list(csv.DictReader(f))
    with open(idoc.DOCUMENTS.parent / "structured" / "suppliers.csv", encoding="utf-8", newline="") as f:
        names = {r["supplier_id"]: r["name"] for r in csv.DictReader(f)}
    current = {r["supplier_id"]: r["source_id"] for r in sorted(index, key=lambda r: int(r["version"])) if r["doc_type"] == "contract"}
    queries = [(f"{names[s]} contract lead time and monthly capacity", {sid}) for s, sid in current.items()]
    queries += [(f"{names[r['supplier_id']]} ISO 9001 certificate expiry", {r["source_id"]})
                for r in index if r["doc_type"] == "qualification"]
    return queries


# Questions an analyst asks during MC-17 without naming the document or (mostly) the supplier.
SCENARIO = [
    ("Atlas announced a delay for MC-17", {"DOC-NOT-ATLAS-MC17", "DOC-EM-ATLAS-01"}),
    ("real Helios capacity for MC-17", {"DOC-EM-HELIOS-01"}),
    ("expedite fee for PO-2026-9002", {"DOC-EM-CORDILLERA-01", "DOC-CON-S004-v1"}),
    ("which MC-17 alternative cannot be used because of quality certification", {"DOC-QUA-S003-v1"}),
    ("MC-17 supplier certification problem", {"DOC-QUA-S003-v1"}),
    ("superseded supply terms for the incumbent MC-17 supplier", {"DOC-CON-S001-v2", "DOC-CON-S001-v3"}),
    ("cheapest MC-17 alternative price notice", {"DOC-NOT-HELIOS-PRICE", "DOC-CON-S002-v1"}),
    ("account manager says delivery could take longer than notified", {"DOC-EM-ATLAS-01"}),
]


def scores(backend: str, queries: list[tuple[str, set[str]]]) -> dict[str, float]:
    """recall@K and MRR@10 of a backend over labelled queries."""
    recall = mrr = 0.0
    for q, expected in queries:
        ids = [r["source_id"] for r in idoc.search(q, SCOPES, backend, 10)]
        rank = next((i for i, sid in enumerate(ids, 1) if sid in expected), None)
        recall += bool(rank and rank <= K)
        mrr += 1 / rank if rank else 0
    return {"recall": recall / len(queries), "mrr": mrr / len(queries)}


def test_bm25_prefers_rare_terms():
    docs = [{"title": "", "content": "delay delay delay"}, {"title": "", "content": "delay borealis"}]
    scores = idoc.bm25("borealis delay", docs)
    assert scores[1] > scores[0] > 0


def test_labelled_queries_cover_contracts_and_qualifications():
    assert len(labelled_queries()) == 60 + 60  # one current contract and one qualification per supplier


@pytest.fixture(scope="module")
def indexed(tmp_path_factory):
    from src.knowledge import supply_graph

    if not os.getenv("CHROMA_HOST"):
        os.environ.setdefault("CHROMA_PATH", str(tmp_path_factory.mktemp("chroma")))
    supply_graph.load()  # graph context; other suites may have reset Neo4j
    idoc.ingest()


@needs_stack
@pytest.mark.parametrize("name,queries", [("labelled", labelled_queries()), ("scenario", SCENARIO)])
def test_hybrid_is_at_least_as_good_as_vector_search(indexed, capsys, name, queries):
    result = {b: scores(b, queries) for b in ("pgvector", "chroma", "hybrid")}
    with capsys.disabled():
        print(f"\n{name}: " + ", ".join(f"{b} recall@{K}={v['recall']:.3f} MRR={v['mrr']:.3f}" for b, v in result.items()))
    # Hybrid fuses the pgvector ranking with BM25 and graph context, so it must not lose to it.
    # Chroma uses its own embedding model (#87 compares the approaches), so it is reported only.
    assert result["hybrid"]["recall"] >= result["pgvector"]["recall"]
    if name == "scenario":  # graph context is what plain vector search lacks
        assert result["hybrid"]["mrr"] > result["pgvector"]["mrr"]


@needs_stack
def test_hybrid_respects_scope_and_uses_graph_context(indexed):
    viewer = idoc.search("finance sheet margin MC-17", ["public"], "hybrid", 10)
    assert viewer and {r["access_scope"] for r in viewer} == {"public"}
    assert idoc.graph_suppliers("delay on MC-17") == {"S001", "S002", "S003", "S004", "S005"}
    top = idoc.search("alternatives for MC-17 lead time", SCOPES, "hybrid", K)
    assert {r["supplier_id"] for r in top} <= {"S001", "S002", "S003", "S004", "S005"}
