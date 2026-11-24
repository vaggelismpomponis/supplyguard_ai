"""Retrieval benchmark: pgvector vs ChromaDB vs Hybrid (#87).

Runs the ground-truth queries of eval/retrieval_queries.json against each retriever and reports
Recall@K, Precision@K, MRR and latency per retriever (and per query kind with -v).

    python -m eval.retrieval_benchmark --live              # seeded stack: pgvector, ChromaDB, hybrid
    python -m eval.retrieval_benchmark --offline           # no services: harness and ground-truth check
    python -m eval.retrieval_benchmark --live --out r.json # also save per-query rankings

Retrievers (relevance is per document, so chunk hits are collapsed to their source_id):

- ``pgvector``: cosine distance over ``policy_chunks`` (the seed embeds "title + chunk").
- ``chroma``: the ``supplyguard_docs`` collection, queried with its own embedding function.
- ``hybrid``: reciprocal-rank fusion of pgvector, BM25 over the same chunks, and a Neo4j graph
  expansion that boosts documents of suppliers related to the query (named supplier, suppliers of
  a named component, suppliers sharing an upstream manufacturer).

``--offline`` replaces pgvector by the same hash embeddings computed in memory and Neo4j by the
graph CSVs, and skips Chroma. Its numbers validate the harness only; the report uses ``--live``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable, Optional

from eval.dataset import DATA_DIR, REPO_ROOT

QUERIES_PATH = REPO_ROOT / "eval" / "retrieval_queries.json"
DOCS_DIR = DATA_DIR / "documents"
GRAPH_DIR = DATA_DIR / "graph"
DEFAULT_KS = (1, 3, 5)
RRF_K = 60
CANDIDATES = 40  # chunks fetched per retriever before collapsing to documents

Retriever = Callable[[str, int], list[str]]
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


# --- Metrics --------------------------------------------------------------------------------


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant) if relevant else 0.0


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / k


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    return next((1.0 / i for i, doc in enumerate(ranked, 1) if doc in relevant), 0.0)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(pct / 100 * len(ordered)) - 1))
    return ordered[idx]


def dedupe(doc_ids: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(doc_ids))


# --- Corpus (same parsing and chunking as scripts/seed.py) ----------------------------------


def parse_doc(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)", text, re.DOTALL)
    if not m:
        return {"source_id": path.stem, "title": path.stem}, text.strip()
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    meta.setdefault("source_id", path.stem)
    meta.setdefault("title", path.stem)
    return meta, m.group(2).strip()


def chunk_text(body: str, max_chars: int = 800) -> list[str]:
    chunks: list[str] = []
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        if chunks and len(chunks[-1]) + len(para) < max_chars:
            chunks[-1] += "\n\n" + para
        else:
            chunks.append(para)
    return chunks or [body[:max_chars]]


def load_corpus(docs_dir: Path = DOCS_DIR) -> list[dict[str, str]]:
    """One entry per chunk: source_id, supplier_id, title and text ("title + chunk")."""
    chunks = []
    for path in sorted(docs_dir.glob("**/*.md")):
        meta, body = parse_doc(path)
        for chunk in chunk_text(body):
            chunks.append({
                "source_id": meta["source_id"],
                "supplier_id": meta.get("supplier_id", ""),
                "title": meta["title"],
                "text": f"{meta['title']}\n{chunk}",
            })
    return chunks


# --- BM25 (in process, no extra dependency) -------------------------------------------------


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25:
    def __init__(self, chunks: list[dict[str, str]], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.docs = [Counter(tokenize(c["text"])) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(1, len(self.lengths))
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for tf, length in zip(self.docs, self.lengths):
            s = 0.0
            for t in terms:
                f = tf.get(t, 0)
                if f:
                    norm = self.k1 * (1 - self.b + self.b * length / self.avg)
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out

    def search(self, query: str, k: int) -> list[str]:
        scored = sorted(zip(self.scores(query), range(len(self.chunks))), reverse=True)
        return dedupe(self.chunks[i]["source_id"] for s, i in scored[:CANDIDATES] if s > 0)[:k]


# --- Graph expansion ------------------------------------------------------------------------


class GraphIndex:
    """Supplier names, component suppliers and shared upstreams, from Neo4j or the CSV export."""

    def __init__(self, names: dict[str, str], supplies: dict[str, set[str]], upstream: dict[str, str]):
        self.names = names  # supplier_id -> name
        self.supplies = supplies  # component_id -> supplier_ids
        self.upstream = upstream  # supplier_id -> upstream_id

    @classmethod
    def from_csv(cls, graph_dir: Path = GRAPH_DIR) -> "GraphIndex":
        def rows(name: str) -> list[dict[str, str]]:
            with (graph_dir / name).open(encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))

        names = {r["supplierId:ID(Supplier)"]: r["name"] for r in rows("nodes_supplier.csv")}
        supplies: dict[str, set[str]] = defaultdict(set)
        for r in rows("rel_supplies.csv"):
            supplies[r[":END_ID(Component)"]].add(r[":START_ID(Supplier)"])
        upstream = {r[":START_ID(Supplier)"]: r[":END_ID(Upstream)"] for r in rows("rel_sources_from.csv")}
        return cls(names, dict(supplies), upstream)

    @classmethod
    def from_neo4j(cls) -> "GraphIndex":
        from src.knowledge.common import neo4j_driver

        with neo4j_driver() as driver:
            names = {r["id"]: r["name"] for r in driver.execute_query(
                "MATCH (s:Supplier) RETURN s.supplierId AS id, s.name AS name").records}
            supplies: dict[str, set[str]] = defaultdict(set)
            for r in driver.execute_query(
                "MATCH (s:Supplier)-[:SUPPLIES]->(c:Component) "
                "RETURN c.componentId AS c, s.supplierId AS s"
            ).records:
                supplies[r["c"]].add(r["s"])
            upstream = {r["s"]: r["u"] for r in driver.execute_query(
                "MATCH (s:Supplier)-[:SOURCES_FROM]->(u:Upstream) "
                "RETURN s.supplierId AS s, u.upstreamId AS u").records}
        return cls(names, dict(supplies), upstream)

    def related_suppliers(self, query: str) -> set[str]:
        low = query.lower()
        named = {sid for sid, name in self.names.items()
                 if name.lower() in low or sid.lower() in tokenize(low)}
        if not named:  # first word of the name, e.g. "Atlas", "Helios"
            named = {sid for sid, name in self.names.items()
                     if re.search(rf"\b{re.escape(name.split()[0].lower())}\b", low)}
        components = {t.upper() for t in tokenize(low) if t.startswith("mc-")}
        related = set(named)
        for comp in components:
            related |= self.supplies.get(comp, set()) if not named else set()
        shared = {self.upstream.get(s) for s in named} - {None}
        related |= {s for s, u in self.upstream.items() if u in shared}
        return related


def graph_ranking(chunks: list[dict[str, str]], graph: GraphIndex, query: str, k: int) -> list[str]:
    """Documents of related suppliers, ordered by how many query terms their title shares."""
    related = graph.related_suppliers(query)
    if not related:
        return []
    terms = set(tokenize(query))
    hits = {}
    for c in chunks:
        if c["supplier_id"] in related:
            overlap = len(terms & set(tokenize(c["title"])))
            hits[c["source_id"]] = max(hits.get(c["source_id"], 0), overlap)
    return [d for d, _ in sorted(hits.items(), key=lambda x: -x[1])][:k]


def rrf(rankings: list[list[str]], k: int) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc in enumerate(ranking, 1):
            scores[doc] += 1.0 / (RRF_K + rank)
    return [d for d, _ in sorted(scores.items(), key=lambda x: -x[1])][:k]


# --- Retrievers -----------------------------------------------------------------------------


def pgvector_retriever() -> Retriever:
    from src.knowledge.common import embed, pg, vec

    sql = ("SELECT doc_id FROM policy_chunks ORDER BY embedding <=> %s::vector LIMIT %s")

    def search(query: str, k: int) -> list[str]:
        with pg() as conn:
            rows = conn.execute(sql, (vec(embed([query])[0]), CANDIDATES)).fetchall()
        return dedupe(r[0] for r in rows)[:k]

    return search


def chroma_retriever() -> Retriever:
    from src.knowledge.common import chroma_client

    collection = chroma_client().get_collection("supplyguard_docs")

    def search(query: str, k: int) -> list[str]:
        res = collection.query(query_texts=[query], n_results=CANDIDATES, include=["metadatas"])
        return dedupe(m["source_id"] for m in res["metadatas"][0])[:k]

    return search


def local_vector_retriever(chunks: list[dict[str, str]]) -> Retriever:
    """pgvector stand-in for --offline: same hash embeddings, cosine in memory."""
    import hashlib

    dim = 1536

    def embed(text: str) -> list[float]:
        v = [0.0] * dim
        for w in re.findall(r"[a-z0-9]+", text.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dim] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    vectors = [embed(c["text"]) for c in chunks]

    def search(query: str, k: int) -> list[str]:
        q = embed(query)
        sims = sorted(((sum(a * b for a, b in zip(q, v)), i) for i, v in enumerate(vectors)),
                      reverse=True)
        return dedupe(chunks[i]["source_id"] for _, i in sims[:CANDIDATES])[:k]

    return search


def hybrid_retriever(vector: Retriever, bm25: BM25, graph: GraphIndex,
                     chunks: list[dict[str, str]]) -> Retriever:
    def search(query: str, k: int) -> list[str]:
        depth = max(k, 10)
        return rrf([vector(query, depth), bm25.search(query, depth),
                    graph_ranking(chunks, graph, query, depth)], k)

    return search


# --- Runner ---------------------------------------------------------------------------------


def load_queries(path: Path = QUERIES_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["queries"]


def run(retrievers: dict[str, Retriever], queries: list[dict], ks: tuple[int, ...] = DEFAULT_KS):
    """Return per-retriever summary metrics and per-query rankings."""
    max_k = max(ks)
    summary, details = {}, []
    for name, search in retrievers.items():
        latencies, rr = [], []
        recall = {k: [] for k in ks}
        precision = {k: [] for k in ks}
        by_kind: dict[str, list[float]] = defaultdict(list)
        for q in queries:
            relevant = set(q["relevant"])
            start = time.perf_counter()
            ranked = search(q["query"], max_k)
            latencies.append((time.perf_counter() - start) * 1000)
            for k in ks:
                recall[k].append(recall_at_k(ranked, relevant, k))
                precision[k].append(precision_at_k(ranked, relevant, k))
            rr.append(reciprocal_rank(ranked, relevant))
            by_kind[q["kind"]].append(recall_at_k(ranked, relevant, max_k))
            details.append({"retriever": name, "id": q["id"], "ranked": ranked,
                            "relevant": q["relevant"]})
        summary[name] = {
            **{f"recall@{k}": statistics.mean(recall[k]) for k in ks},
            **{f"precision@{k}": statistics.mean(precision[k]) for k in ks},
            "mrr": statistics.mean(rr),
            "p50_ms": percentile(latencies, 50),
            "p95_ms": percentile(latencies, 95),
            "by_kind": {kind: statistics.mean(v) for kind, v in by_kind.items()},
        }
    return summary, details


def print_summary(summary: dict, ks: tuple[int, ...], verbose: bool) -> None:
    cols = [f"recall@{k}" for k in ks] + [f"precision@{k}" for k in ks] + ["mrr", "p50_ms", "p95_ms"]
    print("| retriever | " + " | ".join(cols) + " |")
    print("|---|" + "---|" * len(cols))
    for name, m in summary.items():
        cells = [f"{m[c]:.1f}" if c.endswith("_ms") else f"{m[c]:.3f}" for c in cols]
        print(f"| {name} | " + " | ".join(cells) + " |")
    if verbose:
        kinds = sorted({k for m in summary.values() for k in m["by_kind"]})
        print(f"\nRecall@{max(ks)} by query kind")
        print("| retriever | " + " | ".join(kinds) + " |")
        print("|---|" + "---|" * len(kinds))
        for name, m in summary.items():
            print(f"| {name} | " + " | ".join(f"{m['by_kind'].get(k, 0):.2f}" for k in kinds) + " |")


def build_retrievers(live: bool) -> dict[str, Retriever]:
    chunks = load_corpus()
    bm25 = BM25(chunks)
    if not live:
        vector = local_vector_retriever(chunks)
        return {
            "vector (offline hash)": vector,
            "bm25": bm25.search,
            "hybrid (offline)": hybrid_retriever(vector, bm25, GraphIndex.from_csv(), chunks),
        }
    vector = pgvector_retriever()
    return {
        "pgvector": vector,
        "chroma": chroma_retriever(),
        "hybrid": hybrid_retriever(vector, bm25, GraphIndex.from_neo4j(), chunks),
    }


def main(argv: Optional[list[str]] = None) -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="seeded pgvector, ChromaDB and Neo4j")
    mode.add_argument("--offline", action="store_true", help="in-memory stand-ins, no services")
    parser.add_argument("-v", "--verbose", action="store_true", help="breakdown by query kind")
    parser.add_argument("--out", help="save summary and per-query rankings as JSON")
    args = parser.parse_args(argv)

    queries = load_queries()
    try:
        retrievers = build_retrievers(args.live)
    except Exception as exc:
        print(f"Cannot build retrievers: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    summary, details = run(retrievers, queries)
    print(f"{len(queries)} queries, {'live' if args.live else 'offline'} mode\n")
    print_summary(summary, DEFAULT_KS, args.verbose)
    if args.out:
        Path(args.out).write_text(json.dumps({"summary": summary, "queries": details}, indent=2))
        print(f"\nSaved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
