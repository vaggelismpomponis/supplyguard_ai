# Project Checklist – SupplyGuard AI

Project-wide πρόοδος για την πλατφόρμα **SupplyGuard AI** (Agentic Supply Chain Disruption & Recovery Platform - Capstone Project, Code.Hub × PwC).  
Τα αναλυτικά βήματα ανά ρόλο βρίσκονται στο [`roles/`](./roles/README.md). Τικάρουμε ένα item όταν είναι merged στο `develop`.

**Owner ενημέρωσης:** Quality (έλεγχος στο mid-week και πριν το demo).

---

## 1. Kick-off & Architecture Contracts (Εβδ. 1, Ημ. 1–2)

- [ ] Ρόλοι και backup ρόλοι ορίστηκαν (`CONTRIBUTING_LOG.md`)
- [ ] Repo branding και branch strategy συμφωνημένα (`main`/`develop` προστατευμένα)
- [x] **Contracts**: Pydantic models (`DisruptionFact`, `OperationalImpact`, `RecoveryOption`, `ApprovalPayload`)
- [x] **Contracts**: Tool signatures (`query_inventory`, `query_bom`, `query_supplier_graph`, `retrieve_documents`, `retrieve_incident_memories`)
- [x] **Contracts**: Chainlit session ↔ `thread_id` mapping και RBAC scopes (`procurement`, `finance`, `public`, `internal`, `finance-confidential`)
- [x] **Contracts**: MCP interfaces για Simulated Procurement System και External Risk Feed
- [x] **Orchestration**: Αρχιτεκτονική Deep Agents (`deepagents` / `create_deep_agent`) με planning middleware
- [x] Docker Compose stack με 5 services (`postgres`, `neo4j`, `chromadb`, `external-risk`, `app`)
- [x] `.env.example` πλήρες με αυστηρά pinned versions (`PINNED_VERSIONS.md`)
- [x] Tasks κατηγοριοποιημένα ανά ρόλο στο GitHub Project board

---

## 2. Data Package Ingestion & Multi-Vector Pipeline (Ημ. 2–4)

- [x] Σχεσιακό σχήμα PostgreSQL για operational tables (suppliers, components, products, BOM lines, POs, inventory, customer orders)
- [x] Neo4j multi-tier supply chain graph μοντέλο και idempotent seeding script
- [x] Μοντελοποίηση σχέσης κοινού upstream κατασκευαστή (Atlas & Delta) στο Neo4j
- [x] Κατάτμηση και ευρετηρίαση 212 εγγράφων με metadata provenance (`source_id`, `version`/`effective_date`, `access_scope`)
- [x] Ευρετηρίαση στο PostgreSQL `pgvector` και στο `ChromaDB`
- [x] Ευρετηρίαση 300 ιστορικών disruption cases και 40 approved incident memories
- [x] Automated Compose `seed` service (`docker compose run seed`) χωρίς χειροκίνητα βήματα
- [x] Walking skeleton με Deep Agents και tools (με graceful offline fallback χωρίς LLM keys)
- [ ] Clean-clone benchmark σε <10′ σε πολλαπλά λειτουργικά συστήματα *(επαληθεύτηκε σε Linux `x86_64` και macOS Apple Silicon· απομένει το Windows run)*

---

## 3. Deep Agents Specialization & Business Calculators (Ημ. 4–6)

- [x] Triage Subagent με εξαγωγή S001, MC-17, 12-day delay, spending cap €75k
- [x] Clarification interrupt όταν τα στοιχεία είναι ελλιπή ή ασαφή (π.χ. "Atlas")
- [x] Operational Impact Analyzer Subagent (διαχωρισμός usable vs reserved/quarantined stock, Katowice/Lyon impact, 5,350 units uncovered)
- [x] Contract & Provenance Specialist Subagent (εντοπισμός ληγμένης πιστοποίησης Borealis, συγκρούσεις συμβολαίου/email)
- [x] Supply Graph Subagent (εντοπισμός κοινού tier-2 upstream προμηθευτή Atlas/Delta μέσω Neo4j Cypher)
- [x] Deterministic Business Calculators (υπολογισμός Revenue at Risk vs Recovery Cost χωρίς LLM math hallucinations)
- [x] Recovery Strategy Optimizer Subagent (σύγκριση τουλάχιστον 3 στρατηγικών)
- [x] Simulated Procurement MCP integration για εκτέλεση παραγγελιών αγοράς

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

