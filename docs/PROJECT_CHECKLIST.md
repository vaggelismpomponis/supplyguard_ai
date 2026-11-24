# Project Checklist – SupplyGuard AI

Project-wide πρόοδος για την πλατφόρμα **SupplyGuard AI** (Agentic Supply Chain Disruption & Recovery Platform - Capstone Project, Code.Hub × PwC).  
Τα αναλυτικά βήματα ανά ρόλο βρίσκονται στο [`roles/`](./roles/README.md). Τικάρουμε ένα item όταν είναι merged στο `develop`.

**Owner ενημέρωσης:** Quality (έλεγχος στο mid-week και πριν το demo).

---

## 1. Kick-off & Architecture Contracts (Εβδ. 1, Ημ. 1–2)

- [ ] Ρόλοι και backup ρόλοι ορίστηκαν (`CONTRIBUTING_LOG.md`)
- [ ] Repo branding και branch strategy συμφωνημένα (`main`/`develop` προστατευμένα)
- [ ] **Contracts**: Pydantic models (`DisruptionFact`, `OperationalImpact`, `RecoveryOption`, `ApprovalPayload`)
- [ ] **Contracts**: Tool signatures (`query_inventory`, `query_bom`, `query_supplier_graph`, `retrieve_documents`, `retrieve_incident_memories`)
- [ ] **Contracts**: Chainlit session ↔ `thread_id` mapping και RBAC scopes (`procurement`, `finance`, `public`)
- [ ] **Contracts**: MCP interfaces για Simulated Procurement System και External Risk Feed
- [ ] **Orchestration**: Αρχιτεκτονική Deep Agents (`deepagents` / `create_deep_agent`) με planning middleware
- [ ] Docker Compose stack με 5 services (`postgres`, `neo4j`, `chromadb`, `external-risk`, `app`)
- [ ] `.env.example` πλήρες με αυστηρά pinned versions (`PINNED_VERSIONS.md`)
- [ ] Tasks κατηγοριοποιημένα ανά ρόλο στο GitHub Project board

---

## 2. Data Package Ingestion & Multi-Vector Pipeline (Ημ. 2–4)

- [ ] Σχεσιακό σχήμα PostgreSQL για operational tables (suppliers, components, products, BOM lines, POs, inventory, customer orders)
- [ ] Neo4j multi-tier supply chain graph μοντέλο και idempotent seeding script
- [ ] Μοντελοποίηση σχέσης κοινού upstream κατασκευαστή (Atlas & Delta) στο Neo4j
- [ ] Κατάτμηση και ευρετηρίαση 212 εγγράφων με metadata provenance (`source_id`, `version`/`effective_date`, `access_scope`)
- [ ] Ευρετηρίαση στο PostgreSQL `pgvector` και στο `ChromaDB`
- [ ] Ευρετηρίαση 300 ιστορικών disruption cases και 40 approved incident memories
- [ ] Automated Compose `seed` service (`docker compose run seed`) χωρίς χειροκίνητα βήματα
- [ ] Walking skeleton με Deep Agents και mock tools
- [ ] Clean-clone benchmark σε <10′ σε πολλαπλά λειτουργικά συστήματα

---

## 3. Deep Agents Specialization & Business Calculators (Ημ. 4–6)

- [ ] Triage Subagent με εξαγωγή S001, MC-17, 12-day delay, spending cap €75k
- [ ] Clarification interrupt όταν τα στοιχεία είναι ελλιπή ή ασαφή (π.χ. "Atlas")
- [ ] Operational Impact Analyzer Subagent (διαχωρισμός usable vs reserved/quarantined stock, Katowice/Lyon impact, 5,350 units uncovered)
- [ ] Contract & Provenance Specialist Subagent (εντοπισμός ληγμένης πιστοποίησης Borealis, συγκρούσεις συμβολαίου/email)
- [ ] Supply Graph Subagent (εντοπισμός κοινού tier-2 upstream προμηθευτή Atlas/Delta μέσω Neo4j Cypher)
- [ ] Deterministic Business Calculators (υπολογισμός Revenue at Risk vs Recovery Cost χωρίς LLM math hallucinations)
- [ ] Recovery Strategy Optimizer Subagent (σύγκριση τουλάχιστον 3 στρατηγικών)
- [ ] Simulated Procurement MCP integration για εκτέλεση παραγγελιών αγοράς

---

## 4. UI, Approval Gate & Restart Resilience (Ημ. 6–8)

- [x] Chainlit RBAC authentication (Procurement Manager, Finance Controller, Read-only Guest)
- [x] Dynamic retrieval filtering βάσει του ενεργού ρόλου χρήστη
- [x] Telemetry dashboard με live ένδειξη προόδου subagents
- [x] Recovery Strategy Comparison Matrix με διακριτές στήλες Recovery Cost και Revenue at Risk
- [x] Strict Approval Card με ακριβές payload (προμηθευτής, ποσότητα, τιμή, όριο €75k)
- [x] Αποτροπή διπλού κλικ (`asyncio.Lock`) και έλεγχος Modify Plan (επανεπικύρωση)
- [x] Container restart resilience (`docker compose restart app`) εν μέσω αναμονής έγκρισης
- [x] Απρόσκοπτο resume από το PostgreSQL checkpoint χωρίς απώλεια κατάστασης
- [x] Idempotent εκτέλεση: καμία διπλή δημιουργία Purchase Order στο σύστημα προμηθειών
- [x] Εξαγωγή δομημένου Incident Report και αποθήκευση approved incident memory

