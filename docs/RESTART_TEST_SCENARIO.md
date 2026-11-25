# Restart Test Scenario: Zero Duplicate Execution

**Owner:** Quality · **Issue:** #90 · **Collaboration:** Workflow, Platform ✋
**Cases:** EV-0086..EV-0091 · **Code:** [`eval/restart_scenario.py`](../eval/restart_scenario.py) · **Tests:** [`tests/test_restart_scenario.py`](../tests/test_restart_scenario.py)

> **Status (2026-11-24):** Procedures A and B (`EV-0086..EV-0091`) executed and passed against the
> live Docker Compose stack (`supplyguard_app` + `supplyguard_postgres`), with real container
> restarts (`docker compose restart app`), kill points (`SUPPLYGUARD_CRASH_AT`), and Postgres
> verification (`PO-SUP-2026-...` and `audit_log`). The HelpDesk Lite run of 2026-11-19 no longer
> applies and was removed.

## Goal

The MC-17 purchase order needs approval. Whatever point the app container dies at, the case must
resume from its Postgres checkpoint with the **same approval payload**, and the purchase order must be
created **exactly once**.

| Case | Kill point | After the restart |
|---|---|---|
| EV-0086, EV-0089 | `approval_pending`: the approval card is shown, no decision yet | still waiting, same payload; approve → 1 PO; replays → still 1 |
| EV-0087, EV-0090 | `after_graph_query`: inside the investigation, after the Neo4j step | resumes and reaches the approval pause with one payload; 0 POs |
| EV-0088, EV-0091 | `before_execute`: approved, about to call the procurement MCP | resumes and executes once; 1 PO |

## What counts as an execution

Two counts must agree:

1. **Thread state:** `CaseOutcome.executed_action_ids`, one entry per call to the procurement MCP.
2. **Database:** rows in `audit_log` with that `action_id` and `status = 'executed'`, written by
   `SimulatedProcurementSystem.create_purchase_order`.

If they disagree, the higher count is used, so a duplicate on either side fails the test.
"Same payload" is checked with `payload_fingerprint`, a hash of action type, supplier, component,
quantity, unit price and total.

## Preconditions

- Stack running and seeded: `docker compose up -d --wait`.
- The agent uses the Postgres checkpointer.
- Workflow's harness is available (see [EVALUATION.md](./EVALUATION.md#agent-harness)).
- Kill points B and C: the agent exits when `SUPPLYGUARD_CRASH_AT` names the step it is in.

## Procedure A: restart while approval is pending (EV-0086, EV-0089)

```bash
# 1. Run the reference incident until the approval card. Note THREAD and FINGERPRINT.
docker compose exec -T app python -m eval.restart_scenario start

# 2. Restart while approval is pending
docker compose restart app

# 3. Same payload still waiting, nothing executed; then approve -> exactly one execution
docker compose exec -T app python -m eval.restart_scenario approve <THREAD> --fingerprint <FINGERPRINT>

# 4. Restart after execution
docker compose restart app

# 5. Finished, executed once; replay the approval twice and resume -> still one
docker compose exec -T app python -m eval.restart_scenario verify <THREAD>
```

## Procedure B: kill inside a step (EV-0087/0090, EV-0088/0091)

```bash
docker compose exec -T app python -m eval.restart_scenario crash after_graph_query   # note THREAD
docker compose restart app
docker compose exec -T app python -m eval.restart_scenario resume <THREAD> --expect approval

docker compose exec -T app python -m eval.restart_scenario crash before_execute      # note THREAD
docker compose restart app
docker compose exec -T app python -m eval.restart_scenario resume <THREAD> --expect executed
```

`crash` prints `FAIL ... process survived the kill point` if the agent did not exit, which means the
kill point is not implemented.

## Procedure C: manual, through the UI

1. Log in as the procurement manager at `http://localhost:8000` and send the reference message
   (EV-0001). Wait for the approval card. Note the supplier, quantity, unit price and total.
2. Run `docker compose restart app`, then reload the page.
3. Expected: the conversation is back with the same approval card and the same four values.
4. Click **Approve**. Expected: one purchase order receipt (`PO-SUP-...`).
5. Run `docker compose restart app` and reload. Click the old **Approve** again if it is still visible.
   Expected: "already processed" and no second receipt.