- [x] Evaluation suite στα 105 held-out scenarios και στο MC-17 benchmark (`99/99` non-restart + `6/6` restart = `105/105`)
- [x] Automated evaluators (triage, numerical accuracy, policy adherence, dependency awareness, human approval guarantee)
- [x] Retrieval benchmark report (σύγκριση Recall@K, Precision@K, Latency: `pgvector` vs `ChromaDB` vs `Hybrid`)
- [x] Adversarial testing: εξουδετέρωση του φυτεμένου prompt-injection εγγράφου (`17/17` attacks neutralized)
- [x] Multi-turn follow-up Q&A από τη μνήμη της υπόθεσης (αύξηση budget, απόρριψη Helios, προστασία VIP πελατών)
- [x] 10-minute Live Demo script (`DEMO_SCRIPT.md`)
- [ ] ≥2 πλήρεις πρόβες live demo με rotation παρουσιαστών
- [ ] Τελικό clean-clone smoke test πριν την τελική παράδοση
- [x] Final polish README, `CONTRIBUTING.md` και `ARCHITECTURE_CONTRACTS.md`

---

## 6. Definition of Done

- [x] `docker compose up -d` ξεκινά και τα 5+1 services σε <10′ (`seed` exit 0, `app` healthy).
- [x] Το Compose `seed` service φορτώνει αυτόματα όλα τα δεδομένα χωρίς χειροκίνητη παρέμβαση.
- [x] Η ορχήστρωση εκτελείται μέσω Deep Agents (`deepagents`) με planning middleware και subagents.
- [x] Καμία ενέργεια προμήθειας (Purchase Order) δεν εκτελείται χωρίς ρητή ανθρώπινη έγκριση.
- [x] Το approval payload είναι απαραβίαστο και σέβεται το spending cap των €75,000.
- [x] Το resume μετά από container crash δουλεύει άψογα, με εγγηση μηδενικής διπλής εκτέλεσης (strict idempotency).
- [x] Το σύστημα διαχωρίζει αυστηρά το Revenue at Risk από το Recovery Cost.
- [x] Οι απορρίψεις προμηθευτών τεκμηριώνονται (Helios = αργός, Borealis = ληγμένο cert, Delta = κοινός upstream).
- [x] Το φυτεμένο κακόβουλο έγγραφο prompt injection αναφέρεται και εξουδετερώνεται.
- [x] Retrieval benchmark report παραδίδεται συγκρίνοντας `pgvector`, `ChromaDB` και `Hybrid Retrieval`.
- [x] Evaluators και 105 held-out σενάρια επαληθευμένα (`99/99` + `6/6` restart· `LANGSMITH_API_KEY` ενεργοποιεί remote tracing όταν οριστεί).
- [ ] Όλα τα μέλη της ομάδας έχουν commits και reviews και μπορούν να εξηγήσουν ολόκληρη τη ροή.

---

## 7. Πρόοδος ανά ρόλο

Ενημερώνεται χειροκίνητα από τα role checklists. Τελευταία καταμέτρηση: 2026-11-24 (integration verification).

| Ρόλος | Checklist | Πρόοδος | Owner | Backup |
|---|---|---|---|---|
| Platform | [`platform.md`](./roles/platform.md) | 10/11 | @vaggelismpomponis | Workflow |
| Interface | [`interface.md`](./roles/interface.md) | 14/14 | @AlexZarkalis | Quality |
| Workflow | [`workflow.md`](./roles/workflow.md) | 12/15 | @VickyMil-ai | Knowledge |
| Knowledge | [`knowledge.md`](./roles/knowledge.md) | 12/14 | @stef-fot | Platform |
| Quality | [`quality.md`](./roles/quality.md) | 8/13 | @VickyMil-ai | Interface |

---

## 8. Χαρτογράφηση Tasks ανά Ρόλο στο GitHub

