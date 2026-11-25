"""Ingest the 212 support documents into pgvector and ChromaDB (#70, #72).

Run: python -m src.knowledge.ingest_documents
Idempotent: both stores are fully replaced on every run (Postgres in one transaction).

Every chunk carries provenance from the front matter: source_id (column doc_id), doc_type,
version, effective_date, access_scope, supplier_id.
- pgvector: table policy_chunks (docker/postgres/init.sql), embedded as "title + chunk" with
  common.embed, HNSW cosine index.
- ChromaDB: collection supplyguard_docs, embedded by Chroma's own default embedding function,
  as eval/retrieval_benchmark.py expects (#87 compares the two approaches).

Retrieved text is data, never instructions: chunks that try to instruct an AI assistant are
stored with trusted = false and security_flags = ['prompt_injection'] for the red-team checks.
"""
import json
import math
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from .common import DIM, embed, pg, vec
from .ingest import chunk

DOCUMENTS = Path(__file__).resolve().parents[1] / "support-data" / "documents"
COLLECTION = "supplyguard_docs"  # same collection name as the compose seed (#96)

# policy_chunks is created by init.sql; the provenance and safety columns are also added here,
# so databases created before #70 are upgraded in place.
DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS policy_chunks (
    doc_id VARCHAR(64) NOT NULL,
    effective_date DATE NOT NULL,
    chunk_index INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector({DIM}) NOT NULL,
    access_scope VARCHAR(32) DEFAULT 'procurement',
    metadata JSONB DEFAULT '{{}}',
    PRIMARY KEY (doc_id, effective_date, chunk_index)
);
ALTER TABLE policy_chunks ADD COLUMN IF NOT EXISTS doc_type VARCHAR(32);
ALTER TABLE policy_chunks ADD COLUMN IF NOT EXISTS supplier_id VARCHAR(32);
ALTER TABLE policy_chunks ADD COLUMN IF NOT EXISTS version INTEGER;
ALTER TABLE policy_chunks ADD COLUMN IF NOT EXISTS trusted BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE policy_chunks ADD COLUMN IF NOT EXISTS security_flags TEXT[] NOT NULL DEFAULT '{{}}';
CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding ON policy_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_policy_chunks_scope ON policy_chunks(access_scope);
"""

# Columns every search returns, with the document id under its front-matter name.
SELECT_COLS = """doc_id AS source_id, chunk_index, doc_type, title, supplier_id, version,
       effective_date::text AS effective_date, access_scope, trusted, security_flags, content"""


# Text addressed to an AI that tries to override rules or trigger actions. Patterns, not ids,
# so a new planted document is caught too.
INJECTION = re.compile(
    r"ignore (all )?(previous|prior|above) (instructions|rules|policies)"
    r"|system instruction|instructions? for ai|you are now"
    r"|without (human )?approval|do not (mention|tell|report)",
    re.I,
)


def parse(path: Path) -> tuple[dict[str, str], str]:
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", path.read_text(encoding="utf-8"), re.S)
    if not m:
        raise ValueError(f"{path.name}: missing front matter")
    meta = {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in m[1].splitlines() if ":" in line)}
    for key in ("source_id", "doc_type", "title", "effective_date", "access_scope"):
        if not meta.get(key):
            raise ValueError(f"{path.name}: missing '{key}'")
    date.fromisoformat(meta["effective_date"])
    return meta, m[2].strip()


def chunks() -> list[dict[str, Any]]:
    out = []
    for path in sorted(DOCUMENTS.glob("*/*.md")):
        meta, body = parse(path)
        for i, text in enumerate(chunk(body)):
            flags = ["prompt_injection"] if INJECTION.search(text) else []
            out.append({
                "source_id": meta["source_id"], "chunk_index": i, "doc_type": meta["doc_type"],
                "title": meta["title"], "supplier_id": meta.get("supplier_id") or None,
                "version": int(meta["version"]) if meta.get("version") else None,
                "effective_date": meta["effective_date"], "access_scope": meta["access_scope"],
                "path": path.relative_to(DOCUMENTS.parent).as_posix(),
                "trusted": not flags, "security_flags": flags, "content": text,
            })
    return out


def chroma_client():
    """The compose ChromaDB service when CHROMA_HOST is set, otherwise a local folder (tests, no Docker)."""
    if os.getenv("CHROMA_HOST"):
        from .common import chroma_client as http_client

        return http_client()
    import chromadb

    return chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", ".chroma"))


def chroma_metadata(c: dict[str, Any]) -> dict[str, Any]:
    """Chroma metadata values must be str/int/float/bool: drop None, join lists."""
    skip = {"content", "security_flags"}
    meta = {k: v for k, v in c.items() if k not in skip and v is not None}
    meta["security_flags"] = ",".join(c["security_flags"])
    return meta


def ingest() -> int:
    rows = chunks()
    vectors = embed([f"{r['title']}\n{r['content']}" for r in rows])
    with pg() as conn:  # one transaction: all or nothing
        conn.execute(DDL)
        conn.execute("DELETE FROM policy_chunks")
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO policy_chunks (doc_id, effective_date, chunk_index, title, source, content, embedding,
                   access_scope, metadata, doc_type, supplier_id, version, trusted, security_flags)
                   VALUES (%s,%s,%s,%s,%s,%s,%s::vector,%s,%s::jsonb,%s,%s,%s,%s,%s)""",
                [(r["source_id"], r["effective_date"], r["chunk_index"], r["title"], r["path"], r["content"], vec(v),
                  r["access_scope"], json.dumps(chroma_metadata(r)), r["doc_type"], r["supplier_id"], r["version"],
                  r["trusted"], r["security_flags"]) for r, v in zip(rows, vectors)],
            )
    client = chroma_client()
    try:
        client.delete_collection(COLLECTION)
    except Exception:  # first run: nothing to delete
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    for start in range(0, len(rows), 500):  # stay under Chroma's max batch size
        batch = rows[start:start + 500]
        col.add(
            ids=[f"{r['source_id']}#{r['chunk_index']}" for r in batch],
            documents=[r["content"] for r in batch],  # embedded by the collection's own function
            metadatas=[chroma_metadata(r) for r in batch],
        )
    return len({r["source_id"] for r in rows})