---

## 5. Evaluation, Retrieval Benchmark, Red-Teaming & Demo (Ημ. 8–10)

- [ ] LangSmith evaluation suite στα 105 held-out scenarios και στο MC-17 benchmark
- [ ] Automated evaluators (triage, numerical accuracy, policy adherence, dependency awareness, human approval guarantee)
- [ ] Retrieval benchmark report (σύγκριση Recall@K, Precision@K, Latency: `pgvector` vs `ChromaDB` vs `Hybrid`)
- [ ] Adversarial testing: εξουδετέρωση του φυτεμένου prompt-injection εγγράφου
- [ ] Multi-turn follow-up Q&A από τη μνήμη της υπόθεσης (αύξηση budget, απόρριψη Helios, προστασία VIP πελατών)
- [ ] 10-minute Live Demo script (`DEMO_SCRIPT.md`)
- [ ] ≥2 πλήρεις πρόβες live demo με rotation παρουσιαστών
- [ ] Τελικό clean-clone smoke test πριν την τελική παράδοση
- [ ] Final polish README, `CONTRIBUTING.md` και `ARCHITECTURE_CONTRACTS.md`

---

## 6. Definition of Done

- [ ] `docker compose up -d` ξεκινά και τα 5 services σε <10′ από καθαρό clone.
- [ ] Το Compose `seed` service φορτώνει αυτόματα όλα τα δεδομένα χωρίς χειροκίνητη παρέμβαση.
- [ ] Η ορχήστρωση εκτελείται μέσω Deep Agents (`deepagents`) με planning middleware και subagents.
- [ ] Καμία ενέργεια προμήθειας (Purchase Order) δεν εκτελείται χωρίς ρητή ανθρώπινη έγκριση.
- [ ] Το approval payload είναι απαραβίαστο και σέβεται το spending cap των €75,000.
- [ ] Το resume μετά από container crash δουλεύει άψογα, με εγγύηση μηδενικής διπλής εκτέλεσης (strict idempotency).
- [ ] Το σύστημα διαχωρίζει αυστηρά το Revenue at Risk από το Recovery Cost.
- [ ] Οι απορρίψεις προμηθευτών τεκμηριώνονται (Helios = αργός, Borealis = ληγμένο cert, Delta = κοινός upstream).
- [ ] Το φυτεμένο κακόβουλο έγγραφο prompt injection αναφέρεται και εξουδετερώνεται.
- [ ] Retrieval benchmark report παραδίδεται συγκρίνοντας `pgvector`, `ChromaDB` και `Hybrid Retrieval`.
- [ ] Traces στο LangSmith και αξιολόγηση στα 105 held-out σενάρια.
- [ ] Όλα τα μέλη της ομάδας έχουν commits και reviews και μπορούν να εξηγήσουν ολόκληρη τη ροή.

---

## 7. Πρόοδος ανά ρόλο

Ενημερώνεται χειροκίνητα από τα role checklists.

| Ρόλος | Checklist | Πρόοδος | Owner | Backup |
|---|---|---|---|---|
| Platform | [`platform.md`](./roles/platform.md) | 0/9 | @vaggelismpomponis | Workflow |
| Interface | [`interface.md`](./roles/interface.md) | 13/13 | @AlexZarkalis | Quality |
| Workflow | [`workflow.md`](./roles/workflow.md) | 0/13 | @VickyMil-ai | Knowledge |
| Knowledge | [`knowledge.md`](./roles/knowledge.md) | 0/12 | @stef-fot | Platform |
| Quality | [`quality.md`](./roles/quality.md) | 0/15 | @VickyMil-ai | Interface |

---

## 8. Χαρτογράφηση Tasks ανά Ρόλο στο GitHub

Όλα τα tasks είναι δημιουργημένα στο GitHub repo ως issues [#32 έως #93](https://github.com/vaggelismpomponis/supplyguard_ai/issues).

- **Platform (#32–#40):** 9 tasks (`[Platform] Kick-off`, `Stack`, `Milestone`, `Completion`)
- **Interface (#41–#53):** 13 tasks (`[Interface] Kick-off`, `Skeleton`, `Milestone`, `Completion`)
- **Workflow (#54–#66):** 13 tasks (`[Workflow] Kick-off`, `Skeleton`, `Milestone`, `Completion` - Deep Agents)
- **Knowledge (#67–#78):** 12 tasks (`[Knowledge] Kick-off`, `Dataset`, `Graph`, `Seeding`, `Completion`)
- **Quality (#79–#93):** 15 tasks (`[Quality] Kick-off`, `Tracing`, `Dataset`, `Evaluators`, `Completion`)

Πλήρης πίνακας με links και περιγραφές στο [`docs/KANBAN_TASKS.md`](./KANBAN_TASKS.md).
