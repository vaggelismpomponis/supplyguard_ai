# Restart Test Scenario: Zero Duplicate Execution

**Owner:** Quality · **Issue:** #90 · **Collaboration:** Workflow, Platform ✋
**Cases:** EV-0086..EV-0091 · **Code:** [`eval/restart_scenario.py`](../eval/restart_scenario.py) · **Tests:** [`tests/test_restart_scenario.py`](../tests/test_restart_scenario.py)

> **Status (2026-11-24):** scenario and checks are written and pass on a reference agent whose state
> survives a simulated restart. The run against Docker waits for the Deep Agents harness (Workflow)
> and the kill points. The HelpDesk Lite run of 2026-11-19 no longer applies and was removed.

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

_Pending: needs the harness and the kill points._

| Date | Commit | Procedure | Case(s) | Result | Details |
|---|---|---|---|---|---|
| | | A | EV-0086, EV-0089 | | |
| | | B | EV-0087, EV-0090 | | |
| | | B | EV-0088, EV-0091 | | |
| | | C (UI) | | | |

## Findings from reading the code (before any run)

1. **Purchase order ids restart from 9001 after every restart.** `SimulatedProcurementSystem` numbers
   new orders `PO-SUP-2026-{len(self._executed_orders) + 9001}` from an in-memory dict, which is empty
   after a restart. The first new order after a restart therefore gets an id that already exists in
   `purchase_orders`, and `INSERT ... ON CONFLICT (po_id) DO NOTHING` drops it silently. The receipt says
   "confirmed" but the order is not in the table. → Platform: derive the id from `action_id`, or from a
   database sequence.
2. **`audit_log.thread_id` is not the thread.** The MCP server writes `thread-{action_id[:8]}`, so
   executions cannot be traced back to the Chainlit session from the database. → Platform: pass the real
   `thread_id` into `create_purchase_order`.
3. **The `purchase_orders` table has no `action_id` column**, so a duplicate purchase order cannot be
   detected from that table. The test relies on `audit_log`. → Platform, if we want a second
   independent count.
4. **The SupplyGuard UI flow keeps the case in memory.** PR #97 stores each case in `_CASE_STORE`, a
   dict inside `src/app.py`, not in the Postgres checkpoint. A `docker compose restart app` loses it,
   and "Resume the case…" with an empty store rebuilds a default MC-17 case instead of restoring the
   real one. Procedure C will fail on step 3 until the case lives in the agent's checkpoint.
   → Interface, Workflow.

## Sign-off

| Role | Who | Scope | Status | Date |
|---|---|---|---|---|
| Quality | @VickyMil-ai | Scenario, checks, runs A–C | Pending | |
| Workflow | @VickyMil-ai | Harness, Postgres checkpointer, kill points, replay guard | Pending | |
| Platform | @vaggelismpomponis | `audit_log`, MCP idempotency, PO id after restart | Pending | |
| Interface | @AlexZarkalis | Procedure C: card restored, double-click guard | Pending | |