def search(query: str, scopes: list[str], backend: str = "pgvector", k: int = 5) -> list[dict[str, Any]]:
    """Top-k chunks the caller may see (scopes come from the user's document_scopes in users.csv)."""
    if backend == "pgvector":
        q = vec(embed([query])[0])
        with pg() as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT {SELECT_COLS}, 1 - (embedding <=> %s::vector) AS score
                    FROM policy_chunks WHERE access_scope = ANY(%s)
                    ORDER BY embedding <=> %s::vector LIMIT %s""",
                (q, scopes, q, k),
            )
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    if backend == "chroma":
        res = chroma_client().get_collection(COLLECTION).query(
            query_texts=[query], n_results=k, where={"access_scope": {"$in": scopes}}
        )
        return [
            {**m, "content": d, "score": 1 - dist, "supplier_id": m.get("supplier_id"), "version": m.get("version"),
             "security_flags": [f for f in m["security_flags"].split(",") if f]}
            for m, d, dist in zip(res["metadatas"][0], res["documents"][0], res["distances"][0])
        ]
    if backend == "hybrid":
        return hybrid_search(query, scopes, k)
    raise ValueError(f"unknown backend {backend!r}")


# --- hybrid retrieval (#75): dense pgvector + BM25 + Neo4j graph context, fused with RRF ---------
RRF_K = 60  # standard Reciprocal Rank Fusion constant: rank 1 -> 1/61
CANDIDATES = 50


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:-[0-9]+)?", text.lower())  # keeps ids such as mc-17 whole


def bm25(query: str, docs: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Okapi BM25 score of every doc (title + content) for the query."""
    tokens = [_words(f"{d['title']} {d['content']}") for d in docs]
    avg = sum(map(len, tokens)) / (len(tokens) or 1)
    df: dict[str, int] = {}
    for t in tokens:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    n, q = len(docs), set(_words(query))
    scores = []
    for t in tokens:
        tf = {w: t.count(w) for w in q}
        scores.append(sum(
            math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(t) / avg))
            for w in q if tf[w] and w in df))
    return scores


def graph_suppliers(query: str) -> set[str]:
    """Suppliers the query is about: named directly, or suppliers of a component it names (Neo4j)."""
    from .common import neo4j_driver
    from .data_quality import canonical_component_id, table

    text = query.lower()
    named = {s["supplier_id"] for s in table("suppliers.csv")
             if s["supplier_id"].lower() in _words(text) or s["name"].lower() in text}
    components = [c for c in (canonical_component_id(w) for w in re.findall(r"\bmc-?\d+\b", text)) if c]
    if not components:
        return named
    with neo4j_driver() as driver:
        records, _, _ = driver.execute_query(
            "MATCH (s:Supplier)-[:SUPPLIES]->(c:Component) WHERE c.componentId IN $c RETURN collect(DISTINCT s.supplierId) AS ids",
            c=components)
    return named | set(records[0]["ids"])


def hybrid_search(query: str, scopes: list[str], k: int = 5) -> list[dict[str, Any]]:
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            f"""SELECT {SELECT_COLS}, 1 - (embedding <=> %s::vector) AS dense
                FROM policy_chunks WHERE access_scope = ANY(%s)""",
            (vec(embed([query])[0]), scopes),
        )
        cols = [d.name for d in cur.description]
        docs = [dict(zip(cols, row)) for row in cur.fetchall()]
    related = graph_suppliers(query)
    lexical = bm25(query, docs)
    rankings = [
        sorted(range(len(docs)), key=lambda i: -docs[i]["dense"])[:CANDIDATES],
        [i for i in sorted(range(len(docs)), key=lambda i: -lexical[i]) if lexical[i] > 0][:CANDIDATES],
        # graph context: chunks of the suppliers the query is about, best dense match first
        [i for i in sorted(range(len(docs)), key=lambda i: -docs[i]["dense"]) if docs[i]["supplier_id"] in related][:CANDIDATES],
    ]
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, i in enumerate(ranking, 1):
            fused[i] = fused.get(i, 0.0) + 1 / (RRF_K + rank)
    top = sorted(fused, key=lambda i: -fused[i])[:k]
    return [{**{c: v for c, v in docs[i].items() if c != "dense"}, "score": fused[i]} for i in top]


if __name__ == "__main__":
    print(f"ingested {ingest()} documents into pgvector and ChromaDB")
