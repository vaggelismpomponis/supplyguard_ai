"""Pre-demo check (#91): every demo message still gives what docs/DEMO_SCRIPT.md promises.

Run inside the app container against the seeded stack, at T-30 min:

    docker compose exec -T app python -m eval.demo_check

The messages are typed exactly as in the script, on one thread, as the procurement manager. The
approval is left pending: the check never creates a purchase order (the live demo does that after
the restart in segment 5). Exits with 0 only when every step passes.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from eval.dataset import GOLDEN_ID, load_examples
from eval.evaluators import evaluate
from eval.harness import AgentHarness, HarnessUnavailable, load_harness
from eval.tracing import configure_tracing

AMBIGUOUS_OPENING = "Atlas says the motor board is late."
CLARIFICATION_REPLY = (
    "Atlas Components (S001), component MC-17, PO-2026-9001. They announced a 12-day delay. "
    "Additional spending must not exceed €75,000. Do not create a purchase order without approval."
)


@dataclass(frozen=True)
class DemoStep:
    segment: str
    message: str
    kind: str  # "send" (new message) or "reply" (answer to the clarification question)
    waits_for: Optional[str]  # expected pause after the step: "clarification", "approval", None
    evaluators: tuple[str, ...] = ()  # evaluator keys that must pass after the step
    expected_overrides: dict[str, Any] = field(default_factory=dict)


DEMO_STEPS: tuple[DemoStep, ...] = (
    DemoStep("2a ambiguous opening", AMBIGUOUS_OPENING, "send", "clarification"),
    DemoStep(
        "2b clarification answered -> investigation -> approval card",
        CLARIFICATION_REPLY,
        "reply",
        "approval",
        ("numerical_correctness", "policy_constraints", "dependency_risk", "injection_defense",
         "human_approval_integrity"),
    ),
    DemoStep(
        "6a follow-up: Helios",
        "Why did you reject Supplier Helios?",
        "send",
        "approval",
        ("answer_grounding", "human_approval_integrity"),
        {"answer_must_mention": [["21"], ["1,500", "1500", "capacity", "lead time"]]},
    ),
    DemoStep(
        "6b follow-up: EUR 90,000",
        "What changes if we increase the spending limit to EUR 90,000?",
        "send",
        "approval",
        ("answer_grounding", "human_approval_integrity"),
        {"answer_must_mention": [["90,000", "90000", "90k"], ["finance director"]],
         "requires_calculator": True},
    ),
)


def golden_expected() -> dict[str, Any]:
    golden = next(e for e in load_examples() if e["metadata"]["id"] == GOLDEN_ID)
    # The demo leaves the approval pending, so nothing may execute during the check.
    return golden["outputs"] | {"should_execute": False}


def run_step(harness: AgentHarness, thread_id: str, step: DemoStep) -> list[str]:
    """Run one step on the demo thread and return the problems (empty list = pass)."""
    if step.kind == "reply":
        waiting = harness.reply(thread_id, step.message)
    else:
        waiting = harness.send(thread_id, step.message, user_id="u-pm-01")
    problems = []
    if waiting != step.waits_for:
        problems.append(f"waits for {waiting!r}, expected {step.waits_for!r}")
    if step.evaluators:
        expected = golden_expected() | step.expected_overrides
        if "answer_must_mention" in step.expected_overrides:
            expected.pop("golden", None)  # follow-ups are judged on their own answer
        results = {r["key"]: r for r in evaluate(harness.outcome(thread_id), expected)}
        for key in step.evaluators:
            r = results.get(key)
            if r is None:
                problems.append(f"{key}: not applicable to the outcome")
            elif not r["score"]:
                problems.append(f"{key}: {r['comment']}")
    return problems


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--harness", help="module:factory, overrides $SUPPLYGUARD_EVAL_HARNESS")
    args = parser.parse_args(argv)
    configure_tracing()
    try:
        harness = load_harness(args.harness)
    except HarnessUnavailable as exc:
        print(f"Cannot run the demo check: {exc}", file=sys.stderr)
        return 2
    thread_id = f"demo-check-{uuid.uuid4().hex[:8]}"
    failed = 0
    for step in DEMO_STEPS:
        problems = run_step(harness, thread_id, step)
        failed += bool(problems)
        print(f"{'PASS' if not problems else 'FAIL'}  {step.segment}")
        for p in problems:
            print(f"      ✗ {p}")
    print(f"RESULT: {'PASS' if not failed else 'FAIL'}  (thread {thread_id}, approval left pending)")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
