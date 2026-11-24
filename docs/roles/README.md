# Role Map – SupplyGuard AI

Οδηγός για το πώς δουλεύει ο κάθε ρόλος στην πλατφόρμα **SupplyGuard AI** (Agentic Supply Chain Disruption & Recovery Platform - Capstone Project, Code.Hub × PwC, October 2026).

Πηγές: [Capstone Project MD](../Capstone%20project%20-%20Code.Hub%20-%20PwC%20-%20Agentic%20AI%20Bootcamp.md), [ARCHITECTURE_CONTRACTS](../ARCHITECTURE_CONTRACTS.md), [PROJECT_CHECKLIST](../PROJECT_CHECKLIST.md), [AGENTS](../../AGENTS.md).

## Πώς το χρησιμοποιούμε

| Αρχείο | Σκοπός |
|---|---|
| [`platform.md`](./platform.md) | Βήματα και role checklist του Platform (Docker stack: Postgres, Neo4j, ChromaDB, MCP, Compose seed) |
| [`interface.md`](./interface.md) | Βήματα και role checklist του Interface (Chainlit UI, RBAC, Investigation Telemetry, Strategy Comparison, Approval Cards) |
| [`workflow.md`](./workflow.md) | Βήματα και role checklist του Workflow (Deep Agents orchestration, Planning, Subagents, Deterministic Tools, Approval Gate) |
| [`knowledge.md`](./knowledge.md) | Βήματα και role checklist του Knowledge (Data package ingestion, Neo4j multi-tier graph, pgvector + ChromaDB, Hybrid retrieval) |
| [`quality.md`](./quality.md) | Βήματα και role checklist του Quality (105 eval cases, retrieval benchmarks, adversarial red-teaming, demo script) |
| [`../PROJECT_CHECKLIST.md`](../PROJECT_CHECKLIST.md) | Project-wide checklist: milestones, contracts, Definition of Done, Kanban task mapping |
| [`../CONTRIBUTING_LOG.md`](../CONTRIBUTING_LOG.md) | Log αποφάσεων που περνούν στο `CONTRIBUTING.md` |

**Κανόνες χρήσης**
1. Κάθε ρόλος τικάρει μόνο το δικό του role checklist, μέσα στο PR που ολοκληρώνει το βήμα.
2. Το project-wide checklist τικάρεται όταν το αντίστοιχο milestone/deliverable είναι merged στο `develop` (το τικάρει ο owner του item).
3. Κάθε αρχιτεκτονική απόφαση ή αλλαγή κανόνα καταγράφεται στο `CONTRIBUTING_LOG.md`.
4. Ένα βήμα με ✋ χρειάζεται επίσημο handoff και αποδοχή από άλλον ρόλο πριν θεωρηθεί ολοκληρωμένο.

## Συνολική προσέγγιση

1. **Contracts πρώτα (Εβδ. 1, Ημ. 1–2, όλοι).** Domain schemas (`IncidentCase`, `OperationalImpact`, `RecoveryStrategy`, `ApprovalPayload`), tool signatures, RBAC scopes (`procurement`, `finance`, `public`) και MCP boundaries συμφωνούνται πριν γραφτεί κώδικας.
2. **Deep Agents αντί LangGraph.** Η ορχήστρωση υλοποιείται μέσω του **Deep Agents harness** (`deepagents` / `create_deep_agent`) με ενσωματωμένο dynamic planning middleware, context scratchpad και εξειδικευμένους subagents, αντικαθιστώντας τη χειροκίνητη καλωδίωση state machine του LangGraph.
3. **Data Package Ingestion (Ημ. 2–4).** Φόρτωση του πλήρους συνθετικού πακέτου `support-data/` (60 suppliers, 300 components, 80 products, 616 BOM lines, 2k POs, 1k inventory records, production schedules, 1,500 orders, 212 documents, 300 cases, 40 memories) σε Postgres, Neo4j, pgvector και ChromaDB.
4. **Walking skeleton με Deep Agents & Mocks (Ημ. 2–4).** End-to-end ροή του reference incident (S001 Atlas Components 12-day delay για MC-17, spend cap €75k) με mock tools.
5. **Αντικατάσταση mocks με πραγματικά tools & MCP (Ημ. 5–7).** Σύνδεση με παραγωγικά tools ανάκτησης, live Cypher queries στο Neo4j και simulated procurement MCP server.
6. **Evaluation, Retrieval Benchmark, Red-Teaming & Demo (Ημ. 8–10).** 105 held-out evaluation scenarios, benchmark ανάκτησης (pgvector vs ChromaDB vs Hybrid), red-team prompt injection tests και 10-minute live demo rehearsal.

