"""Container restart scenario with zero duplicate execution (#90, cases EV-0086..EV-0091).

The MC-17 reference incident runs until the purchase order waits for approval, the app container
is restarted (or killed at a given step), and the case must resume from its Postgres checkpoint
with the same approval payload and never execute twice. Each phase is its own process inside the
app container, with a restart in between (see docs/RESTART_TEST_SCENARIO.md):

    # A. restart while approval is pending (EV-0086, EV-0089)
    docker compose exec -T app python -m eval.restart_scenario start
    docker compose restart app
    docker compose exec -T app python -m eval.restart_scenario approve <thread_id> --fingerprint <fp>
    docker compose restart app
    docker compose exec -T app python -m eval.restart_scenario verify <thread_id>

    # B. kill inside a step (EV-0087 after_graph_query, EV-0090; EV-0088 before_execute, EV-0091)
    docker compose exec -T app python -m eval.restart_scenario crash after_graph_query
    docker compose restart app
    docker compose exec -T app python -m eval.restart_scenario resume <thread_id> --expect approval

Executions are counted twice: from the thread state (``executed_action_ids``) and from the
``audit_log`` rows the procurement MCP writes. Both must agree. The kill points need the agent to
honour ``SUPPLYGUARD_CRASH_AT=<step>`` (Workflow, see docs/EVALUATION.md#agent-harness).
Each phase prints PASS/FAIL lines and exits with 0 only when all its checks pass.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Any, Optional

from eval.dataset import GOLDEN_ID, load_examples
from eval.harness import AgentHarness, HarnessUnavailable, load_harness, payload_fingerprint
from eval.tracing import configure_tracing

CRASH_ENV = "SUPPLYGUARD_CRASH_AT"
KILL_STEPS = ("approval_pending", "after_graph_query", "before_execute")
USER = "u-pm-01"


def golden_message() -> str:
    return next(e for e in load_examples() if e["metadata"]["id"] == GOLDEN_ID)["inputs"]["message"]


class Checks:
    def __init__(self) -> None:
        self.failed = 0

    def check(self, name: str, ok: bool, detail: Any = "") -> bool:
        self.failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail != "" else ""))
        return ok

    def result(self) -> int:
        print(f"RESULT: {'PASS' if not self.failed else 'FAIL'}")
        return 0 if not self.failed else 1


def db_executions(action_id: Optional[str]) -> Optional[int]:
    """Executed audit_log rows for the action, or None if the database is unreachable."""
    if not action_id:
        return 0
    try:
        from src.knowledge.common import pg

        with pg() as conn:
            row = conn.execute(
                "SELECT count(*) FROM audit_log WHERE action_id = %s AND status = 'executed'",
                (action_id,),
            ).fetchone()
        return int(row[0])
    except Exception as exc:
        print(f"      audit_log not readable: {type(exc).__name__}: {exc}")
        return None


def count_executions(harness: AgentHarness, thread_id: str, action_id: Optional[str]) -> int:
    """Executions of ``action_id`` in the thread state; also checks audit_log agrees."""
    executed = harness.outcome(thread_id)["executed_action_ids"]
    in_state = executed.count(action_id) if action_id else len(executed)
    in_db = db_executions(action_id)
    if in_db is not None and in_db != in_state:
        print(f"      state says {in_state} execution(s), audit_log says {in_db}")
        return max(in_state, in_db)
    return in_state


def _payload(harness: AgentHarness, thread_id: str) -> dict[str, Any]:
    return harness.approval_payload(thread_id) or {}


def _status(value: Any) -> Optional[str]:
    """ActionStatus enum or plain string -> "pending" / "approved" / "executed" / "rejected"."""
    return None if value is None else str(getattr(value, "value", value))


def phase_start(harness: AgentHarness, _: argparse.Namespace) -> int:
    c = Checks()
    thread_id = f"restart-{uuid.uuid4().hex[:12]}"
    waiting = harness.send(thread_id, golden_message(), user_id=USER)
    payload = _payload(harness, thread_id)
    action_id = payload.get("action_id")
    fingerprint = payload_fingerprint(payload) if payload else None
    print(f"THREAD={thread_id}\nACTION_ID={action_id}\nFINGERPRINT={fingerprint}")
    c.check("paused for approval", waiting == "approval", waiting)
    c.check("payload status pending", _status(payload.get("status")) == "pending",
            payload.get("status"))
    c.check("total within EUR 75,000 cap", float(payload.get("total_cost", 1e9)) <= 75000,
            payload.get("total_cost"))
    c.check("no execution before approval", count_executions(harness, thread_id, action_id) == 0)
    return c.result()


def phase_approve(harness: AgentHarness, args: argparse.Namespace) -> int:
    c = Checks()
    waiting = harness.pending(args.thread_id)
    payload = _payload(harness, args.thread_id)
    action_id = payload.get("action_id")
    c.check("still paused for approval after restart", waiting == "approval", waiting)
    if args.fingerprint:
        c.check("same approval payload after restart",
                payload and payload_fingerprint(payload) == args.fingerprint,
                payload and payload_fingerprint(payload))
    c.check("no execution while paused", count_executions(harness, args.thread_id, action_id) == 0)
    harness.decide(args.thread_id, approved=True)
    c.check("executed exactly once", count_executions(harness, args.thread_id, action_id) == 1)
    statuses = harness.outcome(args.thread_id).get("action_statuses") or {}
    c.check("status executed", _status(statuses.get(action_id)) == "executed",
            statuses.get(action_id))
    print(f"ACTION_ID={action_id}")
    return c.result()


def phase_verify(harness: AgentHarness, args: argparse.Namespace) -> int:
    c = Checks()
    outcome = harness.outcome(args.thread_id)
    executed = outcome["executed_action_ids"]
    action_id = executed[0] if executed else None
    c.check("thread finished after restart", harness.pending(args.thread_id) is None)
    c.check("one action executed", len(set(executed)) == 1, executed)
    for replay in ("approve again", "approve again (double click)", "resume finished thread"):
        try:
            if replay.startswith("approve"):
                harness.decide(args.thread_id, approved=True)
            else:
                harness.resume(args.thread_id)
        except Exception as exc:  # refusing the replay is fine; executing again is not
            print(f"      {replay}: refused ({type(exc).__name__})")
        c.check(f"still 1 execution after {replay}",
                count_executions(harness, args.thread_id, action_id) == 1)
    c.check("audit_log has exactly one executed row", db_executions(action_id) in (1, None),
            db_executions(action_id))
    return c.result()


def phase_crash(harness: AgentHarness, args: argparse.Namespace) -> int:
    """Run the case with SUPPLYGUARD_CRASH_AT set. The process should die inside the step."""
    os.environ[CRASH_ENV] = args.step
    thread_id = f"restart-{args.step}-{uuid.uuid4().hex[:8]}"
    print(f"THREAD={thread_id}", flush=True)
    waiting = harness.send(thread_id, golden_message(), user_id=USER)
    if args.step == "before_execute" and waiting == "approval":
        harness.decide(thread_id, approved=True)
    print(f"FAIL  process survived the kill point {args.step!r} (is {CRASH_ENV} implemented?)")
    print("RESULT: FAIL")
    return 1


def phase_resume(harness: AgentHarness, args: argparse.Namespace) -> int:
    c = Checks()
    os.environ.pop(CRASH_ENV, None)
    waiting = harness.resume(args.thread_id)
    if waiting == "approval" and args.expect == "executed":
        harness.decide(args.thread_id, approved=True)  # crash happened before approval landed
        waiting = harness.pending(args.thread_id)
    outcome = harness.outcome(args.thread_id)
    executed = outcome["executed_action_ids"]
    if args.expect == "approval":
        action_id = _payload(harness, args.thread_id).get("action_id")
        c.check("resumed to the approval pause", waiting == "approval", waiting)
        c.check("no execution", count_executions(harness, args.thread_id, action_id) == 0)
        c.check("exactly one payload pending",
                len({p.get("action_id") for p in outcome["approval_payloads"]}) == 1,
                [p.get("action_id") for p in outcome["approval_payloads"]])
    else:
        action_id = executed[0] if executed else None
        c.check("thread finished", waiting is None, waiting)
        c.check("executed exactly once", count_executions(harness, args.thread_id, action_id) == 1,
                executed)
    return c.result()


PHASES = {
    "start": phase_start,
    "approve": phase_approve,
    "verify": phase_verify,
    "crash": phase_crash,
    "resume": phase_resume,
}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--harness", help="module:factory, overrides $SUPPLYGUARD_EVAL_HARNESS")
    sub = parser.add_subparsers(dest="phase", required=True)
    sub.add_parser("start")
    p = sub.add_parser("approve")
    p.add_argument("thread_id")
    p.add_argument("--fingerprint", help="FINGERPRINT printed by start")
    sub.add_parser("verify").add_argument("thread_id")
    sub.add_parser("crash").add_argument("step", choices=KILL_STEPS[1:])
    p = sub.add_parser("resume")
    p.add_argument("thread_id")
    p.add_argument("--expect", choices=("approval", "executed"), required=True)
    args = parser.parse_args(argv)

    configure_tracing()
    try:
        harness = load_harness(args.harness)
    except HarnessUnavailable as exc:
        print(f"Cannot run the restart scenario: {exc}", file=sys.stderr)
        return 2
    return PHASES[args.phase](harness, args)


if __name__ == "__main__":
    sys.exit(main())
