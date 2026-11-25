# HelpDesk Lite – Starter Data Package

Fictional data for Nimbus Analytics (Athens + London). All names, addresses and details are invented exercise assumptions.

| Dataset | Size | File(s) |
|---|---|---|
| Employees with team and office | 40 | `employees.csv` |
| Teams | 8 | `graph/teams.csv` |
| Applications | 12 | `graph/applications.csv`, `graph/application_dependencies.csv` |
| Services | 10 | `graph/services.csv`, `graph/service_dependencies.csv` |
| Open outages | 2 | `graph/outages.csv` |
| IT policies and how-to guides | 20 | `policies/*.md`, `policies/policy_index.csv` |
| Evaluation requests with expected action | 10 | `evaluation/eval_requests.csv` / `.jsonl` |

Extras: `graph/seed.cypher` (ready-to-run Neo4j seed generated from the CSVs), `graph/team_applications.csv` (which team uses which app, so "which teams are affected?" is answerable), `sql/init_tickets.sql` (simulated ticketing table with an idempotency key).

## Graph model (Neo4j)

```
(Employee)-[:MEMBER_OF]->(Team)        (Employee)-[:WORKS_IN]->(Office)
(Team)-[:USES]->(Application)
(Application)-[:DEPENDS_ON]->(Service)  (Service)-[:DEPENDS_ON]->(Service)
(Outage)-[:AFFECTS]->(Service)
```

Key chain for the demo: `Corporate VPN → VPN Gateway (S02) → Identity Provider (S01) ← OUT-001`.
Applications A09 (Client CRM) and A10 (Print Manager) do **not** depend on the Identity Provider.

## The deliberate data issues

1. **Outdated policy version** – `POL-002` exists twice: v1.0 (2024-03-01, `status: superseded`, immediate reset, 72 h) and v2.0 (2026-06-01, approval + identity verification, no reset during an IdP outage, 24 h). The version with the later effective date takes precedence.
2. **Missing team** – employee `E040 Nefeli Andreou` has `team_id = T09`, which does not exist in `teams.csv`, so the seed creates no `MEMBER_OF` edge. The assistant must handle this gracefully.
3. **Dangling policy reference** – `POL-005` (R22) and `POL-006` (R17) cite `POL-020` (onboarding/offboarding), which is not in the document store (only POL-001 to POL-019 exist). The assistant must not invent its content; it should say the referenced policy is unavailable and, if needed, escalate.

## Demo scenario

The demo message (`EV01`) is the VPN request. Expected behaviour: ask for device/office → find OUT-001 via dependencies → cite POL-001, POL-002 v2.0, POL-014 → propose **B: link to OUT-001** (not a reset) → wait for approval → survive a restart → write to the `tickets` table exactly once.

## Evaluation set coverage

| Action | Requests |
|---|---|
| A Answer from policy | EV03, EV09 |
| B Link to outage | EV01, EV02, EV05 |
| C Reset credentials | EV04 |
| D Open ticket | EV07, EV08 |
| E Escalate | EV06, EV10 |

## Loading

- **Neo4j:** `cypher-shell -u neo4j -p <password> -f starter-data/graph/seed.cypher` (or mount it in Compose).
- **pgvector:** ingest each `policies/*.md` (each has 20+ numbered rules with citable IDs such as `POL-002-v2.0-R09`), ideally chunking per rule; keep front-matter fields (`doc_id`, `version`, `effective_date`, `status`) as chunk metadata so answers can cite document and effective date.
- **Postgres:** run `sql/init_tickets.sql`; LangGraph's `PostgresSaver.setup()` creates checkpoint tables.
- **LangSmith:** upload `evaluation/eval_requests.jsonl` as a dataset.