## Ροή εξαρτήσεων μεταξύ ρόλων

```text
Contracts (όλοι)
   ├─ Platform  ──► Stack (Postgres+pgvector, Neo4j, ChromaDB, MCP, Compose seed) ──► όλοι
   ├─ Knowledge ──► Ingestion, Neo4j Graph, pgvector/ChromaDB, Hybrid Tools ──► Workflow
   ├─ Workflow  ──► Deep Agents (Planner, 6 Subagents, Deterministic Calculators, Interrupt) ──► Interface
   ├─ Interface ──► Chainlit UI (RBAC, Telemetry, Strategy Matrix, Approval Card, Resume) ──► Workflow, Quality
   └─ Quality   ──► 105 Eval Cases, Retrieval Benchmark, Adversarial Red-Teaming ──► όλοι (αποδοχή)
```

## Κοινοί κανόνες για όλους τους ρόλους

- Branch από ενημερωμένο `develop`: `feature/<περιγραφή>`, `bugfix/<περιγραφή>`, PR → `develop`, Squash merge από reviewer. Όχι self-merge, PR <300 γραμμές, review <24 ώρες.
- Commits σε Conventional Commits 1.0.0, με scope: `agent`, `ui`, `mcp`, `db`, `neo4j`, `retrieval`, `approval`, `eval`, `docker`, `docs`, `deps`.
- **Αυστηρή ανθρώπινη έγκριση (Human-in-the-Loop):** Καμία δημιουργία Purchase Order ή αλλαγή operational state στο σύστημα simulated procurement χωρίς ρητή έγκριση. Το approval payload είναι απαραβίαστο (supplier, quantity, price, cap ≤ €75k) · οποιαδήποτε τροποποίηση ακυρώνει την κατάσταση και απαιτεί εκ νέου επικύρωση και έγκριση.
- **Idempotency & Persistence:** Αν η εφαρμογή κάνει restart κατά την αναμονή έγκρισης, η συνεδρία συνεχίζεται απρόσκοπτα από το PostgreSQL checkpoint χωρίς διπλή εκτέλεση.
- **Διαχωρισμός Revenue at Risk vs Recovery Cost:** Οι οικονομικές εκθέσεις διαχωρίζουν αυστηρά το διακυβευόμενο εισόδημα από το κόστος ανάκαμψης χωρίς διπλοϋπολογισμούς.
- **Ανθεκτικότητα σε Prompt Injections:** Το περιεχόμενο που ανακτάται από έγγραφα (π.χ. emails, supplier notices) αντιμετωπίζεται ως untrusted data και δεν επιτρέπεται να αποκτήσει εξουσία πάνω στον agent.
- **Κανένα credential στο repo.** Ρυθμίσεις από environment variables, αυστηρό version pinning στο `requirements.txt`.
- Κάθε μέλος πρέπει να μπορεί να εξηγήσει ολόκληρη την αρχιτεκτονική και τη ροή στο live demo.

## Rotation reviews (προτεινόμενο)

| PR από | Review από |
|---|---|
| Platform | Workflow |
| Workflow | Knowledge |
| Knowledge | Interface |
| Interface | Quality |
| Quality | Platform |