Check the database (one row expected):

```bash
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT action_id, status, executed_at FROM audit_log WHERE status = '"'"'executed'"'"' ORDER BY executed_at DESC LIMIT 5"'
```

## Expected results

| Phase | Check | Expected |
|---|---|---|
| start | paused | `approval` |
| start | payload | status `pending`, total ≤ €75,000 |
| start | executions | 0 |
| approve (after restart) | still paused, same fingerprint | `approval`, equal |
| approve | executions while paused | 0 |
| approve | after approving | 1, status `executed` |
| verify (after restart) | thread finished | nothing pending |
| verify | after 2 approval replays and a resume | 1 |
| verify | `audit_log` executed rows | 1 |
| resume `--expect approval` | paused, one payload, executions | `approval`, 1, 0 |
| resume `--expect executed` | finished, executions | done, 1 |

## Results

Executed against the live Docker Compose stack with real `docker compose restart app` cycles (~2.94–3.00s ready to HTTP 200):

| Date | Commit | Procedure | Case(s) | Result | Details |
|---|---|---|---|---|---|
| 2026-11-24 | `a54ed2f` | A | EV-0086, EV-0089 | **PASS** | Thread `restart-8f9ad42de78b`, action `act-f168758e3d`, fingerprint `0209470f2c79bbd0`, restarts 3.00s & 2.94s; `PO-SUP-2026-8958085E` created once (`audit_log` executed rows = 1 after double-click/resume replays) |
| 2026-11-24 | `a54ed2f` | B (`after_graph_query`) | EV-0087, EV-0090 | **PASS** | Crash exited 1 on `restart-after_graph_query-95d2d1b1`; restart 2.97s; `resume --expect approval` paused at `approval` (`act-bf7edebf45` pending, 0 executions) |
| 2026-11-24 | `a54ed2f` | B (`before_execute`) | EV-0088, EV-0091 | **PASS** | Crash exited 1 on `restart-before_execute-2987d273`; restart 2.98s; `resume --expect executed` completed with `PO-SUP-2026-4202FBD2` (`act-297cddab4b` executed once) |
| 2026-11-24 | `a54ed2f` | C (UI) | Manual UI walk-through | **Code & DB wired** | `_CASE_STORE` removed from `src/app.py`; UI reads/writes persisted `thread_states` + `audit_log` via `get_orchestrator()`; manual browser click test pending human demo rehearsal |

## Findings from reading the code (all fixed 2026-11-24)

1. **Purchase order ids restart from 9001 after every restart — FIXED.** `SimulatedProcurementSystem` now generates deterministic collision-free IDs (`PO-SUP-2026-<sha256(action_id)[:8]>`) and returns stored receipts from `audit_log` on replay.
2. **`audit_log.thread_id` is not the thread — FIXED.** Real `thread_id` (e.g., `restart-8f9ad42de78b`) is propagated end-to-end into `create_purchase_order` and persisted in `audit_log`.
3. **The `purchase_orders` table has no `action_id` column — FIXED.** Added `action_id VARCHAR(64) UNIQUE` to `purchase_orders` (`docker/postgres/init.sql` & `001_upgrade_schema.sql`).
4. **The SupplyGuard UI flow keeps the case in memory — FIXED.** Removed `_CASE_STORE` from `src/app.py`; all state lives in PostgreSQL `thread_states` and `audit_log` via `get_orchestrator()`.

## Sign-off

| Role | Who | Scope | Status | Date |
|---|---|---|---|---|
| Quality | @VickyMil-ai | Scenario, checks, automated runs A–B | **Verified (A & B)** | 2026-11-24 |
| Workflow | @VickyMil-ai | Harness, Postgres state & checkpointer, kill points, replay guard | **Verified** | 2026-11-24 |
| Platform | @vaggelismpomponis | `audit_log`, MCP idempotency, PO id after restart | **Verified** | 2026-11-24 |
| Interface | @AlexZarkalis | Postgres UI state restore, double-click guard (automated tests verified; manual UI pending) | **Implemented** | 2026-11-24 |
