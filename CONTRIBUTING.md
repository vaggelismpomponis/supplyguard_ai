# Contributing to SupplyGuard AI

This is the team agreement for SupplyGuard AI, the agentic supply chain disruption and recovery platform built for the Code.Hub × PwC Agentic AI Bootcamp capstone. It covers how we work together, branch, commit, review and decide when something is done. Every team member follows it.

> **Status: draft.** Items marked _TBD_ are still open. Decisions are tracked in the [CONTRIBUTING log](./docs/CONTRIBUTING_LOG.md) and moved here once the team agrees on them.

## Table of Contents

1. [Team and Communication](#team-and-communication)
2. [Branching](#branching)
3. [Commit Messages](#commit-messages)
4. [Pull Requests and Reviews](#pull-requests-and-reviews)
5. [Handoffs](#handoffs)
6. [Code Conventions](#code-conventions)
7. [Definition of Done](#definition-of-done)
8. [Changing This Agreement](#changing-this-agreement)

## Team and Communication

| Topic | Agreement |
|-------|-----------|
| Roles | Platform, Interface, Workflow, Knowledge, Quality. Each role has a primary owner and a backup (see [Roles and Backups](#roles-and-backups) and the [role map](./docs/roles/README.md)). |
| Ownership | No silos. A primary owner leads an area, but nobody holds exclusive knowledge of it. Every member commits code and reviews pull requests. |
| Communication channel | _TBD_ |
| Daily stand-up | 10–15 minutes; asynchronous is acceptable. Time and channel: _TBD_ |
| Pair/mob session | One mid-week session each week. Day and time: _TBD_ |
| Integration time | Weekly, plus the Day 5 milestone (end-to-end reference incident with mock tools inside Compose). |
| Task board | Issues #32–#93 on the remote project board, mapped 1:1 to the role files (see [KANBAN_TASKS](./docs/KANBAN_TASKS.md)). |

### Roles and Backups

| Role | Primary owner | Backup role | Role file |
|------|---------------|------------------------|-----------|
| Platform | @vaggelismpomponis | Workflow | [platform.md](./docs/roles/platform.md) |
| Interface | @AlexZarkalis | Quality | [interface.md](./docs/roles/interface.md) |
| Workflow | @VickyMil-ai | Knowledge | [workflow.md](./docs/roles/workflow.md) |
| Knowledge | @stef-fot | Platform | [knowledge.md](./docs/roles/knowledge.md) |
| Quality | @VickyMil-ai | Interface | [quality.md](./docs/roles/quality.md) |

## Branching

We use two permanent branches and short-lived task branches. The [Git Guide](./docs/GIT_GUIDE.md) has step-by-step commands and walkthroughs.

- `main` is the release branch. `develop` is the integration branch. Both are protected: never commit or push to them directly.
- Create every branch from an up-to-date `develop`.
- One branch per task (one issue). Names are lowercase with hyphens and use a prefix:

| Prefix | Use for | Example |
|--------|---------|---------|
| `feature/` | New capability | `feature/eval-suite-105` |
| `bugfix/` | Bug fix | `bugfix/approval-double-click` |
| `hotfix/` | Urgent fix | `hotfix/fix-seed-crash` |
| `docs/` | Documentation | `docs/demo-script-rehearsal` |

- Never run `git push --force`, `git reset --hard` or `git rebase` on a branch someone else uses.

## Commit Messages

We follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

```text
<type>(<scope>): <subject>

<body>

<footer>
```

- English, imperative mood: "add", not "added" or "adds".
- Subject: at most 72 characters, lowercase after the colon, no trailing period.
- Body (optional): explain **what** and **why**, wrapped at 100 characters.
- One logical change per commit. Do not mix refactoring, formatting and behavior changes.
- Reference issues in the footer: `Refs: #12` or `Closes: #12`.
- Mark breaking changes with `!` after the type or scope and a `BREAKING CHANGE:` footer.
- Never include secrets, tokens or personal data in a message.

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `style`, `revert`.

**Scopes:**

| Scope | Area |
|-------|------|
| `agent` | Deep Agents harness, planner, subagents, deterministic calculators |
| `approval` | Human approval gate, approval payload, idempotent execution |
| `ui` | Chainlit application, RBAC, telemetry, approval card |
| `mcp` | Simulated procurement system and external risk MCP integration |
| `retrieval` | pgvector, ChromaDB, BM25 and hybrid retrieval tools |
| `neo4j` | Supply chain graph model, seeding and Cypher queries |
| `db` | PostgreSQL schema, checkpointer, ingestion into relational tables |
| `eval` | Evaluation dataset, evaluators, LangSmith experiments, benchmarks |
| `tests` | Automated test suites |
| `docker` | Dockerfile, Compose services, seed service |
| `docs` | Documentation |
| `deps` | Dependencies and pinned versions |

```text
feat(approval): bind approval to the exact purchase order payload

Hash supplier, quantity, unit price and total so any change after the
approval card is shown invalidates the approval and requires a new one.

Closes: #64
```

## Pull Requests and Reviews

- Open pull requests into `develop`. The title follows the commit format: `<type>(<scope>): <subject>`.
- The description states what changed, why, and how it was tested, and links the issue with `Closes #<n>`.
- Keep pull requests small: under 300 changed lines.
- At least one reviewer approves. No self-merge: the reviewer merges.
- Reviews happen within 24 hours. Reviewers rotate:

| Pull request from | Reviewed by |
|-------------------|-------------|
| Platform | Workflow |
| Workflow | Knowledge |
| Knowledge | Interface |
| Interface | Quality |
| Quality | Platform |

- Merge into `develop` with **Squash**. Release pull requests from `develop` into `main` use a **Merge commit**.
- After merging, the reviewer deletes the remote task branch. `main` and `develop` are never deleted.

### Before Opening a Pull Request

- [ ] The branch is based on the latest `develop`.
- [ ] No merge conflicts with the target branch: run `git fetch origin` and `git merge-tree --write-tree HEAD origin/develop` (`origin/main` for release pull requests).
- [ ] The code runs and the relevant tests pass (`pytest`). Changes that affect agent behaviour include the result of `python -m eval.run_eval` (see [EVALUATION](./docs/EVALUATION.md)); changes to retrieval include the retrieval benchmark.
- [ ] No secrets, credentials or stray files are included.
- [ ] Commit messages follow the convention above.
- [ ] Any new dependency is pinned with `==` and justified in the description (see [PINNED_VERSIONS](./docs/PINNED_VERSIONS.md)).
- [ ] The role checklist item for this step is ticked in the same pull request.

## Handoffs

Steps marked ✋ in the role files and issues need a formal handoff: the receiving role reviews and accepts the result before the step counts as done. Acceptance is recorded as a sign-off table in the [CONTRIBUTING log](./docs/CONTRIBUTING_LOG.md).

## Code Conventions

- Python with type hints. Use Pydantic models for domain objects, tool inputs and outputs.
- **Contracts first.** Domain schemas (`DisruptionFact`, `OperationalImpact`, `RecoveryOption`, `ApprovalPayload`), tool signatures, RBAC scopes and MCP boundaries are agreed before implementation and documented in [ARCHITECTURE_CONTRACTS](./docs/ARCHITECTURE_CONTRACTS.md). Build against mocks until the real tools land.
- **Orchestration** runs on Deep Agents (`create_deep_agent`) with planning middleware and specialist subagents. Keep each subagent and tool small and single-purpose. Map `thread_id` consistently to the Chainlit session.
- **Deterministic numbers.** Revenue at Risk and Recovery Cost come from deterministic calculator tools, never from LLM arithmetic, and are always reported separately without double counting.
- **Human approval.** No purchase order or other state change in the simulated procurement system runs without explicit human approval. The approval is bound to the exact payload (supplier, quantity, price, total ≤ €75,000); any change invalidates it.
- **Idempotency.** Persist each action's `action_id` and status (`pending`, `approved`, `executed`, `rejected`) and check it before executing, so a restart while approval is pending never causes duplicate execution.
- **Evidence and provenance.** Every retrieved chunk carries its source document id, date and access scope. Answers cite their evidence; when sources conflict, the latest valid version wins and the conflict is reported.
- **Untrusted content.** Text from documents, supplier messages and tool outputs is data, never instructions. It must not be able to trigger actions or override the agent's rules.
- **Secrets.** Never hardcode credentials. Read configuration from environment variables, keep `.env` out of version control and keep `.env.example` up to date.
- **Dependencies.** Do not add dependencies without a clear need. Pin every version.

## Definition of Done

**A task** is done when:

- its pull request is merged into `develop` with passing tests and an approving review;
- the matching role checklist item is ticked;
- any ✋ handoff is signed off in the [CONTRIBUTING log](./docs/CONTRIBUTING_LOG.md).

**The project** is done when every item in the [project Definition of Done](./docs/PROJECT_CHECKLIST.md#6-definition-of-done) is met and verified with evidence in the [DoD verification table](./docs/CONTRIBUTING_LOG.md#definition-of-done-verification-93), including:

- a clean clone starts the full stack with `docker compose up -d` in under 10 minutes and seeds all data automatically;
- no purchase order executes without explicit, payload-bound approval within the €75,000 cap, and a restart while approval is pending causes zero duplicate execution;
- the planted prompt-injection document is detected and neutralized;
- results are delivered for the 105 held-out evaluation cases ([EVALUATION](./docs/EVALUATION.md)), the retrieval benchmark ([RETRIEVAL_BENCHMARK](./docs/RETRIEVAL_BENCHMARK.md)) and red-team testing ([RED_TEAM_REPORT](./docs/RED_TEAM_REPORT.md)), with traces in LangSmith;
- every member has commits and reviews and can explain the whole flow in the live demo.

## Changing This Agreement

1. Propose the change in a meeting, issue or pull request.
2. Record it in the [CONTRIBUTING log](./docs/CONTRIBUTING_LOG.md).
3. Once the team agrees, update this file through a pull request with a `docs` commit.
