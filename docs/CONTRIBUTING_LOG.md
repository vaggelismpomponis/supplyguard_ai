# CONTRIBUTING Log

Τρέχον αρχείο αποφάσεων για το `CONTRIBUTING.md` (team agreement). Ο Quality το συντηρεί και περνά τις **Αποφασισμένες** εγγραφές στο `CONTRIBUTING.md`. Όταν το `CONTRIBUTING.md` γίνει final, το log μένει ως ιστορικό.

## Πώς το γεμίζουμε

1. Κάθε απόφαση ή αλλαγή κανόνα γίνεται **νέα γραμμή** στο [Log αποφάσεων](#log-αποφάσεων) την ίδια μέρα (πιο πρόσφατη στο τέλος).
2. Αν αφορά ένα θέμα του [Πίνακα θεμάτων](#πίνακας-θεμάτων-για-το-contributingmd), ενημερώνεται και η γραμμή του (status, απόφαση).
3. Κάθε γραμμή έχει πηγή: συνάντηση, PR ή issue.
4. Το log αλλάζει μέσω PR με prefix `docs(...)`, όπως κάθε αρχείο.

## Πίνακας θεμάτων για το CONTRIBUTING.md

Status: `Proposed` (προτάθηκε) · `Decided` (συμφωνήθηκε) · `In CONTRIBUTING` (έχει περαστεί).

| # | Θέμα | Απόφαση / Πρόταση | Status | Πηγή |
|---|---|---|---|---|
| 1 | Branch strategy | `main` (release) και `develop` (integration), προστατευμένα. Feature branches `feature/`, `bugfix/`, `hotfix/`, `docs/` από `develop`. | Proposed | [AGENTS.md](../AGENTS.md), [GIT_GUIDE](./GIT_GUIDE.md) |
| 2 | Κανόνας PR | PR → `develop`, ≥1 reviewer, όχι self-merge, <300 γραμμές, review <24 ώρες. | Proposed | [README](../README.md#working-agreements) |
| 3 | Merge method | Squash στο `develop`. Merge commit για release `develop` → `main`. | Proposed | [AGENTS.md](../AGENTS.md) |
| 4 | Commit convention | Conventional Commits 1.0.0, scopes SupplyGuard: `agent`, `approval`, `ui`, `mcp`, `retrieval`, `neo4j`, `db`, `eval`, `tests`, `docker`, `docs`, `deps`. | Proposed | [roles/README.md](./roles/README.md), Issue #81 |
| 5 | Κανάλι επικοινωνίας | _TBD_ | Open | |
| 6 | Daily stand-up | 10–15′, ασύγχρονο αποδεκτό. Ώρα/κανάλι: _TBD_ | Open | [README](../README.md#working-agreements) |
| 7 | Ρόλοι και backups | Quality: @VickyMil-ai. Υπόλοιποι primary owners: _TBD_. Προτεινόμενα backups: Platform→Workflow, Interface→Quality, Workflow→Knowledge, Knowledge→Platform, Quality→Interface. | Open | [`roles/`](./roles/README.md), Issue #79 |
| 8 | Review rotation | Platform→Workflow→Knowledge→Interface→Quality→Platform (πίνακας στο `CONTRIBUTING.md`). | Proposed | [`roles/README.md`](./roles/README.md#rotation-reviews-προτεινόμενο), Issue #81 |
| 9 | Definition of Done | Task: merged PR με tests, review, τικαρισμένο role checklist και sign-off για ✋. Project: τα 12 κριτήρια στο [`PROJECT_CHECKLIST.md`](./PROJECT_CHECKLIST.md#6-definition-of-done). | Proposed | Issue #81 |
| 10 | Code conventions | Python με type hints, Pydantic, Deep Agents με μικρούς subagents/tools, deterministic calculators (όχι LLM arithmetic), Revenue at Risk χωριστά από Recovery Cost, payload-bound approval ≤ €75k, idempotency, provenance σε κάθε chunk, untrusted document content, χωρίς hardcoded credentials. | Proposed | [roles/README.md](./roles/README.md), Issue #81 |
| 11 | Contracts | State (`AgentState`), Pydantic models (`ExtractedFields`, `PolicyResult`, `GraphResult`, `ActionProposal`), 5 actions (`ActionType`), status (`pending`, `approved`, `executed`, `rejected`), tool signatures (`retrieve_policy`, `check_graph`), κανόνας `thread_id` ↔ Chainlit session. | Decided | [ARCHITECTURE_CONTRACTS.md](./ARCHITECTURE_CONTRACTS.md), [`src/agent/schemas.py`](../src/agent/schemas.py), Issue #2 |
| 12 | Pair/mob sessions | Μία στη μέση κάθε εβδομάδας. Ημέρα/ώρα: _TBD_ | Open | |
| 13 | Dependencies & Pinned Versions Policy | Αυστηρό pinning με `==` στο `requirements.txt` και immutable tags στα Docker base images (`python:3.11-slim`, `pgvector/pgvector:pg16`, `neo4j:5.26.0`). Καμία χρήση `:latest` ή `>=`. Αναφορά στο PR και commit scope `deps`. | Decided | [PINNED_VERSIONS.md](./PINNED_VERSIONS.md), Issue #2 |
| 14 | Secrets | Κανένα credential στο repo, `.env` εκτός version control. | Proposed | [AGENTS.md](../AGENTS.md) |
| 15 | Repo Structure & Module Boundaries | Δομή: `src/` (`src/agent/` [Workflow], `src/ui/` [Interface], `src/db/` [Platform], `src/core/` [Platform]), `docker/` (`docker/postgres/init.sql` [Platform]), `scripts/` (`ingest_policies.py`, `seed_neo4j.py` [Knowledge]), `data/` (`policies/`, `eval_dataset.json`, `graph_seed.json` [Knowledge/Quality]), `tests/` & `evals/` [Quality], `docs/` [All/Quality]. Σαφή όρια χωρίς τροποποίηση κοινών αρχείων. | Decided | [COLLABORATION_GUIDE.md](./COLLABORATION_GUIDE.md), [roles/README.md](./roles/README.md), Issue #2 |
| 16 | Docker Base Images & Runtime Pinning | `python:3.11-slim` (app service), `pgvector/pgvector:pg16` (Postgres + pgvector), `neo4j:5.26.0` (Neo4j). Όλα τα services εκκινούν σε <10′ σε καθαρό clone. | Decided | [PINNED_VERSIONS.md](./PINNED_VERSIONS.md), Issue #2 |
| 17 | Handoffs (✋) | Τα βήματα με ✋ θεωρούνται ολοκληρωμένα μόνο μετά από αποδοχή του παραλήπτη ρόλου, καταγεγραμμένη ως sign-off πίνακας σε αυτό το log. | Proposed | [roles/README.md](./roles/README.md), Issue #81 |
| 18 | Zero-conflict check πριν από PR | `git fetch origin` και `git merge-tree --write-tree HEAD origin/develop` (`origin/main` για release) πριν ανοίξει PR. | Proposed | [AGENTS.md](../AGENTS.md), Issue #81 |

## Log αποφάσεων

Οι εγγραφές πριν από τις 2026-11-24 αφορούν το warm-up project (HelpDesk Lite) και μένουν ως ιστορικό.

Μορφή: `Ημερομηνία | Ρόλος | Τι αποφασίστηκε / άλλαξε | Γιατί | Πηγή`

| Ημερομηνία | Ρόλος | Απόφαση / Αλλαγή | Γιατί | Πηγή |
|---|---|---|---|---|
| 2026-11-11 | Quality | Δημιουργία role map, project checklist και αυτού του log | Να παρακολουθούμε την πρόοδο και να έχουμε υλικό για το `CONTRIBUTING.md` | _PR TBD_ |
| 2026-11-16 | Platform | Day 1 Kick-off: Συμφωνία αρχιτεκτονικών συμβολαίων (State, Pydantic models, 5 actions, tool signatures, κανόνας `thread_id` ↔ session), επίσημη δομή repository (`src/`, `docker/`, `scripts/`, `data/`, `tests/`, `evals/`, `docs/`) με σαφή module boundaries, και πολιτική pinned versions για Docker images και Python dependencies (`requirements.txt`). | Διασφάλιση κοινής βάσης, ανεξάρτητη παράλληλη ανάπτυξη με mocks χωρίς merge conflicts, και εγγύηση εκκίνησης stack σε <10′ σε όλα τα λειτουργικά συστήματα (Windows/Linux/macOS). | Issue #2, [ARCHITECTURE_CONTRACTS.md](./ARCHITECTURE_CONTRACTS.md), [PINNED_VERSIONS.md](./PINNED_VERSIONS.md), [COLLABORATION_GUIDE.md](./COLLABORATION_GUIDE.md) |
| 2026-11-17 | Platform | PostgreSQL Schema Init & Upgrade Migration: Ενεργοποίηση `pgvector` extension, πίνακας `tickets` για state-changing ticketing, πίνακας `audit_log` για idempotency tracking και audit trail, πίνακας `policy_chunks` με HNSW index (`embedding vector(1536)`) για το Knowledge retrieval, επίσημοι πίνακες LangGraph `PostgresSaver` (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) για state persistence και seamless resume μετά από container restart, και non-destructive upgrade migration (`001_upgrade_schema.sql`) με safe column addition και data backfill για υφιστάμενα Docker volumes. | Υλοποίηση Issue #5, αποτροπή duplicate executions (idempotency guard), ασφαλής αναβάθμιση υφιστάμενων compose volumes χωρίς απώλεια δεδομένων, και πλήρης ετοιμότητα βάσης για Workflow και Knowledge roles. | Issue #5, [`docker/postgres/init.sql`](../docker/postgres/init.sql), [`docker/postgres/migrations/001_upgrade_schema.sql`](../docker/postgres/migrations/001_upgrade_schema.sql) |
| 2026-11-17 | Platform | Multi-stage Dockerfile (python:3.11-slim) για το Chainlit app, integration στο docker-compose.yml με helpdesk_network, healthchecks και volume mounts, starter src/app.py με session mapping (thread_id), και επαληθευμένες οδηγίες εκκίνησης στο README.md. Handoff και συμφωνία με Interface role (✋). | Ολοκλήρωση Phase 2 (Steps 7–8) του Platform role, εξασφάλιση one-command startup (docker compose up) σε <10′. | Issue #6, PR #68 |
| 2026-11-18 | Platform | Day 5 Milestone Clean-Clone Test & Startup Benchmark (<10′): Επιτυχής εκτέλεση clean clone μόνο με το README σε ≥3 laptops (Windows 11, macOS M2, Ubuntu 22.04 LTS) με μέσο χρόνο εκκίνησης ~2–3′ (<10′). Προσθήκη `.gitattributes` για LF line endings, διασταυρούμενες οδηγίες cp/Copy-Item/copy στο README.md, παραμετροποίηση ports Neo4j στο docker-compose.yml και οδηγίες αντιμετώπισης προβλημάτων (troubleshooting). ✋ Συντονισμός με Quality (@VickyMil-ai). | Επίτευξη του κρίσιμου milestone τέλους 1ης εβδομάδας, απρόσκοπτη εκκίνηση του stack από όλα τα μέλη της ομάδας χωρίς friction. | Issue #7, [CLEAN_CLONE_BENCHMARK.md](./CLEAN_CLONE_BENCHMARK.md) |
| 2026-11-18 | Platform | Days 6–10 Completion: Automated Ingestion & Seeding in Compose. Προσθήκη service 'seed' στο docker-compose.yml και unified script 'scripts/seed.py' με αυτόματη εκτέλεση και dependency 'service_completed_successfully' πριν το 'app'. Εξασφάλιση πλήρους idempotency (DELETE per version στο pgvector, MERGE στο Neo4j), ευθυγράμμιση schema policy_chunks και εκμηδένιση χειροκίνητων βημάτων. ✋ Συνεργασία με Knowledge (@stef-fot). | Πλήρωση του Definition of Done: τα ingestion και seeding scripts τρέχουν αυτόματα χωρίς χειροκίνητη παρέμβαση, διασφαλίζοντας έτοιμες βάσεις δεδομένων αμέσως μετά το 'docker compose up'. | Issue #8, [roles/platform.md](./roles/platform.md), [roles/knowledge.md](./roles/knowledge.md) |
| 2026-11-18 | Platform | Days 6–10 Completion: Container Restart Support for Idempotency Test. Προσθήκη stop_grace_period (15s) στο service 'app' για ασφαλή ολοκλήρωση in-flight checkpoint writes, module src/db/ με PostgresSaver για LangGraph state persistence σε PostgreSQL (πίνακες checkpoints, checkpoint_blobs, checkpoint_writes), IdempotencyGuard (audit_log με row-level locking) και idempotent ticket creation. Επιβεβαίωση persistence σε Postgres και Neo4j σε restart app και down/up, και νέα αυτοματοποιημένη σουίτα tests/test_restart_idempotency.py. ✋ Συνεργασία με Workflow (@VickyMil-ai) και Quality (@VickyMil-ai). | Διασφάλιση ακεραιότητας κατάστασης μετά από restart container, αποτροπή διπλής εκτέλεσης (idempotency guard), και εκπλήρωση κριτηρίου Definition of Done για το 10′ demo. | Issue #9, [roles/platform.md](./roles/platform.md), [roles/workflow.md](./roles/workflow.md), [roles/quality.md](./roles/quality.md) |
| 2026-11-18 | Platform | Days 6–10 Completion: Final README Polish & Pre-Demo Clean-Clone Verification. Ολοκλήρωση τελικού polish στο README.md με λεπτομερείς οδηγίες εκκίνησης για όλα τα OS, προσθήκη ολοκληρωμένου οδηγού διεξαγωγής του 10λεπτου live demo ανά στάδιο ροής (clarification, policy citations, dependency outages, approval interrupt, app container restart & resume, LangSmith tracing), ενότητα automated testing suite, troubleshooting με fallback embeddings και JVM warmup. Επιτυχής εκτέλεση τελικής πρόβας clean clone (<3 λεπτά) σε όλα τα περιβάλλοντα (Windows/macOS/Linux) με πλήρη επιβεβαίωση Definition of Done. ✋ Συντονισμός με Quality (@VickyMil-ai), Interface (@AlexZarkalis) και Knowledge (@stef-fot). | Πλήρωση κριτηρίων Issue #10 και ολοκλήρωση όλων των παραδοτέων του Platform role (Steps 13–14) ενόψει της τελικής παρουσίασης. | Issue #10, [README.md](../README.md), [CLEAN_CLONE_BENCHMARK.md](./CLEAN_CLONE_BENCHMARK.md), [roles/platform.md](./roles/platform.md) |
| 2026-11-18 | Workflow | Days 2–4 Skeleton: Field Extraction Node with 'Ask if Missing' Rule. Υλοποίηση κόμβου 'extract_fields' με Pydantic schema 'ExtractedFields' (optional fields: employee, application, symptom, urgency) και μεθόδους 'missing_fields()' & 'is_complete()'. Αυστηρή επιβολή κανόνα 'αν λείπει, ρώτα': οποιοδήποτε ελλιπές υποχρεωτικό πεδίο οδηγεί σε clarification interrupt χωρίς εικασίες (never guess). Εξαγωγή employee από session email ή κείμενο, symptom validation και urgency detection. Νέα σουίτα ελέγχων στο tests/test_graph.py. ✋ Συνεργασία με Interface (@AlexZarkalis) και Quality (@VickyMil-ai). | Υλοποίηση Issue #25, αποτροπή hallucination/guessing ελλιπών στοιχείων και διασφάλιση πλήρους triage πριν από policy/graph lookup. | Issue #25, [roles/workflow.md](./roles/workflow.md), [ARCHITECTURE_CONTRACTS.md](./ARCHITECTURE_CONTRACTS.md) |
| 2026-11-18 | Workflow | Days 2–4 Skeleton: Interrupt Nodes & PostgresSaver Integration. Υλοποίηση interrupt nodes (`ask_clarification` interrupt_after, `human_approval` interrupt_before), σύνδεση `build_graph` με `PostgresSaver` (`use_postgres=True`) για ανθεκτική αποθήκευση κατάστασης στους πίνακες `checkpoints` και `checkpoint_blobs`, και απρόσκοπτη συνέχιση της ροής μετά από restart διεργασίας μέσω των μεθόδων `reply()` και `decide()`. ✋ Συντονισμός με Platform (@vaggelismpomponis) για το database schema. | Διασφάλιση ανθεκτικότητας γραφήματος σε διακοπές και restarts, συμμόρφωση με τους κανόνες human-in-the-loop για clarification και approval, και εκπλήρωση acceptance criteria του Issue #26. | Issue #26, [roles/workflow.md](./roles/workflow.md), [roles/platform.md](./roles/platform.md) |
| 2026-11-18 | Workflow | Day 5 Milestone: End-to-End Mock Workflow inside Docker Compose. Επαλήθευση πλήρους εκτέλεσης του LangGraph workflow με mock nodes εντός του Docker Compose stack (helpdesk_app, helpdesk_postgres, helpdesk_neo4j) σε όλα τα 10 σενάρια του eval dataset και σε όλες τις conditional διακλαδώσεις (clarification, approval, rejection, policy citation, outage detection, escalation, idempotency replay) χωρίς unhandled exceptions. Νέα σουίτα tests/test_workflow_compose_milestone.py. ✋ Συντονισμός με Quality (@VickyMil-ai) και Platform (@vaggelismpomponis). | Επίτευξη του κρίσιμου οροσήμου της 1ης εβδομάδας (Milestone Day 5 - Step 7), διασφάλιση πλήρους σταθερότητας ροής πριν την αντικατάσταση των mocks με πραγματικά tools, και εκπλήρωση κριτηρίων Issue #27. | Issue #27, [roles/workflow.md](./roles/workflow.md), [PROJECT_CHECKLIST.md](./PROJECT_CHECKLIST.md) |
| 2026-11-18 | Interface | Υλοποίηση πλήρους Chainlit UI στο `src/app.py`, οδηγός χρήσης στο `chainlit.md` και unit tests στο `tests/test_ui.py`: 1:1 αντιστοίχιση `cl.context.session.id` ↔ `thread_id` (με `/resume <thread_id>` για ανάκτηση μετά από restart), progress steps ανά node (`cl.Step` για `extract_fields`, `retrieve_policy`, `check_graph`, `decide_action`, `human_approval`, `execute_action`, `respond`), clarification interrupt & resume, κάρτα approval με `action_id`, παραμέτρους, policy/outage context και κουμπιά Approve/Reject, αποτροπή διπλού κλικ (`asyncio.Lock` & αφαίρεση κουμπιών), citations (`source`, `doc_id`, `effective_date`) στην τελική απάντηση και graceful error handling. | Ολοκλήρωση παραδοτέων του Interface role, πλήρης συμμόρφωση με τα Day 1 contracts και ασφαλής human-in-the-loop αλληλεπίδραση χωρίς διπλές εκτελέσεις. | Issue #11, Issue #12, Issue #13, Issue #14, Issue #15, Issue #16, Issue #17, [`src/app.py`](../src/app.py), [`chainlit.md`](../chainlit.md), [`tests/test_ui.py`](../tests/test_ui.py), [roles/interface.md](./roles/interface.md) |
| 2026-11-18 | Workflow | Days 6–10 Completion: Replace Mocks with Real Tools. Πλήρης αποδέσμευση και απόσυρση των mocks (mocks decommissioned) από τον γράφο και ενσωμάτωση των πραγματικών Knowledge tools (`src.knowledge.tools.retrieve_policy` με semantic search σε pgvector και κανόνα latest effective date, `src.knowledge.tools.check_graph` με live Cypher queries στο Neo4j για dependencies & outages). Αυτόνομη επίλυση οντοτήτων triage (`find_application`, `find_employee`) και επιτυχής επικύρωση όλων των καταστάσεων και conditional edges με live queries. ✋ Συνεργασία με Knowledge (@stef-fot). | Πλήρωση των acceptance criteria του Issue #28 (Step 8), σύνδεση των παραγωγικών βάσεων PostgreSQL/pgvector και Neo4j με τον LangGraph workflow, και διασφάλιση 100% λειτουργικότητας σε live data. | Issue #28, [roles/workflow.md](./roles/workflow.md), [roles/knowledge.md](./roles/knowledge.md) |
| 2026-11-19 | Workflow | Days 6–10 Completion: Decision Rules (Active Outage -> Link to Outage). Υλοποίηση επιχειρησιακής λογικής στο `decide_action` και αξιολόγηση δέντρου εξαρτήσεων υπηρεσιών (`check_graph`). Αυστηρή επιβολή του κανόνα υπερίσχυσης outage: όταν εξαρτώμενη υπηρεσία παρουσιάζει ενεργό outage (π.χ. Identity Provider SSO -> Corporate VPN, Finance Portal, GitHub Enterprise), ο assistant προτείνει υποχρεωτικά `link_outage` (χωρίς απαίτηση έγκρισης) και αναστέλλει/απαγορεύει αυστηρά το credential reset (`reset_credentials`), ακόμη και όταν ο χρήστης ζητά ρητά επαναφορά κωδικού. Εμπλουτισμός παραμέτρων `ActionProposal` με `outage_id` και `active_outages`, και 5 νέες δοκιμές επικύρωσης στο `tests/test_graph.py`. ✋ Συντονισμός με Knowledge (@stef-fot) και Quality (@VickyMil-ai). | Πλήρωση των acceptance criteria του Issue #29 (Step 9), προστασία από εσφαλμένες αλλαγές διαπιστευτηρίων κατά τη διάρκεια περιστατικών υποδομής, και διασφάλιση 100% επιτυχίας στα σχετικά evaluators. | Issue #29, [roles/workflow.md](./roles/workflow.md), [ARCHITECTURE_CONTRACTS.md](./ARCHITECTURE_CONTRACTS.md) |
| 2026-11-19 | Workflow | Days 6–10 Completion: Idempotent Action Execution & Status Tracking. Σύνδεση των κόμβων `decide_action`, `human_approval` και `execute_action` με το PostgreSQL `audit_log` (`src.db.idempotency`), ατομικές ενημερώσεις κύκλου ζωής ενεργειών (`pending` -> `approved`/`rejected` -> `executed`) και αυστηρός προ-εκτελεστικός έλεγχος (pre-execution idempotency guard). Ενσωμάτωση πραγματικής δημιουργίας ticket (`create_ticket_idempotent`) στον πίνακα `tickets` με προστασία από duplicate inserts (`ON CONFLICT (action_id) DO NOTHING`). Πλήρης αποτροπή διπλής εκτέλεσης ή lifecycle regressions σε επανεκκινήσεις container, process crashes και network replays. 4 νέες δοκιμές επικύρωσης στο `tests/test_graph.py` και 10/10 επιτυχία στα evaluators. ✋ Συντονισμός με Platform (@vaggelismpomponis), Interface (@AlexZarkalis) και Quality (@VickyMil-ai). | Πλήρωση των acceptance criteria του Issue #30 (Step 10), κατοχύρωση της απαίτησης ότι καμία ενέργεια δεν εκτελείται δύο φορές, και εκπλήρωση του οροσήμου end-to-end με approval και resume. | Issue #30, [roles/workflow.md](./roles/workflow.md), [ARCHITECTURE_CONTRACTS.md](./ARCHITECTURE_CONTRACTS.md) |
| 2026-11-19 | Workflow | Days 6–10 Completion: Restart Test Verification (Zero Duplicate Execution). Επιτυχής εκτέλεση και επαλήθευση του σεναρίου επανεκκίνησης (Restart Test Scenario): ενέργεια που απαιτεί έγκριση επιβιώνει από διαδοχικές επανεκκινήσεις του app container/διεργασίας, διατηρεί την αναμονή έγκρισης και την κατάσταση στο `PostgresSaver` και `audit_log`, και εκτελείται ακριβώς μία φορά χωρίς διπλή εκτέλεση (zero duplicate execution). Ενσωμάτωση προστασίας (guard) στη συνάρτηση `decide()` ώστε να αποτρέπεται οποιαδήποτε υποστροφή κατάστασης (`executed` -> `approved`) σε επαναλαμβανόμενες κλήσεις ή replays σε ολοκληρωμένα threads. ✋ Συντονισμός και κοινή υπογραφή (Team Sign-off) με Quality (@VickyMil-ai) και Platform (@vaggelismpomponis). | Πλήρωση των acceptance criteria του Issue #31 (Step 11), επιβεβαίωση της ανθεκτικότητας του workflow σε αστοχίες διεργασίας/container και διασφάλιση 100% ακεραιότητας κατάστασης. | Issue #31, [roles/workflow.md](./roles/workflow.md), [RESTART_TEST_SCENARIO.md](./RESTART_TEST_SCENARIO.md) |
| 2026-11-19 | Workflow | Days 6–10 Completion: LangSmith Tracing Metadata & Evaluation Run Fixes. Προσθήκη tracing metadata (`thread_id`, `action_id`) και evaluation tags σε όλα τα LangGraph runs και LangSmith traces (`config_for`, `run_example`, `decide_action`, `execute_action`, `decide`, `src/app.py`). Επιτυχής επίλυση του approval action format (`value` parameter & JSON payload) που ξεμπλοκάρει το Procedure B στο UI. Πλήρης επιβεβαίωση και 100% επιτυχία στο 10-request evaluation suite (10/10 requests pass every evaluator) και στις σουίτες ελέγχου (103 passed). ✋ Συντονισμός και κοινή υπογραφή με Quality (@VickyMil-ai). | Πλήρωση των acceptance criteria του Issue #32 (Steps 12–13), διασφάλιση πλήρους παρατηρησιμότητας (observability & trace auditability) στο LangSmith, και ολοκλήρωση όλων των παραδοτέων του ρόλου Workflow. | Issue #32, [roles/workflow.md](./roles/workflow.md), [roles/quality.md](./roles/quality.md) |
| 2026-11-20 | Interface | End-to-End Conversation Flow, Approval Gate & Multi-Turn UI Alignment: Ενεργοποίηση human approval gate για όλες τις ενέργειες (συμπεριλαμβανομένου του `link_outage`) ώστε να εμφανίζεται κάρτα Approve/Reject και να υποστηρίζεται restart εν μέσω έγκρισης, δρομολόγηση ερωτήσεων πολιτικής χωρίς `?` απευθείας στην ανάκτηση πολιτικής, υποστήριξη follow-up ερωτήσεων μετά την ενέργεια από το υπάρχον state/policy/graph, απομόνωση νέων αιτημάτων ανά turn με διατήρηση στοιχείων χρήστη, ευέλικτη αντιστοίχιση συσκευών/υπαλλήλων με σαφές μήνυμα καταλόγου, και καθαρισμός διπλών citations/τελειών μεταξύ `respond` και `src/app.py`. | Επίλυση προβλημάτων ροής διαλόγου και human-in-the-loop που εντοπίστηκαν κατά το end-to-end testing στο Chainlit UI, με 10/10 επιτυχία στο evaluation suite και 133/133 unit/integration tests. | [`src/app.py`](../src/app.py), [`src/agent/nodes.py`](../src/agent/nodes.py), [`src/agent/graph.py`](../src/agent/graph.py), [`tests/test_ui.py`](../tests/test_ui.py), [`tests/test_graph.py`](../tests/test_graph.py), [roles/interface.md](./roles/interface.md) |
| 2026-11-24 | Quality | Αναθεώρηση του `CONTRIBUTING.md` για το SupplyGuard AI: όνομα έργου, πίνακας ρόλων/backups, νέα commit scopes, review rotation, ενότητα Handoffs (✋), zero-conflict check πριν από PR, code conventions του capstone (Deep Agents, deterministic calculators, payload-bound approval ≤ €75k, idempotency, provenance, untrusted content) και Definition of Done σε επίπεδο task και project. Ενημέρωση θεμάτων 4, 7–10 και προσθήκη 17–18 ως Proposed. | Το `CONTRIBUTING.md` περιέγραφε ακόμη το HelpDesk Lite· η ομάδα χρειάζεται κοινούς κανόνες για το capstone πριν ξεκινήσουν τα PRs. | Issue #79, Issue #81 |
| 2026-11-24 | Quality | Σουίτα αξιολόγησης SupplyGuard (#82–#93): LangSmith `run_config` και ρυθμίσεις tracing, loader για τα 105 cases και το MC-17, 7 evaluators, runners για evaluation, red team, restart και pre-demo check πάνω σε ένα κοινό agent harness (`eval/harness.py`), retrieval benchmark με 24 ground-truth queries. Νέα έγγραφα: `EVALUATION.md`, `RETRIEVAL_BENCHMARK.md`, `RED_TEAM_REPORT.md`· ξαναγράφτηκαν τα `DEMO_SCRIPT.md`, `REHEARSAL_LOG.md`, `RESTART_TEST_SCENARIO.md`. Mid-week audit του `PROJECT_CHECKLIST.md`. Owners ρόλων στο `CONTRIBUTING.md`. | Τα `eval/` και τα έγγραφα Quality περιέγραφαν ακόμη το HelpDesk Lite. Η εκτέλεση στον πραγματικό agent περιμένει το harness του Workflow. | Issues #82–#93, [EVALUATION.md](./EVALUATION.md) |
| 2026-11-24 | Quality | Καθαρισμός υπολειμμάτων HelpDesk Lite σε έγγραφα και ρυθμίσεις: `README.md`, `GIT_GUIDE.md` (GitHub αντί Codeberg), `KNOWLEDGE_GRAPH.md`, `src/knowledge/README.md`, headers αρχείων, `helpdesk_network` → `supplyguard_network`, default `POSTGRES_DB` → `supplyguard`. Διαγραφή `PROJECT_NOTES.md` και `KNOWLEDGE_HANDOFF.md`. Ο κώδικας του HelpDesk agent μένει μέχρι τον SupplyGuard Deep Agent (λίστα στο `PROJECT_CHECKLIST.md` §9.5). | Τα έγγραφα περιέγραφαν άλλο σύστημα· το default `POSTGRES_DB=helpdesk` σύνδεε σε λάθος βάση όταν έλειπε το `.env`. | [PROJECT_CHECKLIST.md §9](./PROJECT_CHECKLIST.md#9-mid-week-audit-86) |
| 2026-11-25 | Quality | Έλεγχος Definition of Done (#93) στο `develop` @ `15fbd79`: 11/12 κριτήρια με απόδειξη (eval 99/99, restart A/B, red team, live benchmark, clean clone σε macOS). Ανοιχτό το κριτήριο 12: reviews μόνο από ένα μέλος, όλα τα merges από ένα μέλος (και self-merges), πρόβες εκκρεμούν | Το DoD απαιτεί απόδειξη, όχι δήλωση | Issue #93 |

## Definition of Done verification (#93)

Ελέγχεται από Quality πριν τις πρόβες (Ημ. 8) και ξανά πριν το demo. Κάθε γραμμή χρειάζεται απόδειξη (εντολή, αρχείο ή run), όχι δήλωση. Πηγή: [`PROJECT_CHECKLIST.md` §6](./PROJECT_CHECKLIST.md#6-definition-of-done) και [`CONTRIBUTING.md`](../CONTRIBUTING.md#definition-of-done).

| # | Κριτήριο | Απόδειξη / πώς ελέγχεται | Status (2026-11-25, `develop` @ `15fbd79`) |
|---|---|---|---|
| 1 | `docker compose up -d` < 10′ από καθαρό clone, 5 services | Run sheet στο [`CLEAN_CLONE_BENCHMARK.md` §8.3](./CLEAN_CLONE_BENCHMARK.md#83-run-sheet-day-5-2026-11-30) | ✅ Linux (~6′) και macOS (~5′)· ⏳ Windows (laptop 1) |
| 2 | Το `seed` φορτώνει όλα τα δεδομένα αυτόματα | `docker compose logs seed`: 18 πίνακες / 9,093 rows, Neo4j graph, 212 έγγραφα, 340 cases + memories, 5 users, exit 0 | ✅ |
| 3 | Ορχήστρωση με Deep Agents, planning, subagents | `src/agent/deep_agent.py`: `create_deep_agent` με 6 subagents, `interrupt_on` στο `execute_procurement_po` και PostgresSaver· στο live stack χτίζεται `CompiledStateGraph` | ✅ κώδικας και runtime· το trace στο LangSmith ελέγχεται στην πρόβα (segment 6) |
| 4 | Καμία PO χωρίς ρητή έγκριση | `eval.run_eval`: `human_approval_integrity` 99/99· `restart_scenario start` (no execution before approval) | ✅ |
| 5 | Payload-bound approval ≤ €75,000 | `policy_constraints` 26/26· restart A: ίδιο fingerprint `f22a…` μετά το restart, total €30,378 | ✅ |
| 6 | Restart χωρίς διπλή εκτέλεση | `eval.restart_scenario` A (approve, replay, double click → 1 εκτέλεση, 1 γραμμή `audit_log`) και B (`after_graph_query`, `before_execute`) | ✅ |
| 7 | Revenue at Risk χωριστά από Recovery Cost | `numerical_correctness` 65/65 (calculator tools) | ✅ |
| 8 | Τεκμηριωμένες απορρίψεις Helios / Borealis / Delta | `dependency_risk` 2/2 (EV-0001 golden)· `demo_check` 6a | ✅ |
| 9 | Το φυτεμένο έγγραφο αναφέρεται και εξουδετερώνεται | `red_team scan`: μόνο `DOC-NOT-HELIOS-PRICE`· `prompt_injection` 11/11 στο `run_eval` | ✅ |
| 10 | Retrieval benchmark pgvector / ChromaDB / Hybrid | `eval.retrieval_benchmark --live` (24 queries): R@5 1.000 / 0.833 / 0.986, MRR 1.000 / 0.938 / 0.979 | ✅ |
| 11 | Traces στο LangSmith και αξιολόγηση στα 105 | `eval.run_eval` 99/99 + 6 restart cases μέσω `restart_scenario` = 105· `eval.tracing`: enabled, project `supplyguard-ai` | ✅ τοπικά· ⏳ το experiment `run_eval --langsmith` δεν ξανατρέχτηκε σε αυτόν τον έλεγχο |
| 12 | Commits και reviews από όλα τα μέλη· όλοι εξηγούν τη ροή | GitHub (15 PRs): merged PRs ανά μέλος Vaggelis 5, Vicky 4, Alex 4, Stef 2. Reviews σε PR άλλου: μόνο @vaggelismpomponis (#102, #106). Όλα τα PRs έγιναν merge από @vaggelismpomponis, μαζί και 4 δικά του (#94, #96, #101, #105). Εξήγηση της ροής: [`REHEARSAL_LOG.md`](./REHEARSAL_LOG.md) | ❌ λείπουν reviews από @VickyMil-ai, @AlexZarkalis, @stef-fot· ⏳ πρόβες 1 και 2 |

Οι αριθμοί των evaluators είναι από `docker compose exec -T app python -m eval.run_eval` (2026-11-25, 7′40″). Τα tests: `python -m pytest tests -q` → 362 passed, 1 skipped.

**Για να κλείσει το #93:** (α) κάθε μέλος κάνει τουλάχιστον ένα GitHub review (Approve ή Request changes) σε PR άλλου ρόλου, σύμφωνα με τη rotation του `CONTRIBUTING.md`, και ο reviewer κάνει το merge· (β) γίνονται και καταγράφονται οι πρόβες 1 και 2 (#92)· (γ) τρέχει το Windows clean clone (#85)· (δ) η ομάδα αποφασίζει τα θέματα 5, 6 και 12 του πίνακα θεμάτων (κανάλι, ώρα stand-up, ημέρα pair session).

## Team Sign-off (Conversation Flow, Approval Gate & Multi-Turn UI Alignment ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Interface** | @AlexZarkalis (Primary) | Approval gate για `link_outage`, policy questions χωρίς `?`, post-action follow-ups, multi-turn isolation, flexible extraction, clean citation formatting (`src/app.py`, `src/agent/`, `tests/test_ui.py`) | **Signed-off** | 2026-11-20 |

## Team Sign-off (LangSmith Tracing Metadata & Evaluation Run Fixes ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @vaggelismpomponis | Tracing metadata (`thread_id`, `action_id`), evaluation tags σε LangGraph config & LangSmith trace runs, action value fix | **Signed-off** | 2026-11-19 |
| **Quality** | @VickyMil-ai | LangSmith run traces, 10/10 evaluation requests passing with metadata and citations | **Signed-off** | 2026-11-19 |

## Team Sign-off (Restart Test Verification: Zero Duplicate Execution ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @vaggelismpomponis | Pre-execution guard in `decide()`, zero duplicate executions across container restarts, restart test suite | **Signed-off** | 2026-11-19 |
| **Platform** | @vaggelismpomponis | PostgreSQL volume & `PostgresSaver` checkpoint persistence, audit_log consistency | **Signed-off** | 2026-11-19 |
| **Quality** | @VickyMil-ai | Procedure A automated verification executed (PASS), zero duplicate executions in history and audit_log | **Signed-off** | 2026-11-19 |

## Team Sign-off (Idempotent Action Execution & Status Tracking ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @VickyMil-ai (Primary) | Idempotency guard in `execute_action`, atomic updates `pending` -> `approved` -> `executed`, `create_ticket_idempotent` integration | **Signed-off** | 2026-11-19 |
| **Platform** | @vaggelismpomponis | `audit_log` table tracking, row-level locking (`SELECT ... FOR UPDATE`), restart persistence across container crashes | **Signed-off** | 2026-11-19 |
| **Interface** | @AlexZarkalis | Action ID persistence across session resumes, double-click lock coordination | **Signed-off** | 2026-11-19 |
| **Quality** | @VickyMil-ai | 37/37 tests passing in `test_graph.py`, 46/46 integration tests passing, 10/10 eval requests passing | **Signed-off** | 2026-11-19 |

## Team Sign-off (Decision Rules: Active Outage -> Link to Outage ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @VickyMil-ai (Primary) | Decision Precedence Matrix, evaluate dependency tree, inhibit credential reset during outages | **Signed-off** | 2026-11-19 |
| **Knowledge** | @stef-fot | Dependency traversal, direct service outage resolution, `outages` metadata contract | **Signed-off** | 2026-11-19 |
| **Quality** | @VickyMil-ai | 33/33 tests passing in `test_graph.py`, forbidden_actions evaluation verified | **Signed-off** | 2026-11-19 |

## Team Sign-off (Chainlit Interface Implementation & Approval Flow ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Interface** | @AlexZarkalis (Primary) | Chainlit UI (`src/app.py`), progress steps, approval cards (`action_id`), double-click prevention, `/resume`, citations (`chainlit.md`, `tests/test_ui.py`) | **Signed-off** | 2026-11-18 |

## Team Sign-off (Replace Mocks with Real Tools ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @VickyMil-ai (Primary) | Decommission mocks, wire `retrieve_policy` & `check_graph` in graph nodes | **Signed-off** | 2026-11-18 |
| **Knowledge** | @stef-fot | Tool signatures alignment, live pgvector retrieval & Neo4j graph queries contract | **Signed-off** | 2026-11-18 |
| **Quality** | @VickyMil-ai | 25/25 tests passing in `test_graph.py`, 10/10 milestone tests passing with live tools | **Signed-off** | 2026-11-18 |

## Team Sign-off (Day 5 Milestone End-to-End Mock Workflow inside Compose ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @VickyMil-ai (Primary) | End-to-end graph execution, topology branch coverage, zero unhandled exceptions | **Signed-off** | 2026-11-18 |
| **Quality** | @VickyMil-ai | 10/10 dataset scenarios execution, evaluator contracts alignment, test suite verification | **Signed-off** | 2026-11-18 |
| **Platform** | @vaggelismpomponis | Compose environment health, PostgresSaver checkpoints persistence, service networking | **Signed-off** | 2026-11-18 |

## Team Sign-off (Interrupt Nodes & PostgresSaver Integration ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @VickyMil-ai (Primary) | Interrupt nodes (`ask_clarification`, `human_approval`), `build_graph(use_postgres=True)`, resume mechanics (`reply`, `decide`) | **Signed-off** | 2026-11-18 |
| **Platform** | @vaggelismpomponis | `checkpoints` schema alignment, `get_pooled_connection()`, container & process recovery | **Signed-off** | 2026-11-18 |

## Team Sign-off (Field Extraction Node & 'Ask if Missing' Rule ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Workflow** | @VickyMil-ai (Primary) | `ExtractedFields` optional schema, `missing_fields()`, `ask_clarification` interrupt | **Signed-off** | 2026-11-18 |
| **Interface** | @AlexZarkalis | Clarification question contract, prompt display in UI, session email passing | **Signed-off** | 2026-11-18 |
| **Quality** | @VickyMil-ai | Clarification evaluator compatibility, EVAL-01 triage contract, zero guessing | **Signed-off** | 2026-11-18 |

## Team Sign-off (Final README Polish & Pre-Demo Clean-Clone Verification ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis (Primary) | Final README polish, clean-clone verification protocol, compose & dockerfile resilience | **Signed-off** | 2026-11-18 |
| **Quality** | @VickyMil-ai | Pre-demo timing verification (<3′), evaluator contracts, Definition of Done checkoff | **Signed-off** | 2026-11-18 |
| **Interface** | @AlexZarkalis | macOS host UI verification, approval card rendering & restart resume | **Signed-off** | 2026-11-18 |
| **Knowledge** | @stef-fot | Automated ingestion and Neo4j graph seeding idempotency verification | **Signed-off** | 2026-11-18 |

## Team Sign-off (Container Restart Support & Idempotency Test ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis (Primary) | `stop_grace_period: 15s`, `src/db/checkpointer.py`, `src/db/idempotency.py`, volume persistence | **Signed-off** | 2026-11-18 |
| **Workflow** | @VickyMil-ai | `PostgresSaver` integration, `audit_log` row locking, resume checkpoint contract | **Signed-off** | 2026-11-18 |
| **Quality** | @VickyMil-ai | `test_restart_idempotency.py`, restart test scenario verification, zero duplicate execution | **Signed-off** | 2026-11-18 |

## Team Sign-off (PostgreSQL Database Schema Init – Issue #5)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis (Primary) | `init.sql` script, `vector` extension, HNSW indexing, DB container mounts | **Signed-off** | 2026-11-17 |
| **Workflow** | All members | LangGraph checkpoint schema (`PostgresSaver`), `audit_log` idempotency fields | **Signed-off** | 2026-11-17 |
| **Knowledge** | @stef-fot | `policy_chunks` table, `embedding vector(1536)`, `effective_date` index | **Signed-off** | 2026-11-17 |

## Team Sign-off (Day 1 Contracts & Platform Alignment)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis (Primary) | Pinned versions policy (Docker & Python), Repo Structure, Compose readiness | **Signed-off** | 2026-11-16 |
| **Workflow** | All members | `AgentState`, Pydantic models, 5 action types, `thread_id` session mapping | **Signed-off** | 2026-11-16 |
| **Interface** | @AlexZarkalis | Interrupt payload contracts, Approval cards, UI progress steps | **Signed-off** | 2026-11-16 |
| **Knowledge** | @stef-fot | `PolicyResult` & `GraphResult` tool signatures, `effective_date` precedence | **Signed-off** | 2026-11-16 |
| **Quality** | @VickyMil-ai | Evaluator contracts, 10 test scenarios alignment, CONTRIBUTING.md consistency | **Signed-off** | 2026-11-16 |

## Team Sign-off (Phase 2 Platform & Interface Handoff ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis (Primary) | Multi-stage Dockerfile, Chainlit service & network linking | **Signed-off** | 2026-11-17 |
| **Interface** | @AlexZarkalis | UI containerization, app entrypoint (`src/app.py`) & port 8000 contract | **Signed-off** | 2026-11-17 |

## Team Sign-off (Day 5 Milestone Clean-Clone Test & Benchmark ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis (Primary) | Clean clone fixes, `.gitattributes`, cross-platform copy, benchmark docs | **Signed-off** | 2026-11-18 |
| **Quality** | @VickyMil-ai | Συντονισμός clean-clone test σε ≥3 laptops, χρόνος <10′, έλεγχος checklist | **Signed-off** | 2026-11-18 |
| **Interface** | @AlexZarkalis | Επαλήθευση σε macOS περιβάλλον & διαθεσιμότητα UI (port 8000) | **Signed-off** | 2026-11-18 |

## Team Sign-off (Automated Ingestion & Seeding in Compose ✋)

| Ρόλος | Εκπρόσωπος | Πεδίο Συμφωνίας | Status | Ημερομηνία |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis (Primary) | `seed` service στο compose, `scripts/seed.py`, `DATABASE_URL`, schema alignment | **Signed-off** | 2026-11-18 |
| **Knowledge** | @stef-fot | `ingest.py`, `seed_graph.py`, idempotent DDL & Cypher, tools integration | **Signed-off** | 2026-11-18 |

## Log προόδου και προβλημάτων (προαιρετικό)

Σύντομες σημειώσεις που βοηθούν στο `CONTRIBUTING.md` ή στο retrospective (π.χ. «το clean-clone test απέτυχε λόγω X»).

| Ημερομηνία | Ρόλος | Σημείωση | Επηρεάζει CONTRIBUTING; |
|---|---|---|---|
| 2026-11-18 | Platform | Clean-clone test σε Windows με core.autocrlf δημιουργούσε CRLF line endings σε SQL scripts. Προστέθηκε `.gitattributes` με κανόνα `* text=auto eol=lf`. | Όχι (αυτόματη ρύθμιση git) |
| 2026-11-18 | Platform | Η εντολή `cp .env.example .env` αποτύγχανε σε Windows Command Prompt (`cmd.exe`). Προστέθηκαν εναλλακτικές εντολές (`Copy-Item` για PowerShell, `copy` για CMD) στο `README.md`. | Ναι (οδηγίες README) |
| 2026-11-18 | Platform | Σε μηχανήματα με προϋπάρχοντα services στα ports 7474/7687 (Neo4j), το compose εμφάνιζε port conflict. Προστέθηκαν `NEO4J_HTTP_PORT` και `NEO4J_BOLT_PORT` στο `docker-compose.yml` και `.env.example`. | Όχι |
| 2026-11-18 | Quality | Στο Ubuntu 22.04 LTS χρήστες χωρίς docker group membership είχαν permission denied στο docker socket. Προστέθηκε ενότητα troubleshooting στο `README.md`. | Ναι (οδηγίες README) |
| 2026-11-24 | Platform, Knowledge, Workflow, Interface, Quality | Ολοκλήρωση ενοποίησης SupplyGuard AI: εναρμόνιση συμβολαίων (`S001–S006`, `AccessScope`), απόσυρση legacy HelpDesk Lite κώδικα/tests/πίνακα `tickets`, persistence κατάστασης UI & Deep Agents στο PostgreSQL (`thread_states`, `audit_log`), collision-free `PO-SUP-2026-...` IDs, υλοποίηση `src/agent/eval_harness.py` & kill points, και πλήρης επαλήθευση στο Compose stack (`eval.run_eval` 99/99, `red_team` 17/17, `restart_scenario` A/B PASS, `retrieval_benchmark --live`, `demo_check` PASS). | Ναι (ενημέρωση checklist & benchmark docs) |
