# Retrieval Benchmark: pgvector vs ChromaDB vs Hybrid

**Owner:** Quality · **Issue:** #87 · **Collaboration:** Knowledge ✋
**Code:** [`eval/retrieval_benchmark.py`](../eval/retrieval_benchmark.py) · **Queries:** [`eval/retrieval_queries.json`](../eval/retrieval_queries.json)

> **Status (2026-11-24):** harness, ground truth, metrics, offline validation, and live benchmark
> run inside the seeded Docker Compose stack are complete. See [Live results](#live-results).

## Question

Which retrieval setup should the contract subagent use over the 212 documents?

1. **pgvector**: cosine distance over `policy_chunks` (Postgres).
2. **ChromaDB**: the `supplyguard_docs` collection.
3. **Hybrid**: reciprocal-rank fusion of pgvector, BM25 and a Neo4j graph expansion.

## Method

**Ground truth.** 24 queries, each with the set of documents a correct answer needs. Every id was
checked against the document text. The queries cover the decisions of the MC-17 case and the general
procedures:

| Kind | Queries | Example |
|---|---:|---|
| golden | 5 | "Is the Borealis Parts ISO 9001 certificate still valid?" → `DOC-QUA-S003-v1`, `DOC-EM-BOREALIS-01` |
| conflict | 3 | "Cordillera expedite fee, contract versus e-mail" → contract, e-mail, PRO-08 |
| version | 2 | "Current standard lead time in the Atlas contract" → `DOC-CON-S001-v3` only |
| policy | 11 | "Does a second source that shares an upstream count as diversification?" → `DOC-PRO-05-v1` |
| security | 1 | "Helios MC-17 price update notice" → `DOC-NOT-HELIOS-PRICE` (the planted document) |
| history | 2 | past incidents and notices outside the MC-17 case |

**Unit of relevance: the document.** Each retriever fetches 40 chunks, collapses them to their
`source_id` in rank order, and is scored on the top K documents.

**Metrics.** Recall@K and Precision@K for K = 1, 3, 5, MRR, and per-query latency p50/p95, measured in
the app container, sequentially, warm.

**Same corpus for all three.** All three use the chunks of `scripts/seed.py` (paragraphs, ≤ 800
characters). One difference stays: the seed stores pgvector chunks as "title + chunk" with the project
embedding (`text-embedding-3-small`, or hash embeddings offline), while ChromaDB embeds the chunk
alone with its default model. The comparison is between the two setups as deployed, not between the
two databases with identical vectors. ✋ Knowledge: if we want a database-only comparison, the seed
can pass `embeddings=` to Chroma.

**Hybrid.** Rankings are fused with RRF (k = 60) from:

- pgvector (top 10 documents);
- BM25 over the same chunks (in process, no new dependency);
- graph expansion: suppliers named in the query, plus suppliers of a named component when no
  supplier is named, plus suppliers that share an upstream manufacturer with a named one (Cypher on
  `SUPPLIES` and `SOURCES_FROM`). Their documents are ranked by title overlap with the query.

## Running

```bash
docker compose exec -T app python -m eval.retrieval_benchmark --live -v --out benchmark.json
python -m eval.retrieval_benchmark --offline -v    # no services, harness check only
```

## Offline validation run (2026-11-24)

The offline run uses in-memory stand-ins: hash embeddings instead of pgvector, the graph CSVs instead
of Neo4j, and no ChromaDB. It shows that the harness, the ground truth and the metrics work. **It does
not compare the databases.**

| retriever | recall@1 | recall@3 | recall@5 | precision@1 | precision@3 | precision@5 | mrr | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| vector (offline hash) | 0.701 | 0.924 | 0.979 | 0.917 | 0.444 | 0.292 | 0.958 | 22.3 | 22.5 |
| bm25 | 0.722 | 0.965 | 0.986 | 0.958 | 0.472 | 0.292 | 0.979 | 0.4 | 0.5 |
| hybrid (offline) | 0.764 | 0.965 | 0.965 | 1.000 | 0.472 | 0.283 | 1.000 | 23.1 | 23.7 |

What it already tells us:

- Most queries have 1–2 relevant documents, so Precision@5 has a ceiling of about 0.3. Recall and
  MRR are the useful metrics here.
- Hash embeddings are lexical, so the offline vector run behaves like BM25. The live run with real
  embeddings is the one that matters, especially for paraphrased queries.
- Graph expansion lifts MRR to 1.0 (the first document is always relevant). It costs recall where a
  procedure is relevant next to supplier documents: on RQ-04 the Cordillera documents push
  `DOC-PRO-08-v1` (expedite procedure) out of the top 5. It cannot help when no supplier is named: on
  RQ-06 ("supplier whose certification has expired") the Borealis record `DOC-QUA-S003-v1` is missed by
  the vector and hybrid runs. The live run should check whether both effects hold with real embeddings.

## Live results

Executed inside `supplyguard_app` (`python -m eval.retrieval_benchmark --live -v --out /tmp/benchmark.json`):

| retriever | recall@1 | recall@3 | recall@5 | precision@1 | precision@3 | precision@5 | mrr | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| pgvector | 0.764 | 0.986 | 1.000 | 1.000 | 0.486 | 0.300 | 1.000 | 730.8 | 1909.3 |
| chroma | 0.639 | 0.771 | 0.792 | 0.875 | 0.375 | 0.233 | 0.896 | 33.1 | 45.8 |
| hybrid | 0.722 | 0.986 | 0.986 | 0.958 | 0.486 | 0.292 | 0.979 | 716.5 | 882.6 |

Recall@5 by kind (`-v`):

| retriever | conflict | golden | history | policy | security | version |
|---|---|---|---|---|---|---|
| pgvector | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| chroma | 0.83 | 0.60 | 1.00 | 0.86 | 1.00 | 0.50 |
| hybrid | 0.89 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**Environment:** 2026-11-24, commit `f9a62ed`, 24 queries in `live` mode inside `supplyguard_app` (PostgreSQL `pgvector`, ChromaDB `0.5.23`, Neo4j `5.26.0`, offline deterministic hash embeddings / configured embedding model).

## Recommendation

Use **pgvector** for highest recall and exact contract/version compliance (`Recall@5 = 1.000`, `MRR = 1.000`, `1.00` across all 6 query kinds including `version` and `conflict`), paired with **Hybrid (pgvector + BM25 + Neo4j graph expansion)** (`Recall@3 = 0.986`, `Recall@5 = 0.986`, `MRR = 0.979`, lower `p95 = 882.6 ms`) for graph-augmented multi-hop supplier lookups. **ChromaDB** delivers the lowest latency (`p50 = 33.1 ms`, `p95 = 45.8 ms`) but falls short on `version` (`0.50`) and `golden` (`0.60`) precision/recall with its default embedding setup.