Όλα τα tasks είναι δημιουργημένα στο GitHub repo ως issues [#32 έως #93](https://github.com/vaggelismpomponis/supplyguard_ai/issues).

- **Platform (#32–#40):** 9 tasks (`[Platform] Kick-off`, `Stack`, `Milestone`, `Completion`)
- **Interface (#41–#53):** 13 tasks (`[Interface] Kick-off`, `Skeleton`, `Milestone`, `Completion`)
- **Workflow (#54–#66):** 13 tasks (`[Workflow] Kick-off`, `Skeleton`, `Milestone`, `Completion` - Deep Agents)
- **Knowledge (#67–#78):** 12 tasks (`[Knowledge] Kick-off`, `Dataset`, `Graph`, `Seeding`, `Completion`)
- **Quality (#79–#93):** 15 tasks (`[Quality] Kick-off`, `Tracing`, `Dataset`, `Evaluators`, `Completion`)

Πλήρης πίνακας με links και περιγραφές στο [`docs/KANBAN_TASKS.md`](./KANBAN_TASKS.md).

---

## 9. Mid-week audit (#86)

**Ελεγκτής:** Quality (@VickyMil-ai) · **Ημερομηνία:** 2026-11-24 · **Βάση:** `develop` στο `69c85a2`

Κάθε item τικάρεται μόνο με απόδειξη στο `develop` (αρχείο ή εντολή). Τα items χωρίς απόδειξη μένουν ανοιχτά, ακόμη κι αν ο ρόλος τα θεωρεί έτοιμα.

### 9.1 Τικαρίστηκαν (11)

| Item | Απόδειξη |
|---|---|
| Pydantic models | `src/core/contracts.py` (`DisruptionFact`, `OperationalImpact`, `RecoveryOption`, `ApprovalPayload`) |
| MCP interfaces | `PurchaseOrderRequest/Receipt`, `SupplierRiskInfo` στο `src/core/contracts.py`, `src/mcp/` |
| Compose stack | `docker-compose.yml`: `postgres`, `neo4j`, `chromadb`, `external-risk`, `app` (+ `seed`) |
| `.env.example` και pinning | `.env.example`, `requirements.txt` (όλα με `==`), images με tags |
| Tasks στο board | issues #32–#93, [`KANBAN_TASKS.md`](./KANBAN_TASKS.md) |
| Σχεσιακό σχήμα | `docker/postgres/init.sql` |
| Neo4j μοντέλο και idempotent seed | `scripts/seed.py` (`MERGE` για nodes και relations) |
| Κοινός upstream Atlas/Delta | `SOURCES_FROM` στο seed· S001 και S005 → U01 στο `rel_sources_from.csv` |
| 212 έγγραφα με provenance | `seed_documents()`: `doc_id`, `effective_date`, `access_scope`, metadata με `version` |
| pgvector και ChromaDB | `policy_chunks` και collection `supplyguard_docs` |
| Compose `seed` service | service `seed` στο `docker-compose.yml` |

### 9.2 Τικαρισμένα από το PR #97 (Interface), με επιφύλαξη

Τα 10 items της §4 τικαρίστηκαν από το Interface PR #97. Υπάρχει κώδικας για όλα στο `src/app.py` και στο `src/agent/schemas.py` (RBAC από `users.csv`, scoped retrieval, telemetry steps, strategy matrix, approval card με `payload_hash` και `asyncio.Lock`, Modify Plan, incident report). Τα κρατάμε τικαρισμένα. Τρία items όμως ελέγχονται μόνο με run, και το run δεν έχει γίνει στο SupplyGuard stack:

| Item | Επαλήθευση που λείπει |
|---|---|
| Container restart resilience | [`RESTART_TEST_SCENARIO.md`](./RESTART_TEST_SCENARIO.md), Procedures A και C |
| Resume από το Postgres checkpoint | ίδιο |
| Καμία διπλή PO | ίδιο, μαζί με το εύρημα για τα `PO-SUP-2026-9001…` ids μετά από restart |

**Εύρημα (2026-11-24): η κατάσταση της υπόθεσης δεν είναι στο Postgres.** Η ροή SupplyGuard του PR #97 κρατά κάθε υπόθεση στο in-memory dict `_CASE_STORE` του `src/app.py`, όχι στο checkpointer. Μετά από `docker compose restart app` η υπόθεση χάνεται. Το «Resume the case…» χωρίς κατάσταση στη μνήμη φτιάχνει από την αρχή μια default υπόθεση MC-17 (`src/app.py`, `_handle_supplyguard_message`) αντί να επαναφέρει την πραγματική. Άρα τα τρία items πάνω δεν ισχύουν ακόμη για τη ροή SupplyGuard. → Interface, Workflow (η κατάσταση πρέπει να ζει στο checkpoint του agent).

Σημείωση: η pipeline του PR #97 είναι deterministic κώδικας μέσα στο UI layer, όχι Deep Agents. Μπορεί να στηρίξει το evaluation harness μέχρι να υπάρξει ο Deep Agent.

### 9.3 Ανοιχτά με εύρημα

| Item | Εύρημα | Ρόλος |
|---|---|---|
| Ρόλοι και backups | Στο `CONTRIBUTING.md` οι owners ήταν _TBD_· διορθώνεται στο #93 | Quality |
| Repo branding / branch strategy | Τεκμηριωμένα (`CONTRIBUTING.md`, `GIT_GUIDE.md`), αλλά το `CONTRIBUTING.md` είναι ακόμη **draft** (κανάλι, stand-up, pair session _TBD_) | Όλοι |
| Tool signatures | Το `retrieve_incident_memories` δεν υπάρχει στο `ARCHITECTURE_CONTRACTS.md` §4· κανένα tool του §4 δεν υλοποιείται ακόμη (`src/knowledge/tools.py` είναι ακόμη του HelpDesk Lite) | Knowledge, Workflow |
| Chainlit ↔ `thread_id`, RBAC | Το `AccessScope` υπάρχει, αλλά το `users.csv` έχει και scopes `internal`, `finance-confidential` που δεν υπάρχουν στο enum (`procurement`, `finance`, `public`)· το PR #97 πρόσθεσε RBAC με role switcher, αλλά τα δύο σύνολα scopes παραμένουν διαφορετικά | Interface, Knowledge |
| Deep Agents orchestration | Το `deepagents==0.1.0` είναι pinned αλλά δεν χρησιμοποιείται πουθενά· το `src/agent/` είναι ακόμη ο LangGraph γράφος του HelpDesk Lite | Workflow |
| 300 ιστορικά cases, 40 memories | Ο πίνακας `historical_disruption_cases` υπάρχει, αλλά το seed δεν φορτώνει ούτε αυτά ούτε το `approved_incident_memories.jsonl` | Knowledge, Platform |
| Walking skeleton | Εξαρτάται από το Deep Agents orchestration | Workflow |
| Clean-clone <10′ | Οι χρόνοι στο `CLEAN_CLONE_BENCHMARK.md` είναι της 2026-11-18 (πριν το SupplyGuard stack)· νέο run στο #85, §8 | Platform, Quality |
| Provenance στο Neo4j | Το `scripts/seed.py` δεν γράφει `sourceId`/`effectiveDate` σε κανένα node ή relationship, ούτε `Supplier.certificationExpiry` (το `load.cypher` τα γράφει). Βλ. [`KNOWLEDGE_GRAPH.md`](./KNOWLEDGE_GRAPH.md#known-gap-in-the-seed) | Knowledge, Platform |

### 9.4 Ασυνέπειες στα έγγραφα

1. **IDs προμηθευτών.** Το `ARCHITECTURE_CONTRACTS.md` §5 γράφει Helios = S003, Borealis = S002, Delta = S004 και "Epsilon (S005)". Τα δεδομένα (`suppliers.csv`, `golden_scenario.json`) έχουν Helios = S002, Borealis = S003, Cordillera = S004, Delta = S005, χωρίς Epsilon. Ισχύουν τα δεδομένα. → Workflow, Knowledge.
2. **Πρόοδος ρόλων.** Ο πίνακας §7 είχε σύνολα που δεν ταίριαζαν με τα role files (Platform 9/9 αντί 10/11, Interface 13/13 αντί 14/14, και διαφορετικά σύνολα για Workflow, Knowledge, Quality). Ενημερώθηκαν όλα από τα role files.
3. **Παλιά έγγραφα του HelpDesk Lite.** Ξαναγράφτηκαν για το SupplyGuard: `DEMO_SCRIPT.md`, `REHEARSAL_LOG.md`, `RESTART_TEST_SCENARIO.md`, `eval/`, `README.md` (από το restart section και μετά), `GIT_GUIDE.md` (GitHub αντί για Codeberg), `KNOWLEDGE_GRAPH.md`, `src/knowledge/README.md`. Διαγράφηκαν τα `PROJECT_NOTES.md` και `KNOWLEDGE_HANDOFF.md` (σημειώσεις του warm-up project). Το Docker network `helpdesk_network` αφαιρέθηκε και το default `POSTGRES_DB` στο `src/db/connection.py` έγινε `supplyguard` (ήταν `helpdesk`).

### 9.5 Κώδικας του HelpDesk Lite που μένει (task για Workflow)

Ο κώδικας αυτός είναι ακόμη ενεργός και αντικαθίσταται μαζί με τον SupplyGuard Deep Agent, όχι με μετονομασία. Προτείνεται ένα issue για Workflow με αυτή τη λίστα.

| Περιοχή | Αρχεία | Τι κάνει σήμερα |
|---|---|---|
| Agent | `src/agent/graph.py`, `nodes.py`, `models.py`, `mocks.py` | LangGraph γράφος του HelpDesk (extract_fields → retrieve_policy → check_graph → decide_action → approval)· fallback του `src/app.py` για μηνύματα εκτός SupplyGuard και για legacy approvals |
| UI fallback | `src/app.py` (ενότητες «Legacy HelpDesk»), `tests/test_ui.py` (legacy μέρη) | Μορφοποίηση `ActionProposal`, `PolicyResult`, `GraphResult`, outages |
| Knowledge | `src/knowledge/tools.py`, `models.py`, `mocks.py`, `ingest.py`, `seed_graph.py` | `retrieve_policy`, `check_graph` (Application/Service/Outage)· αντικαθίστανται από τα tools του contract §4 |
| Database | πίνακας `tickets` (`docker/postgres/init.sql`), `migrations/001_upgrade_schema.sql`, `create_ticket_idempotent` και πεδία `employee`/`application` του `audit_log` (`src/db/idempotency.py`) | Idempotency για HelpDesk tickets |
| Tests | `tests/test_graph.py`, `test_knowledge.py`, `test_restart_idempotency.py`, `test_workflow_compose_milestone.py`, μέρη του `test_postgres_schema.py` | Ελέγχουν τον HelpDesk agent. Το `test_restart_idempotency.py` ψάχνει container `helpdesk_app`, που δεν υπάρχει πια, οπότε **παρακάμπτεται πάντα σιωπηλά**· το `test_workflow_compose_milestone.py` περιμένει τα 10 HelpDesk examples και αποτυγχάνει |

### 9.6 Επόμενος έλεγχος & Επίλυση Ευρημάτων (2026-11-24)

Όλα τα τεχνικά ευρήματα των §§9.2–9.5 επιλύθηκαν και επαληθεύτηκαν στο live Compose stack:
- **Checkpoint & UI State:** Αφαιρέθηκε το in-memory `_CASE_STORE` από το `src/app.py`· η κατάσταση αποθηκεύεται στο PostgreSQL (`thread_states`, `audit_log`) και ανακτάται μετά από `docker compose restart app`.
- **MCP Idempotency & PO IDs:** Προστέθηκε `action_id UNIQUE` στον `purchase_orders`, real `thread_id` στο `audit_log`, και collision-free IDs (`PO-SUP-2026-<sha256(action_id)[:8]>`).
- **Knowledge & Provenance:** Φορτώνονται όλα τα 18 CSV tables, τα 300 historical cases + 40 approved memories (`346` rows μετά από restart approvals), `sourceId`/`effectiveDate` στο Neo4j, και τα tools του §4 (`src/knowledge/tools.py`).
- **Workflow Deep Agents & Harness:** Υλοποιήθηκε το `src/agent/eval_harness.py`, τα kill points `SUPPLYGUARD_CRASH_AT`, τα ντετερμινιστικά εργαλεία (`src/agent/calculators.py`), και αποσύρθηκε πλήρως ο legacy κώδικας και τα tests του HelpDesk Lite.
- **Contracts & Docs:** Ενημερώθηκε το `docs/ARCHITECTURE_CONTRACTS.md` §5 (`S001–S006`, χωρίς Epsilon) και το `AccessScope` enum. Απομένουν μόνο ομαδικές διαδικασίες (live demo rehearsals ≥2 και PR reviews μελών).
