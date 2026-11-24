# SupplyGuard AI – Kanban Project Tasks Board

Αυτό το αρχείο περιέχει όλα τα επίσημα tasks του έργου (issues #32 έως #93), αντιστοιχισμένα 1:1 με τα βήματα των role files (`docs/roles/*.md`) και κατηγοριοποιημένα ανά ρόλο και φάση, ακριβώς όπως στο προηγούμενο project (`helpdesk_lite`).

---

## 1. Platform Tasks (@vaggelismpomponis)

| Issue | Τίτλος Task | Labels | Handoff |
|---|---|---|---|
| [#32](https://github.com/vaggelismpomponis/supplyguard_ai/issues/32) | `[Platform] Kick-off: Architecture Contracts, Multi-Service Stack & Pinned Versions Policy ✋` | `role:platform`, `phase:kickoff` | ✋ Όλοι |
| [#33](https://github.com/vaggelismpomponis/supplyguard_ai/issues/33) | `[Platform] Stack: Docker Compose with Postgres (pgvector), Neo4j 5.26+ & ChromaDB` | `role:platform`, `phase:skeleton` | |
| [#34](https://github.com/vaggelismpomponis/supplyguard_ai/issues/34) | `[Platform] Stack: Environment Configuration (.env.example & Persistent Volumes)` | `role:platform`, `phase:skeleton` | |
| [#35](https://github.com/vaggelismpomponis/supplyguard_ai/issues/35) | `[Platform] Stack: Multi-stage Dockerfile for Chainlit App & Deep Agents Runtime ✋` | `role:platform`, `phase:skeleton` | ✋ Interface |
| [#36](https://github.com/vaggelismpomponis/supplyguard_ai/issues/36) | `[Platform] Milestone: Clean-Clone Benchmark (<10 min) on Multiple Laptops ✋` | `role:platform`, `phase:milestone` | ✋ Quality |
| [#37](https://github.com/vaggelismpomponis/supplyguard_ai/issues/37) | `[Platform] Completion: Automated Compose Ingestion Service (seed) for Synthetic Data Package ✋` | `role:platform`, `phase:completion` | ✋ Knowledge |
| [#38](https://github.com/vaggelismpomponis/supplyguard_ai/issues/38) | `[Platform] Completion: Simulated Procurement System & External Risk MCP Integration ✋` | `role:platform`, `phase:completion` | ✋ Workflow |
| [#39](https://github.com/vaggelismpomponis/supplyguard_ai/issues/39) | `[Platform] Completion: Container Restart Support & Checkpoint Persistence for Idempotency Test ✋` | `role:platform`, `phase:completion` | ✋ Workflow, Quality |
| [#40](https://github.com/vaggelismpomponis/supplyguard_ai/issues/40) | `[Platform] Completion: Final README Polish & Pre-Demo Clean-Clone Verification` | `role:platform`, `phase:completion` | |

---

## 2. Interface Tasks (@AlexZarkalis)

| Issue | Τίτλος Task | Labels | Handoff |
|---|---|---|---|
| [#41](https://github.com/vaggelismpomponis/supplyguard_ai/issues/41) | `[Interface] Kick-off: UI Contracts, RBAC Scopes & thread_id Session Mapping Agreement ✋` | `role:interface`, `phase:kickoff` | ✋ Workflow, Platform |
| [#42](https://github.com/vaggelismpomponis/supplyguard_ai/issues/42) | `[Interface] Skeleton: Chainlit Application with Deep Agents Session Integration` | `role:interface`, `phase:skeleton` | |
| [#43](https://github.com/vaggelismpomponis/supplyguard_ai/issues/43) | `[Interface] Skeleton: Role-Based Access Control (RBAC) Authentication (Procurement, Finance, Guest)` | `role:interface`, `phase:skeleton` | |
| [#44](https://github.com/vaggelismpomponis/supplyguard_ai/issues/44) | `[Interface] Skeleton: Subagent Live Step Progress & Telemetry Indicators Display` | `role:interface`, `phase:skeleton` | |
| [#45](https://github.com/vaggelismpomponis/supplyguard_ai/issues/45) | `[Interface] Skeleton: Clarification Dialog via Interrupt for Ambiguous Incidents` | `role:interface`, `phase:skeleton` | |
| [#46](https://github.com/vaggelismpomponis/supplyguard_ai/issues/46) | `[Interface] Milestone: Day 5 UI Containerization in Docker Compose ✋` | `role:interface`, `phase:milestone` | ✋ Platform |
| [#47](https://github.com/vaggelismpomponis/supplyguard_ai/issues/47) | `[Interface] Completion: Operational Impact Dashboard (Usable vs Quarantined Stock & Factory Timelines)` | `role:interface`, `phase:completion` | |
| [#48](https://github.com/vaggelismpomponis/supplyguard_ai/issues/48) | `[Interface] Completion: Recovery Strategy Comparison Matrix (Recovery Cost vs Revenue at Risk)` | `role:interface`, `phase:completion` | |
| [#49](https://github.com/vaggelismpomponis/supplyguard_ai/issues/49) | `[Interface] Completion: Payload-Bound Human Approval Card with Double-Click Protection ✋` | `role:interface`, `phase:completion` | ✋ Workflow |
| [#50](https://github.com/vaggelismpomponis/supplyguard_ai/issues/50) | `[Interface] Completion: Post-Approval Receipt & Markdown/PDF Incident Report Export` | `role:interface`, `phase:completion` | |
| [#51](https://github.com/vaggelismpomponis/supplyguard_ai/issues/51) | `[Interface] Completion: Session Resume UI on Reconnect After App Container Restart` | `role:interface`, `phase:completion` | |
| [#52](https://github.com/vaggelismpomponis/supplyguard_ai/issues/52) | `[Interface] Completion: Multi-Turn Follow-Up Q&A from Persisted Case Memory` | `role:interface`, `phase:completion` | |
| [#53](https://github.com/vaggelismpomponis/supplyguard_ai/issues/53) | `[Interface] Completion: Demo Rehearsals Participation (>=2) ✋` | `role:interface`, `phase:completion` | ✋ Quality |

---

## 3. Workflow Tasks – Deep Agents (@VickyMil-ai)

| Issue | Τίτλος Task | Labels | Handoff |
|---|---|---|---|
| [#54](https://github.com/vaggelismpomponis/supplyguard_ai/issues/54) | `[Workflow] Kick-off: Propose Contracts (DisruptionFact, OperationalImpact, RecoveryOption, ApprovalPayload) ✋` | `role:workflow`, `phase:kickoff` | ✋ Όλοι |
| [#55](https://github.com/vaggelismpomponis/supplyguard_ai/issues/55) | `[Workflow] Kick-off: Agree on Tool Signatures (Inventory, BOM, Supplier Graph, Documents) ✋` | `role:workflow`, `phase:kickoff` | ✋ Knowledge |
| [#56](https://github.com/vaggelismpomponis/supplyguard_ai/issues/56) | `[Workflow] Skeleton: Root Deep Agent Harness (create_deep_agent) with Planning Middleware & Scratchpad` | `role:workflow`, `phase:skeleton` | |
| [#57](https://github.com/vaggelismpomponis/supplyguard_ai/issues/57) | `[Workflow] Skeleton: Triage & Entity Extraction Subagent with Clarification Rules` | `role:workflow`, `phase:skeleton` | |
| [#58](https://github.com/vaggelismpomponis/supplyguard_ai/issues/58) | `[Workflow] Skeleton: Human Approval Interrupt Hook & PostgreSQL Checkpointer Integration ✋` | `role:workflow`, `phase:skeleton` | ✋ Platform |
| [#59](https://github.com/vaggelismpomponis/supplyguard_ai/issues/59) | `[Workflow] Milestone: End-to-End Reference Incident Walkthrough with Mock Tools inside Compose` | `role:workflow`, `phase:milestone` | |
| [#60](https://github.com/vaggelismpomponis/supplyguard_ai/issues/60) | `[Workflow] Completion: Replace Mocks with Real Knowledge Tools & Live Cypher Queries ✋` | `role:workflow`, `phase:completion` | ✋ Knowledge |
| [#61](https://github.com/vaggelismpomponis/supplyguard_ai/issues/61) | `[Workflow] Completion: Specialist Subagents (Operational Impact, Contract & Provenance, Supply Graph)` | `role:workflow`, `phase:completion` | |
| [#62](https://github.com/vaggelismpomponis/supplyguard_ai/issues/62) | `[Workflow] Completion: Deterministic Business Calculators (Recovery Cost & Revenue at Risk Tools)` | `role:workflow`, `phase:completion` | |
| [#63](https://github.com/vaggelismpomponis/supplyguard_ai/issues/63) | `[Workflow] Completion: Recovery Strategy Optimizer Subagent (>=3 Viable Strategies & Trade-off Matrix)` | `role:workflow`, `phase:completion` | |
| [#64](https://github.com/vaggelismpomponis/supplyguard_ai/issues/64) | `[Workflow] Completion: Strict Payload-Bound Approval Gate & Idempotent Simulated Procurement Execution ✋` | `role:workflow`, `phase:completion` | ✋ Platform |
| [#65](https://github.com/vaggelismpomponis/supplyguard_ai/issues/65) | `[Workflow] Completion: Container Restart Verification (Zero Duplicate PO Execution on Replay) ✋` | `role:workflow`, `phase:completion` | ✋ Platform, Quality |
| [#66](https://github.com/vaggelismpomponis/supplyguard_ai/issues/66) | `[Workflow] Completion: LangSmith Tracing Metadata, Subagent Spans & Case Memory Persistence ✋` | `role:workflow`, `phase:completion` | ✋ Quality |

---

## 4. Knowledge Tasks (@stef-fot)

| Issue | Τίτλος Task | Labels | Handoff |
|---|---|---|---|
| [#67](https://github.com/vaggelismpomponis/supplyguard_ai/issues/67) | `[Knowledge] Kick-off: Agree on Tool Output Models & Retrieval Signatures ✋` | `role:knowledge`, `phase:kickoff` | ✋ Workflow |
| [#68](https://github.com/vaggelismpomponis/supplyguard_ai/issues/68) | `[Knowledge] Dataset: Relational Schema DDL for Suppliers, Components, BOMs, Inventory & Orders` | `role:knowledge`, `phase:skeleton` | |
| [#69](https://github.com/vaggelismpomponis/supplyguard_ai/issues/69) | `[Knowledge] Graph: Design & Document Neo4j Multi-tier Supply Chain Model with Schema Diagram` | `role:knowledge`, `phase:skeleton` | |
| [#70](https://github.com/vaggelismpomponis/supplyguard_ai/issues/70) | `[Knowledge] Ingestion: pgvector Document Ingestion Script with Provenance Metadata & Access Scopes ✋` | `role:knowledge`, `phase:skeleton` | ✋ Platform |
| [#71](https://github.com/vaggelismpomponis/supplyguard_ai/issues/71) | `[Knowledge] Seeding: Idempotent Neo4j Seeding Script with Upstream Supplier Dependencies ✋` | `role:knowledge`, `phase:skeleton` | ✋ Workflow |
| [#72](https://github.com/vaggelismpomponis/supplyguard_ai/issues/72) | `[Knowledge] Vector: ChromaDB Indexing for Document Corpus and Benchmark Comparison` | `role:knowledge`, `phase:skeleton` | |
| [#73](https://github.com/vaggelismpomponis/supplyguard_ai/issues/73) | `[Knowledge] Skeleton: Provide Mock Knowledge & Graph Tools with Agreed Signatures to Workflow` | `role:knowledge`, `phase:skeleton` | |
| [#74](https://github.com/vaggelismpomponis/supplyguard_ai/issues/74) | `[Knowledge] Milestone: Day 5 Automated Data Seeding Execution in Compose ✋` | `role:knowledge`, `phase:milestone` | ✋ Platform |
| [#75](https://github.com/vaggelismpomponis/supplyguard_ai/issues/75) | `[Knowledge] Completion: Implement Hybrid Retrieval Tool (pgvector + BM25 + Neo4j Graph Traversal)` | `role:knowledge`, `phase:completion` | |
| [#76](https://github.com/vaggelismpomponis/supplyguard_ai/issues/76) | `[Knowledge] Completion: Index 300 Disruption Cases and 40 Approved Incident Memories` | `role:knowledge`, `phase:completion` | |
| [#77](https://github.com/vaggelismpomponis/supplyguard_ai/issues/77) | `[Knowledge] Completion: Resolve Planted Data Quality Defects (Conflicting Dates, Stale Certs, Duplicate Notices)` | `role:knowledge`, `phase:completion` | |
| [#78](https://github.com/vaggelismpomponis/supplyguard_ai/issues/78) | `[Knowledge] Completion: Hand Off Test Dataset & Ground Truth to Quality for 105 Evaluation Cases ✋` | `role:knowledge`, `phase:completion` | ✋ Quality |

---

## 5. Quality Tasks (@VickyMil-ai)

| Issue | Τίτλος Task | Labels | Handoff |
|---|---|---|---|
| [#79](https://github.com/vaggelismpomponis/supplyguard_ai/issues/79) | `[Quality] Kick-off: Coordinate Team Agreements in CONTRIBUTING_LOG.md` | `role:quality`, `phase:kickoff` | |
| [#80](https://github.com/vaggelismpomponis/supplyguard_ai/issues/80) | `[Quality] Kick-off: Populate Remote Project Task Board from Role Files ✋` | `role:quality`, `phase:kickoff` | ✋ Όλοι |
| [#81](https://github.com/vaggelismpomponis/supplyguard_ai/issues/81) | `[Quality] Kick-off: Draft CONTRIBUTING.md Pull Request for SupplyGuard AI` | `role:quality`, `phase:kickoff` | |
| [#82](https://github.com/vaggelismpomponis/supplyguard_ai/issues/82) | `[Quality] Tracing: Setup LangSmith Project & Tracing Configuration for Deep Agents ✋` | `role:quality`, `phase:skeleton` | ✋ Platform |
| [#83](https://github.com/vaggelismpomponis/supplyguard_ai/issues/83) | `[Quality] Dataset: Load 105 Held-out Scenarios and MC-17 Reference Incident Benchmark ✋` | `role:quality`, `phase:skeleton` | ✋ Knowledge |
| [#84](https://github.com/vaggelismpomponis/supplyguard_ai/issues/84) | `[Quality] Evaluators: Implement Automated Evaluators (Triage, Numerical Correctness, Policy, Dependencies, Approval)` | `role:quality`, `phase:skeleton` | |
| [#85](https://github.com/vaggelismpomponis/supplyguard_ai/issues/85) | `[Quality] Milestone: Coordinate Day 5 Clean-Clone Test Across Team Laptops ✋` | `role:quality`, `phase:milestone` | ✋ Platform |
| [#86](https://github.com/vaggelismpomponis/supplyguard_ai/issues/86) | `[Quality] Milestone: Mid-Week Audit of PROJECT_CHECKLIST.md` | `role:quality`, `phase:milestone` | |
| [#87](https://github.com/vaggelismpomponis/supplyguard_ai/issues/87) | `[Quality] Completion: Execute Retrieval Benchmark Experiment (pgvector vs ChromaDB vs Hybrid)` | `role:quality`, `phase:completion` | |
| [#88](https://github.com/vaggelismpomponis/supplyguard_ai/issues/88) | `[Quality] Completion: Execute LangSmith Evaluation Run on 105 Disruption Cases` | `role:quality`, `phase:completion` | |
| [#89](https://github.com/vaggelismpomponis/supplyguard_ai/issues/89) | `[Quality] Completion: Adversarial Red-Teaming & Prompt Injection Defense Verification ✋` | `role:quality`, `phase:completion` | ✋ Workflow |
| [#90](https://github.com/vaggelismpomponis/supplyguard_ai/issues/90) | `[Quality] Completion: Author & Execute Container Restart Scenario with Zero Duplicate Execution Check ✋` | `role:quality`, `phase:completion` | ✋ Workflow, Platform |
| [#91](https://github.com/vaggelismpomponis/supplyguard_ai/issues/91) | `[Quality] Completion: Draft 10-Minute Demo Script & Rehearsal Schedule` | `role:quality`, `phase:completion` | |
| [#92](https://github.com/vaggelismpomponis/supplyguard_ai/issues/92) | `[Quality] Completion: Conduct >=2 Demo Rehearsals with Role Presentation Rotation` | `role:quality`, `phase:completion` | |
| [#93](https://github.com/vaggelismpomponis/supplyguard_ai/issues/93) | `[Quality] Completion: Finalize CONTRIBUTING.md & Verify Definition of Done` | `role:quality`, `phase:completion` | |
