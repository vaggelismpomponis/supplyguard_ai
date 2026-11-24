# Role: Platform – SupplyGuard AI

**Ευθύνη:** Docker Compose πολυ-υπηρεσιακού stack (PostgreSQL + pgvector, Neo4j, ChromaDB, Mock External Services), MCP boundaries, `.env.example`, automated seed service, README, καθαρό clone σε <10′.  
**Παραδοτέο:** Πλήρες stack που εκκινεί και φορτώνει τα δεδομένα με μία εντολή (`docker compose up -d`).  
**Scopes commit:** `docker`, `db`, `mcp`, `docs`, `deps`.  
**Branches:** `feature/docker-compose-expansion`, `feature/chromadb-service`, `feature/mcp-environment`, κλπ.

## Αρχή
Το Platform αποτελεί τη βάση για όλους τους ρόλους. Στο SupplyGuard AI επεκτείνουμε το stack πέρα από το βασικό PostgreSQL/Neo4j για να υποστηρίξουμε vector benchmarking με **ChromaDB**, **MCP interfaces** για το simulated procurement system, και automated ingestion service (`seed`) του μεγάλου συνθετικού πακέτου `support-data/`.

## Βήματα

### Φάση 1 – Kick-off & Επέκταση Stack (Εβδ. 1, Ημ. 1–2)
1. Συμμετοχή στα contracts (`docs/ARCHITECTURE_CONTRACTS.md`): Pydantic schemas, database boundaries, tool signatures, MCP protocols. ✋ με όλους.
2. Ενημέρωση και αυστηρό pinning στο `requirements.txt` (`deepagents`, `chromadb`, `neo4j`, `psycopg`, `chainlit`, `mcp`). Καταγραφή στο `docs/PINNED_VERSIONS.md`.
3. Επέκταση του `docker-compose.yml` με 5 βασικά services:
   - `postgres` (PostgreSQL 16 + pgvector για operational records, checkpoints, audit logs, primary vectors).
   - `neo4j` (Neo4j 5.26+ για multi-tier supply chain dependency graph).
   - `chromadb` (ChromaDB service για retrieval experiments & benchmarking).
   - `external-risk` (Mock/external risk feed service container).
   - `app` (Chainlit UI + Deep Agents harness).
4. Ενημέρωση `.env.example` με όλες τις νέες μεταβλητές (ChromaDB endpoints, Neo4j credentials, MCP settings, LangSmith).

### Φάση 2 – Automated Ingestion & Persisted Storage (Ημ. 2–4)
5. Διαμόρφωση Docker persistent named volumes (`postgres_data`, `neo4j_data`, `chroma_data`) με `stop_grace_period: 15s` για ασφαλές graceful shutdown κατά τα restarts.
6. Δημιουργία Compose service `seed` που εκτελεί αυτόματα και idempotent το ingestion script του συνθετικού πακέτου `support-data/` πριν την εκκίνηση του `app` (`condition: service_completed_successfully`). ✋ με Knowledge.
7. Multi-stage build για το `Dockerfile` του application container με υποστήριξη Deep Agents και caching dependencies. ✋ με Interface και Workflow.

### Φάση 3 – Milestone Clean-Clone Test (Ημ. 4–5)
8. Εκτέλεση clean-clone test από το μηδέν μόνο με τις οδηγίες του README σε Windows, macOS και Linux.
9. Μέτρηση χρόνου εκκίνησης (<10 λεπτά συνολικά μαζί με το seeding). Καταγραφή στο `docs/CLEAN_CLONE_BENCHMARK.md`. ✋ με Quality.

### Φάση 4 – MCP Boundaries & Container Restart Resilience (Ημ. 6–8)
10. Υποστήριξη MCP transport (Simulated Procurement System MCP server & External Risk Feed) εντός του Compose δικτύου (`supplyguard_network`). ✋ με Workflow.
11. Έλεγχος ανθεκτικότητας σε container restarts (`docker compose restart app`): επιβεβαίωση ότι τα PostgreSQL checkpoints και audit logs παραμένουν ανέπαφα και δεν χάνεται κατάσταση. ✋ με Workflow και Quality.

### Φάση 5 – Final Polish & Demo Preparation (Ημ. 9–10)
12. Final polish του `README.md` (Quickstart, αρχιτεκτονικό διάγραμμα, troubleshooting ports/JVM, οδηγοί demo).
13. Τελικό clean-clone smoke test πριν την τελική παρουσίαση.
14. Συμμετοχή στις πρόβες του demo και επεξήγηση του infrastructure layer.

## Role checklist

- [ ] Συμφωνία αρχιτεκτονικών συμβολαίων και pinning νέων dependencies (`deepagents`, `chromadb`, `mcp`)
- [ ] `docker-compose.yml` με 5 services (`postgres`, `neo4j`, `chromadb`, `external-risk`, `app`)
- [ ] `.env.example` πλήρες με διαχωρισμό παραμέτρων
- [ ] Persistent volumes και graceful shutdown (`stop_grace_period: 15s`)
- [ ] Automated Compose `seed` service για πλήρη φόρτωση του `support-data/` χωρίς χειροκίνητα βήματα
- [ ] Clean-clone benchmark σε <10′ σε πολλαπλά λειτουργικά συστήματα
- [ ] MCP service transport συνδεδεμένο και λειτουργικό
- [ ] Persistence ελεγμένη μετά από hard container restart
- [ ] Τελικό clean-clone test πριν το demo
- [ ] Έχω commits και τουλάχιστον ένα review σε PR άλλου ρόλου
- [ ] Μπορώ να εξηγήσω ολόκληρη την αρχιτεκτονική υποδομής στο demo

## Backup
Ορίζεται στο `CONTRIBUTING_LOG.md`. Προτείνεται: Workflow.
