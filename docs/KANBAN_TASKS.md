# SupplyGuard AI – Kanban Project Tasks Board

Αυτό το αρχείο περιέχει όλα τα tasks (κάρτες / issues) έτοιμα για αντιγραφή ή εισαγωγή στο Kanban Project Board της ομάδας (π.χ. στο Codeberg / GitHub Projects / Jira).

---

## Περιεχόμενα
- [Πίνακας Επισκόπησης Tasks (KAN-01 έως KAN-30)](#πίνακας-επισκόπησης-tasks)
- [Φάση 1: Kick-off, Architecture Contracts & Deep Agents Harness Setup (Ημ. 1–2)](#φάση-1-kick-off-contracts--deep-agents-setup-ημ-12)
- [Φάση 2: Data Ingestion, Knowledge Graph & Multi-Vector Pipeline (Ημ. 2–4)](#φάση-2-data-ingestion-knowledge-graph--multi-vector-pipeline-ημ-24)
- [Φάση 3: Deep Agents Specialization, Sub-Agents & Simulated MCP (Ημ. 4–6)](#φάση-3-deep-agents-specialization-sub-agents--simulated-mcp-ημ-46)
- [Φάση 4: Chainlit UI, Human Approval Gate & Restart Resilience (Ημ. 6–8)](#φάση-4-chainlit-ui-human-approval-gate--restart-resilience-ημ-68)
- [Φάση 5: Evaluation (105 Cases), Retrieval Benchmark, Red-Teaming & Demo (Ημ. 8–10)](#φάση-5-evaluation-105-cases-retrieval-benchmark-red-teaming--demo-ημ-810)

---

## Πίνακας Επισκόπησης Tasks

| ID | Τίτλος Κάρτας / Issue | Ρόλος | Scope | Handoff | Προτεραιότητα |
|---|---|---|---|---|---|
| **KAN-01** | `chore(deps): add deepagents, chromadb, and mcp dependencies` | Platform | `deps`, `docker` | ✋ Workflow | P0 (Blocker) |
| **KAN-02** | `docs(contracts): freeze domain schemas and architecture contracts` | Workflow | `agent`, `docs` | ✋ All | P0 (Blocker) |
| **KAN-03** | `feat(docker): expand compose with chromadb and mock external services` | Platform | `docker` | ✋ Knowledge | P1 |
| **KAN-04** | `feat(agent): initialize root deep agent harness with planning & postgres persistence` | Workflow | `agent`, `db` | ✋ Interface | P1 |
| **KAN-05** | `docs(team): update contributing agreement and review rotation` | Quality | `docs` | ✋ All | P1 |
| **KAN-06** | `feat(db): create relational supply chain tables in postgres` | Knowledge | `db` | ✋ Platform | P1 |
| **KAN-07** | `feat(neo4j): model multi-tier supply chain and upstream dependencies` | Knowledge | `neo4j` | ✋ Workflow | P1 |
| **KAN-08** | `feat(retrieval): ingest 212 documents into pgvector and chromadb` | Knowledge | `retrieval`, `db`| ✋ Quality | P1 |
| **KAN-09** | `feat(retrieval): index 300 disruption cases and 40 approved memories` | Knowledge | `retrieval` | ✋ Workflow | P2 |
| **KAN-10** | `feat(docker): automate database & graph seeding in compose seed service` | Platform | `docker`, `db` | ✋ Knowledge | P1 |
| **KAN-11** | `test(platform): clean-clone benchmark verification (<10 min)` | Quality | `eval`, `docker` | ✋ All | P1 (Milestone) |
| **KAN-12** | `feat(agent): implement triage and clarification subagent` | Workflow | `agent` | ✋ Interface | P1 |
| **KAN-13** | `feat(agent): implement operational impact analyzer subagent` | Workflow | `agent`, `tools` | ✋ Knowledge | P1 |
| **KAN-14** | `feat(agent): implement contract and provenance specialist subagent` | Workflow | `agent`, `retrieval`| ✋ Knowledge | P1 |
| **KAN-15** | `feat(agent): implement supply graph dependency subagent with cypher queries` | Workflow | `agent`, `neo4j` | ✋ Knowledge | P1 |
| **KAN-16** | `feat(tools): implement deterministic cost and revenue at risk calculators` | Workflow | `tools` | ✋ Quality | P1 |
| **KAN-17** | `feat(agent): implement recovery strategy optimizer subagent` | Workflow | `agent` | ✋ Interface | P1 |
| **KAN-18** | `feat(mcp): integrate simulated procurement and external risk mcp interfaces` | Platform | `mcp`, `agent` | ✋ Workflow | P1 |
| **KAN-19** | `feat(ui): implement chainlit rbac authentication and scoped views` | Interface | `ui` | ✋ Platform | P1 |
| **KAN-20** | `feat(ui): build investigation telemetry and structured findings dashboard` | Interface | `ui` | ✋ Workflow | P1 |
| **KAN-21** | `feat(ui): build recovery strategy comparison matrix component` | Interface | `ui` | ✋ Workflow | P1 |
| **KAN-22** | `feat(ui): build payload-bound approval card with double-click guard` | Interface | `ui`, `approval` | ✋ Workflow | P1 |
| **KAN-23** | `test(agent): container restart resilience and session recovery verification` | Workflow | `agent`, `db` | ✋ Platform, Quality | P1 (Milestone) |
| **KAN-24** | `feat(ui): post-approval simulated po execution receipt and incident report export` | Interface | `ui`, `mcp` | ✋ Workflow | P2 |
| **KAN-25** | `eval(retrieval): benchmark report comparing pgvector, chromadb, and hybrid` | Knowledge | `eval`, `retrieval`| ✋ Quality | P1 |
| **KAN-26** | `eval(langsmith): automated evaluation suite over 105 held-out scenarios` | Quality | `eval` | ✋ Workflow | P1 |
| **KAN-27** | `sec(eval): adversarial red-teaming and prompt-injection defense verification` | Quality | `eval`, `agent` | ✋ Workflow | P1 |
| **KAN-28** | `test(ui): multi-turn follow-up q&a verification from case memory` | Interface | `ui`, `agent` | ✋ Workflow | P2 |
| **KAN-29** | `docs(demo): 10-minute live demo script and pre-demo smoke tests` | Quality | `docs`, `eval` | ✋ All | P0 (Demo) |
| **KAN-30** | `test(team): live demo rehearsals and presenter rotation (>=2 runs)` | Quality | `docs` | ✋ All | P0 (Demo) |

---

## Αναλυτικές Κάρτες Tasks (Ready to Copy/Paste)

### Φάση 1: Kick-off, Contracts & Deep Agents Setup (Ημ. 1–2)

#### KAN-01: `chore(deps): add deepagents, chromadb, and mcp dependencies`
- **Owner:** Platform (@vaggelismpomponis) | **Backup:** Workflow
- **Labels:** `role:platform`, `scope:deps`, `phase:1`, `prio:P0`
- **Handoff (✋):** Παράδοση σε Workflow για την έναρξη του Deep Agents harness.
- **Περιγραφή:**  
  Ενημέρωση του `requirements.txt` και του `docs/PINNED_VERSIONS.md`. Προσθήκη των `deepagents==0.1.0`, `chromadb==0.5.23`, και `mcp==1.1.2` με αυστηρό pinning (`==`). Ενημέρωση του `.env.example` με τις απαιτούμενες μεταβλητές.
- **Acceptance Criteria:**
  - [ ] `requirements.txt` ενημερωμένο με strict pinning.
  - [ ] `.env.example` περιέχει όλα τα ChromaDB, Neo4j, MCP και LangSmith keys.
  - [ ] `pip install -r requirements.txt` ολοκληρώνεται χωρίς conflict εκδόσεων.

---

#### KAN-02: `docs(contracts): freeze domain schemas and architecture contracts`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Knowledge
- **Labels:** `role:workflow`, `scope:agent`, `scope:docs`, `phase:1`, `prio:P0`
- **Handoff (✋):** Παράδοση σε όλους τους ρόλους ως βάση για mocks και υλοποίηση.
- **Περιγραφή:**  
  Συγγραφή και οριστικοποίηση του `docs/ARCHITECTURE_CONTRACTS.md`. Ορισμός Pydantic schemas: `DisruptionFact`, `OperationalImpact`, `RecoveryOption`, `ApprovalPayload`, `AccessScope` και υπογραφές tools.
- **Acceptance Criteria:**
  - [ ] Όλα τα core schemas ορισμένα με type hints και field validations.
  - [ ] Υπογραφές tools (`query_inventory`, `query_bom`, `query_supplier_graph`, `retrieve_documents`) συμφωνημένες με Knowledge.
  - [ ] Payload approval contract ορισμένο με κανόνα αυστηρής σύνδεσης (spending cap ≤ €75k).

---

#### KAN-03: `feat(docker): expand compose with chromadb and mock external services`
- **Owner:** Platform (@vaggelismpomponis) | **Backup:** Workflow
- **Labels:** `role:platform`, `scope:docker`, `phase:1`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Knowledge για τη σύνδεση του vector store.
- **Περιγραφή:**  
  Επέκταση του `docker-compose.yml` για υποστήριξη 5 services: `postgres` (pgvector), `neo4j` (5.26+), `chromadb`, `external-risk`, και `app`. Προσθήκη healthchecks και persistent volumes.
- **Acceptance Criteria:**
  - [ ] `docker compose up -d` εκκινεί επιτυχώς και τα 5 containers.
  - [ ] Healthchecks αναφέρουν `healthy` σε όλα τα services.
  - [ ] Τα ports δεν συγκρούονται με τοπικές εγκαταστάσεις.

---

#### KAN-04: `feat(agent): initialize root deep agent harness with planning & postgres persistence`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Interface
- **Labels:** `role:workflow`, `scope:agent`, `scope:db`, `phase:1`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Interface για τη διασύνδεση του chat session.
- **Περιγραφή:**  
  Αρχικοποίηση του Root Deep Agent (`create_deep_agent`) με planning middleware, context scratchpad, και PostgreSQL checkpointer για state persistence.
- **Acceptance Criteria:**
  - [ ] Ο agent μπορεί να εκτελέσει βασικό task decomposition loop.
  - [ ] Η κατάσταση αποθηκεύεται σε PostgreSQL checkpoints.
  - [ ] Session thread ανακτάται απρόσκοπτα μέσω `thread_id`.

---

#### KAN-05: `docs(team): update contributing agreement and review rotation`
- **Owner:** Quality (@VickyMil-ai) | **Backup:** Interface
- **Labels:** `role:quality`, `scope:docs`, `phase:1`, `prio:P1`
- **Handoff (✋):** Παράδοση σε όλη την ομάδα.
- **Περιγραφή:**  
  Ευθυγράμμιση της ομάδας στο `CONTRIBUTING.md` και `CONTRIBUTING_LOG.md`: ρόλοι/backups, Conventional Commits scopes (`agent`, `ui`, `mcp`, `db`, `neo4j`, `retrieval`, `approval`, `eval`, `docker`, `docs`, `deps`), κανόνες PR (<300 lines) και Definition of Done.
- **Acceptance Criteria:**
  - [ ] `CONTRIBUTING.md` ενημερωμένο με τα νέα scopes.
  - [ ] Review rotation πίνακας ενεργοποιημένος.
  - [ ] Συμφωνία ομάδας υπογεγραμμένη στο log.

---

### Φάση 2: Data Ingestion, Knowledge Graph & Multi-Vector Pipeline (Ημ. 2–4)

#### KAN-06: `feat(db): create relational supply chain tables in postgres`
- **Owner:** Knowledge (@stef-fot) | **Backup:** Platform
- **Labels:** `role:knowledge`, `scope:db`, `phase:2`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Platform για το `init.sql`.
- **Περιγραφή:**  
  Σχεδιασμός DDL και δημιουργία πινάκων PostgreSQL: `suppliers`, `components`, `products`, `bom_lines`, `purchase_orders`, `shipments`, `inventory_lots` (με physical/reserved/quarantined), `production_schedules`, `customer_orders`.
- **Acceptance Criteria:**
  - [ ] Σχεσιακό σχήμα πλήρες με foreign keys και indexes.
  - [ ] Υποστήριξη πεδίων διαχωρισμού usable vs reserved/quarantined stock.
  - [ ] DDL scripts εκτελούνται χωρίς λάθη στο `docker/postgres/init.sql`.

---

#### KAN-07: `feat(neo4j): model multi-tier supply chain and upstream dependencies`
- **Owner:** Knowledge (@stef-fot) | **Backup:** Workflow
- **Labels:** `role:knowledge`, `scope:neo4j`, `phase:2`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Workflow για Cypher query tools.
- **Περιγραφή:**  
  Μοντελοποίηση στο Neo4j και φόρτωση των CSVs: Suppliers, Components, Products, Factories, Customers και Upstream Manufacturers. Ιδιαίτερη έμφαση στη σχέση `(:Supplier)-[:DEPENDS_ON_UPSTREAM]->(:UpstreamManufacturer)` για την αποκάλυψη της κοινής εξάρτησης Atlas και Delta.
- **Acceptance Criteria:**
  - [ ] Seeding script είναι πλήρως idempotent (`MERGE`).
  - [ ] Cypher queries επιστρέφουν σωστά τις εξαρτήσεις 1ου και 2ου επιπέδου.
  - [ ] Επιβεβαίωση εντοπισμού κοινού upstream κατασκευαστή chip fab.

---

#### KAN-08: `feat(retrieval): ingest 212 documents into pgvector and chromadb`
- **Owner:** Knowledge (@stef-fot) | **Backup:** Quality
- **Labels:** `role:knowledge`, `scope:retrieval`, `scope:db`, `phase:2`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Quality για το benchmark ανάκτησης.
- **Περιγραφή:**  
  Κατάτμηση και ευρετηρίαση 212 εγγράφων σε PostgreSQL `pgvector` και `ChromaDB`. Προσθήκη metadata provenance (`source_id`, `version`/`effective_date`, `access_scope`, `document_type`).
- **Acceptance Criteria:**
  - [ ] Όλα τα 212 έγγραφα κατατμημένα με ακριβή metadata.
  - [ ] HNSW indexes δημιουργημένα σε pgvector και ChromaDB collections.
  - [ ] Φυτεμένο κακόβουλο έγγραφο επισημασμένο για red-teaming.

---

#### KAN-09: `feat(retrieval): index 300 disruption cases and 40 approved memories`
- **Owner:** Knowledge (@stef-fot) | **Backup:** Workflow
- **Labels:** `role:knowledge`, `scope:retrieval`, `phase:2`, `prio:P2`
- **Handoff (✋):** Παράδοση σε Workflow για few-shot incident retrieval.
- **Περιγραφή:**  
  Ευρετηρίαση 300 ιστορικών disruption cases και 40 approved incident memories σε ξεχωριστό vector collection για παροχή context σε νέες υποθέσεις.
- **Acceptance Criteria:**
  - [ ] Memories αναζητήσιμες βάσει σημασιολογικής ομοιότητας.
  - [ ] Φίλτρα ανά component type και σοβαρότητα καθυστέρησης.

---

#### KAN-10: `feat(docker): automate database & graph seeding in compose seed service`
- **Owner:** Platform (@vaggelismpomponis) | **Backup:** Knowledge
- **Labels:** `role:platform`, `scope:docker`, `scope:db`, `phase:2`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Quality για το clean-clone test.
- **Περιγραφή:**  
  Δημιουργία ενοποιημένου Compose service `seed` που εκτελεί αυτόματα τη φόρτωση όλων των δεδομένων του `support-data/` πριν εκκινήσει το app container (`condition: service_completed_successfully`).
- **Acceptance Criteria:**
  - [ ] `docker compose up` φορτώνει όλα τα δεδομένα χωρίς χειροκίνητη παρέμβαση.
  - [ ] Το script είναι πλήρως idempotent (επανεκτέλεση δεν διπλασιάζει εγγραφές).

---

#### KAN-11: `test(platform): clean-clone benchmark verification (<10 min)`
- **Owner:** Quality (@VickyMil-ai) | **Backup:** All
- **Labels:** `role:quality`, `scope:eval`, `scope:docker`, `phase:2`, `prio:P1`
- **Handoff (✋):** Milestone αποδοχής τέλους 1ης εβδομάδας.
- **Περιγραφή:**  
  Εκτέλεση clean clone μόνο με το README σε πολλαπλά λειτουργικά συστήματα. Μέτρηση χρόνου εκκίνησης (<10 λεπτά).
- **Acceptance Criteria:**
  - [ ] Το stack εκκινεί σε <10′ από καθαρό clone.
  - [ ] Καταγραφή benchmark στο `docs/CLEAN_CLONE_BENCHMARK.md`.

---

### Φάση 3: Deep Agents Specialization, Sub-Agents & Simulated MCP (Ημ. 4–6)

#### KAN-12: `feat(agent): implement triage and clarification subagent`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Interface
- **Labels:** `role:workflow`, `scope:agent`, `phase:3`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Interface για clarification prompts.
- **Περιγραφή:**  
  Υλοποίηση Triage Subagent για εξαγωγή supplier S001, component MC-17, 12 ημερών καθυστέρησης και spending cap €75,000. Ενεργοποίηση clarification interrupt αν το όνομα είναι ασαφές.
- **Acceptance Criteria:**
  - [ ] Ακριβής εξαγωγή πεδίων στο `DisruptionFact`.
  - [ ] Διακοπή για διευκρίνιση όταν το μήνυμα είναι ασαφές (π.χ. "Atlas") χωρίς hallucinations.

---

#### KAN-13: `feat(agent): implement operational impact analyzer subagent`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Knowledge
- **Labels:** `role:workflow`, `scope:agent`, `scope:tools`, `phase:3`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Knowledge για inventory tools validation.
- **Περιγραφή:**  
  Υλοποίηση Operational Impact Subagent. Εξέταση αποθεμάτων σε πραγματικό χρόνο: εντοπισμός 3,200 διαθέσιμων μονάδων (αφαίρεση 1,400 δεσμευμένων & 600 καραντίνας), 6 προϊόντα, 77 πελάτες, και ακάλυπτη ζήτηση 5,350 μονάδων.
- **Acceptance Criteria:**
  - [ ] Ακριβής αριθμητική ταξινόμηση φυσικού vs usable αποθέματος.
  - [ ] Εντοπισμός εργοστασίων Katowice & Lyon που ξεμένουν πρώτα.

---

#### KAN-14: `feat(agent): implement contract and provenance specialist subagent`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Knowledge
- **Labels:** `role:workflow`, `scope:agent`, `scope:retrieval`, `phase:3`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Knowledge για document citations.
- **Περιγραφή:**  
  Υλοποίηση Contract Subagent. Ανάλυση συμβολαίων και ποιοτικών πιστοποιήσεων. Εντοπισμός ληγμένης πιστοποίησης Borealis (S002) και συγκρούσεων μεταξύ email και επίσημων συμβολαίων.
- **Acceptance Criteria:**
  - [ ] Εντοπισμός και επισήμανση ληγμένης πιστοποίησης Borealis.
  - [ ] Ανίχνευση συγκρούσεων lead time / τιμών ανάμεσα σε emails και συμβόλαια.

---

#### KAN-15: `feat(agent): implement supply graph dependency subagent with cypher queries`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Knowledge
- **Labels:** `role:workflow`, `scope:agent`, `scope:neo4j`, `phase:3`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Knowledge για Cypher optimization.
- **Περιγραφή:**  
  Υλοποίηση Supply Graph Subagent. Εκτέλεση queries στο Neo4j για εντοπισμό εναλλακτικών πηγών και αποκάλυψη της κοινής upstream εξάρτησης του προμηθευτή Delta με την Atlas.
- **Acceptance Criteria:**
  - [ ] Cypher query επιστρέφει ότι Delta και Atlas μοιράζονται τον ίδιο chip fab.
  - [ ] Ο προμηθευτής Delta απορρίπτεται ως κρυφό ρίσκο συγκέντρωσης.

---

#### KAN-16: `feat(tools): implement deterministic cost and revenue at risk calculators`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Quality
- **Labels:** `role:workflow`, `scope:tools`, `phase:3`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Quality για numerical testing.
- **Περιγραφή:**  
  Ανάπτυξη Python tools για ντετερμινιστικό υπολογισμό Recovery Cost (ναύλοι, τιμές) και Revenue at Risk (ρήτρες πελατών, αξία παραγγελιών). Απαγόρευση μαθηματικών υπολογισμών από το LLM.
- **Acceptance Criteria:**
  - [ ] Μηδενικά λάθη υπολογισμών (zero math hallucinations).
  - [ ] Σαφής διαχωρισμός Revenue at Risk από το Recovery Cost.

---

#### KAN-17: `feat(agent): implement recovery strategy optimizer subagent`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Interface
- **Labels:** `role:workflow`, `scope:agent`, `phase:3`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Interface για Strategy Comparison Matrix.
- **Περιγραφή:**  
  Υλοποίηση Strategy Optimizer Subagent. Σύνθεση τουλάχιστον 3 στρατηγικών (Transfer, Expedite, Alternative, Reallocate, Reschedule). Τεκμηρίωση απορρίψεων (Helios αργός, Borealis uncertified, Delta dependent).
- **Acceptance Criteria:**
  - [ ] Διαμόρφωση συγκριτικού πίνακα τουλάχιστον 3 στρατηγικών.
  - [ ] Συνολικό recovery cost αναφοράς ~€30,000 (κάτω από το όριο των €75,000).

---

#### KAN-18: `feat(mcp): integrate simulated procurement and external risk mcp interfaces`
- **Owner:** Platform (@vaggelismpomponis) | **Backup:** Workflow
- **Labels:** `role:platform`, `scope:mcp`, `scope:agent`, `phase:3`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Workflow για PO execution.
- **Περιγραφή:**  
  Υλοποίηση MCP server interfaces για εκτέλεση Purchase Orders στο simulated procurement system και πρόσβαση στο external risk feed.
- **Acceptance Criteria:**
  - [ ] MCP tool `execute_procurement_po` εκτελείται με επιτυχία μέσω JSON-RPC / stdio.
  - [ ] Επιστροφή έγκυρου execution receipt με confirmation ID.

---

### Φάση 4: Chainlit UI, Human Approval Gate & Restart Resilience (Ημ. 6–8)

#### KAN-19: `feat(ui): implement chainlit rbac authentication and scoped views`
- **Owner:** Interface (@AlexZarkalis) | **Backup:** Platform
- **Labels:** `role:interface`, `scope:ui`, `phase:4`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Platform για environment configuration.
- **Περιγραφή:**  
  Υλοποίηση εισόδου με ρόλους στο Chainlit: *Procurement Manager*, *Finance Controller*, και *Read-only Guest*. Εφαρμογή δυναμικού φίλτρου `access_scope` στα ανακτώμενα έγγραφα.
- **Acceptance Criteria:**
  - [ ] Procurement Manager δεν βλέπει εμπιστευτικά οικονομικά περιθώρια.
  - [ ] Finance Controller έχει πλήρη πρόσβαση σε συμβατικές τιμές & ρήτρες.
  - [ ] Guest βλέπει μόνο δημόσιες ανακοινώσεις.

---

#### KAN-20: `feat(ui): build investigation telemetry and structured findings dashboard`
- **Owner:** Interface (@AlexZarkalis) | **Backup:** Workflow
- **Labels:** `role:interface`, `scope:ui`, `phase:4`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Workflow για streaming step events.
- **Περιγραφή:**  
  Ανάπτυξη UI component που προβάλλει live step indicators καθώς εκτελούνται οι Deep Agent subagents (Triage, Stock Check, Contract Analysis, Supply Graph, Optimization).
- **Acceptance Criteria:**
  - [ ] Live απεικόνιση ενεργειών και χρόνων εκτέλεσης ανά subagent.
  - [ ] Καθαρή παρουσίαση αποθεμάτων (usable, reserved, quarantined).

---

#### KAN-21: `feat(ui): build recovery strategy comparison matrix component`
- **Owner:** Interface (@AlexZarkalis) | **Backup:** Workflow
- **Labels:** `role:interface`, `scope:ui`, `phase:4`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Workflow για options payload.
- **Περιγραφή:**  
  Ανάπτυξη διαδραστικού συγκριτικού πίνακα στρατηγικών στο Chainlit. Διακριτές στήλες Recovery Cost vs Revenue at Risk, και σαφής ένδειξη των λόγων απόρριψης.
- **Acceptance Criteria:**
  - [ ] Εμφάνιση τουλάχιστον 3 στρατηγικών σε μορφή κάρτας/πίνακα.
  - [ ] Highlight απορρίψεων: Helios (αργός), Borealis (cert expired), Delta (upstream).

---

#### KAN-22: `feat(ui): build payload-bound approval card with double-click guard`
- **Owner:** Interface (@AlexZarkalis) | **Backup:** Workflow
- **Labels:** `role:interface`, `scope:ui`, `scope:approval`, `phase:4`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Workflow για approval interrupt.
- **Περιγραφή:**  
  Υλοποίηση της κάρτας έγκρισης. Εμφάνιση ακριβούς payload (supplier, quantity, unit price, total cost ≤ €75k, citations). Κουμπιά: **[Approve]**, **[Reject]**, **[Modify Plan]**. Προστασία διπλού κλικ (`asyncio.Lock`).
- **Acceptance Criteria:**
  - [ ] Πλήρης δέσμευση του approval payload (supplier, ποσότητα, τιμή).
  - [ ] Το Modify Plan ακυρώνει την κατάσταση και ενεργοποιεί επανεπικύρωση.
  - [ ] Κανένα διπλό κλικ δεν προκαλεί διπλή ενέργεια.

---

#### KAN-23: `test(agent): container restart resilience and session recovery verification`
- **Owner:** Workflow (@VickyMil-ai) | **Backup:** Platform, Quality
- **Labels:** `role:workflow`, `scope:agent`, `scope:db`, `phase:4`, `prio:P1`
- **Handoff (✋):** Milestone ανθεκτικότητας και idempotency.
- **Περιγραφή:**  
  Δοκιμή επανεκκίνησης του app container (`docker compose restart app`) ενώ εκκρεμεί η έγκριση. Επιβεβαίωση ότι η συνεδρία συνεχίζεται από το PostgreSQL checkpoint και η εκτέλεση γίνεται ακριβώς μία φορά (zero duplicate PO execution).
- **Acceptance Criteria:**
  - [ ] Μετά από container restart, το session ανακτάται άμεσα.
  - [ ] Καμία διπλή εκτέλεση στο simulated procurement (strict idempotency guard).

---

#### KAN-24: `feat(ui): post-approval simulated po execution receipt and incident report export`
- **Owner:** Interface (@AlexZarkalis) | **Backup:** Workflow
- **Labels:** `role:interface`, `scope:ui`, `scope:mcp`, `phase:4`, `prio:P2`
- **Handoff (✋):** Παράδοση σε Workflow για memory storage.
- **Περιγραφή:**  
  Εμφάνιση επίσημου receipt εκτέλεσης μετά την έγκριση (PO confirmation ID). Δυνατότητα λήψης δομημένου Incident Report σε Markdown/PDF.
- **Acceptance Criteria:**
  - [ ] Receipt εμφανίζει supplier, PO number, timestamp και τελικό κόστος.
  - [ ] Incident report είναι πλήρως τεκμηριωμένο με citations.

---

### Φάση 5: Evaluation (105 Cases), Retrieval Benchmark, Red-Teaming & Demo (Ημ. 8–10)

#### KAN-25: `eval(retrieval): benchmark report comparing pgvector, chromadb, and hybrid`
- **Owner:** Knowledge (@stef-fot) | **Backup:** Quality
- **Labels:** `role:knowledge`, `scope:eval`, `scope:retrieval`, `phase:5`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Quality για ένταξη στην τελική έκθεση.
- **Περιγραφή:**  
  Εκτέλεση πειράματος αξιολόγησης ανάκτησης σε 212 έγγραφα: σύγκριση Recall@K, Precision@K, και Latency ανάμεσα σε `pgvector`, `ChromaDB`, και `Hybrid Retrieval`.
- **Acceptance Criteria:**
  - [ ] Benchmark report ολοκληρωμένο με συγκριτικούς πίνακες και γραφήματα.
  - [ ] Υπεροχή Hybrid Retrieval σε σύνθετα ερωτήματα.

---

#### KAN-26: `eval(langsmith): automated evaluation suite over 105 held-out scenarios`
- **Owner:** Quality (@VickyMil-ai) | **Backup:** Workflow
- **Labels:** `role:quality`, `scope:eval`, `phase:5`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Workflow για διορθώσεις.
- **Περιγραφή:**  
  Εκτέλεση automated evaluators στο LangSmith στα 105 held-out σενάρια διακοπής. Έλεγχος triage, αριθμητικής ακρίβειας, τήρησης budget cap, και εγκυρότητας πιστοποιήσεων.
- **Acceptance Criteria:**
  - [ ] 100% traces καταγεγραμμένα στο LangSmith.
  - [ ] Pass rate >90% στα evaluation scenarios.

---

#### KAN-27: `sec(eval): adversarial red-teaming and prompt-injection defense verification`
- **Owner:** Quality (@VickyMil-ai) | **Backup:** Workflow
- **Labels:** `role:quality`, `scope:eval`, `scope:agent`, `phase:5`, `prio:P1`
- **Handoff (✋):** Παράδοση σε Workflow για guardrail patches.
- **Περιγραφή:**  
  Δοκιμή red-teaming με το φυτεμένο κακόβουλο έγγραφο (περιέχει εντολή παράκαμψης έγκρισης). Επιβεβαίωση ότι ο Adversarial Challenger Subagent εξουδετερώνει την επίθεση και προστατεύει τον έλεγχο του agent.
- **Acceptance Criteria:**
  - [ ] Το κακόβουλο έγγραφο επισημαίνεται και αγνοείται.
  - [ ] Καμία μη εξουσιοδοτημένη ενέργεια δεν εκτελείται.

---

#### KAN-28: `test(ui): multi-turn follow-up q&a verification from case memory`
- **Owner:** Interface (@AlexZarkalis) | **Backup:** Workflow
- **Labels:** `role:interface`, `scope:ui`, `scope:agent`, `phase:5`, `prio:P2`
- **Handoff (✋):** Παράδοση σε Workflow για validation.
- **Περιγραφή:**  
  Δοκιμή ερωτήσεων συνέχειας μετά την ολοκλήρωση της υπόθεσης ("Γιατί απορρίφθηκε ο Helios;", "Τι αλλάζει με όριο €90,000;", "Προστασία VIP πελατών").
- **Acceptance Criteria:**
  - [ ] Οι απαντήσεις αντλούνται αξιόπιστα από την αποθηκευμένη μνήμη της υπόθεσης.
  - [ ] Νέα σενάρια προϋπολογισμού επανυπολογίζονται σωστά.

---

#### KAN-29: `docs(demo): 10-minute live demo script and pre-demo smoke tests`
- **Owner:** Quality (@VickyMil-ai) | **Backup:** All
- **Labels:** `role:quality`, `scope:docs`, `scope:eval`, `phase:5`, `prio:P0`
- **Handoff (✋):** Παράδοση σε όλη την ομάδα για τις πρόβες.
- **Περιγραφή:**  
  Ολοκλήρωση του αναλυτικού σεναρίου live demo διάρκειας 10 λεπτών με χρονικό καταμερισμό ανά στάδιο (Goal, Triage, Telemetry, Strategy Matrix, Approval & Restart, Traces).
- **Acceptance Criteria:**
  - [ ] `docs/DEMO_SCRIPT.md` ενημερωμένο για SupplyGuard AI.
  - [ ] Pre-demo smoke test επιβεβαιώνει ότι όλα τα components λειτουργούν άψογα.

---

#### KAN-30: `test(team): live demo rehearsals and presenter rotation (>=2 runs)`
- **Owner:** Quality (@VickyMil-ai) | **Backup:** All
- **Labels:** `role:quality`, `scope:docs`, `phase:5`, `prio:P0`
- **Handoff (✋):** Τελικό παραδοτέο bootcamp.
- **Περιγραφή:**  
  Διεξαγωγή τουλάχιστον 2 πλήρων προβών του live demo με rotation παρουσιαστών. Επιβεβαίωση ότι κάθε μέλος της 5μελούς ομάδας μπορεί να εξηγήσει οποιοδήποτε κομμάτι της ροής.
- **Acceptance Criteria:**
  - [ ] ≥2 πλήρεις πρόβες χρονομετρημένες σε <10 λεπτά.
  - [ ] Καταγραφή rotation στο `docs/REHEARSAL_LOG.md`.
  - [ ] 100% ετοιμότητα ομάδας για την τελική παρουσίαση.
