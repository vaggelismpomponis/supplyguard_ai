# Knowledge

Data and retrieval tools the SupplyGuard agent uses: operational tables (Postgres), the document
corpus (pgvector and ChromaDB) and the multi-tier supplier graph (Neo4j). Workflow calls the tools
and never touches the databases directly.

> **Status (2026-11-24):** the data is loaded by `scripts/seed.py`. The tools below are the contract
> ([`docs/ARCHITECTURE_CONTRACTS.md`](../../docs/ARCHITECTURE_CONTRACTS.md) §4) and are **not
> implemented yet**. `tools.py`, `models.py`, `mocks.py`, `ingest.py` and `seed_graph.py` in this
> folder are still the HelpDesk Lite policy and service-graph code; they are replaced together with
> the HelpDesk agent (see [`docs/PROJECT_CHECKLIST.md`](../../docs/PROJECT_CHECKLIST.md#9-mid-week-audit-86)).
> `common.py` (connections, embeddings) is shared and stays.

## Tools (contract)

| Tool | Returns | Rule |
|---|---|---|
| `query_inventory(component_id, factory_id=None)` | `OperationalImpact` | Usable = on hand − reserved − quarantined; quarantined lots are never usable |
| `query_bom(component_id)` | products, factories, open customer orders | From `bill_of_materials`, `production_schedule`, `customer_orders` |
| `query_supplier_graph(component_id, max_depth=2)` | suppliers, capacities, lead times, upstream manufacturers | Parameterized Cypher on the graph ([`docs/KNOWLEDGE_GRAPH.md`](../../docs/KNOWLEDGE_GRAPH.md)); reports shared upstreams |
| `retrieve_documents(query, access_scope, top_k=5)` | chunks with `source_id`, `version`, `effective_date`, `access_scope` | Filters by the user's scopes before ranking; the latest valid version of a document wins and conflicts are reported |

## Data (`src/support-data/`)

See [`src/support-data/README.md`](../support-data/README.md): 60 suppliers, 300 components, 80
products, 2,000 purchase orders, inventory with reservations and quarantine lots, 1,500 customer
orders, 212 documents with provenance, the Neo4j CSVs, 300 historical cases, 40 approved incident
memories, the 105 evaluation cases and the MC-17 reference scenario.

## Loading the data (idempotent)

```
docker compose run --rm seed     # tables -> Postgres, documents -> pgvector + ChromaDB, graph -> Neo4j
```

Tables: `docker/postgres/init.sql`. Documents: table `policy_chunks` (pgvector) and collection
`supplyguard_docs` (ChromaDB). Graph model: [`docs/KNOWLEDGE_GRAPH.md`](../../docs/KNOWLEDGE_GRAPH.md).

Not loaded yet: `historical_disruption_cases.csv` and `approved_incident_memories.jsonl`.

## Config (environment)

`DATABASE_URL` (or `POSTGRES_*`), `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD`, `CHROMA_HOST`/`CHROMA_PORT`,
and for embeddings `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
(or `OPENAI_API_KEY`). Without a working key, or with `OFFLINE_MODE=true`, embeddings fall back to
a lexical hash: fine for dev and tests, weaker than real embeddings. Re-run the seed after changing it.

## Retrieval benchmark

pgvector vs ChromaDB vs hybrid on 24 ground-truth queries: [`docs/RETRIEVAL_BENCHMARK.md`](../../docs/RETRIEVAL_BENCHMARK.md).
