# Knowledge

Data and retrieval tools the SupplyGuard agent uses: operational tables (Postgres), the document
corpus (pgvector and ChromaDB), incident memories (pgvector), and the multi-tier supplier graph (Neo4j).
Workflow calls the tools in `src/knowledge/tools.py` and never touches the databases directly.

## Implemented Tools (`src/knowledge/tools.py` & `SUPPLYGUARD_TOOLS`)

| Tool | Returns | Rule |
|---|---|---|
| `query_inventory(component_id, factory_id=None)` | `InventoryStatusResult` | Usable = on hand − reserved − quarantined; quarantined lots are never usable |
| `query_bom(component_id, horizon_days=60)` | `BOMResult` | From `bill_of_materials`, `production_schedule`, `customer_orders` |
| `query_supplier_graph(component_id, max_depth=2)` | `SupplierGraphResult` | Parameterized Cypher on Neo4j ([`docs/KNOWLEDGE_GRAPH.md`](../../docs/KNOWLEDGE_GRAPH.md)); reports shared upstreams and cert validity |
| `retrieve_documents(query, access_scope, top_k=5)` | `list[DocumentResult]` | Hybrid retrieval (pgvector + BM25 + Neo4j graph context); filters by user scopes before ranking; demotes superseded versions |
| `retrieve_similar_incidents(query, component_type=None, severity=None, top_k=5)` | `list[dict]` | Semantic search over 300 historical disruption cases + approved incident memories (`incident_memories`) |

## Data (`src/support-data/`)

See [`src/support-data/README.md`](../support-data/README.md): 60 suppliers, 300 components, 80
products, 2,000 purchase orders, inventory with reservations and quarantine lots, 1,500 customer
orders, 212 documents with provenance, the Neo4j CSVs, 300 historical cases, 40 approved incident
memories, the 105 evaluation cases and the MC-17 reference scenario.

## Loading the data (idempotent)

```bash
docker compose run --rm seed     # tables -> Postgres, graph -> Neo4j, documents -> pgvector + ChromaDB, memories -> pgvector
```

Tables: `docker/postgres/init.sql`. Documents: table `policy_chunks` (pgvector) and collection
`supplyguard_docs` (ChromaDB). Memories: table `incident_memories` (pgvector). Graph model: [`docs/KNOWLEDGE_GRAPH.md`](../../docs/KNOWLEDGE_GRAPH.md).

## Config (environment)

`DATABASE_URL` (or `POSTGRES_*`), `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD`, `CHROMA_HOST`/`CHROMA_PORT`,
and for embeddings `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
(or `OPENAI_API_KEY`). Without a working key, or with `OFFLINE_MODE=true`, embeddings fall back to
a lexical hash. Re-run the seed after changing embedding configuration.

## Retrieval benchmark

pgvector vs ChromaDB vs hybrid on 24 ground-truth queries: [`docs/RETRIEVAL_BENCHMARK.md`](../../docs/RETRIEVAL_BENCHMARK.md).
