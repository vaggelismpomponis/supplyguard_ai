"""Run the 105 held-out cases through the SupplyGuard agent and score them (#88).

Usage:
    python -m eval.run_eval                     # local run, score table per category
    python -m eval.run_eval -v                  # also show pauses and failure reasons
    python -m eval.run_eval --only EV-0001      # one case (repeatable)
    python -m eval.run_eval --out results.json  # save every outcome and score
    python -m eval.run_eval --langsmith         # LangSmith experiment on the uploaded dataset

The agent is reached through eval/harness.py. Each case runs on a fresh thread; a case with a
``context`` (follow-ups, policy cases) first replays that context case on the same thread with
its approval left pending. ``restart_recovery`` cases are run by eval.restart_scenario instead.

Exit code 0 only when every applicable evaluator passes on every case that ran.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from eval.dataset import load_examples
from eval.evaluators import ALL_EVALUATORS, EVALUATOR_KEYS, evaluate
from eval.harness import AgentHarness, HarnessUnavailable, drive, load_harness
from eval.tracing import configure_tracing


def run_case(
    harness: AgentHarness,
    example: dict[str, Any],
    examples_by_id: dict[str, dict[str, Any]],
    *,
    thread_id: Optional[str] = None,
) -> tuple[dict[str, Any], list[str]]:
    """Run one example (and its context case first). Returns the outcome and a short log."""
    inputs = example["inputs"]
    thread_id = thread_id or f"eval-{inputs['case_id']}-{uuid.uuid4().hex[:8]}"
    log: list[str] = []
    if inputs.get("context"):
        ctx = examples_by_id[inputs["context"]]["inputs"]
        log.append(f"context {ctx['case_id']}")
        log += drive(harness, thread_id, ctx["message"], user_id=inputs["user_id"])
    log += drive(
        harness,
        thread_id,
        inputs["message"],
        user_id=inputs["user_id"],
        clarification_reply=inputs.get("clarification_reply"),
        approval_decision=inputs.get("approval_decision"),
    )
    return dict(harness.outcome(thread_id)), log


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[int]]]:
    """category -> evaluator -> [passed, applicable]."""
    table: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row in rows:
        for r in row["results"]:
            cell = table[row["category"]][r["key"]]
            cell[0] += r["score"]
            cell[1] += 1
    return table


def print_table(table: dict[str, dict[str, list[int]]], cases: dict[str, list[int]]) -> None:
    short = {k: k.split("_")[0][:10] for k in EVALUATOR_KEYS}
    print(f"\n{'category':<26}{'cases':>8}  " + "".join(f"{short[k]:>12}" for k in EVALUATOR_KEYS))
    for category in sorted(table):
        passed, total = cases[category]
        cells = []
        for key in EVALUATOR_KEYS:
            p, n = table[category].get(key, [0, 0])
            cells.append(f"{f'{p}/{n}' if n else '-':>12}")
        print(f"{category:<26}{f'{passed}/{total}':>8}  " + "".join(cells))


def run_local(args: argparse.Namespace) -> int:
    try:
        harness = load_harness(args.harness)
    except HarnessUnavailable as exc:
        print(f"Cannot run the evaluation: {exc}", file=sys.stderr)
        return 2

    examples = load_examples()
    by_id = {e["metadata"]["id"]: e for e in examples}
    selected = [by_id[i] for i in args.only] if args.only else examples
    rows, cases = [], defaultdict(lambda: [0, 0])
    skipped = 0

    for example in selected:
        case_id, category = example["metadata"]["id"], example["metadata"]["category"]
        if example["metadata"]["harness_only"]:
            skipped += 1
            continue
        try:
            outcome, log = run_case(harness, example, by_id)
            results = evaluate(outcome, example["outputs"])
            error = None
        except Exception as exc:  # one broken case must not stop the run
            outcome, log, error = {}, [], f"{type(exc).__name__}: {exc}"
            results = [{"key": "run", "score": 0, "comment": error}]
        ok = all(r["score"] for r in results)
        cases[category][0] += ok
        cases[category][1] += 1
        rows.append({"case_id": case_id, "category": category, "results": results,
                     "log": log, "outcome": outcome, "error": error})
        if args.verbose or not ok:
            print(f"{case_id} {category:<24} {'PASS' if ok else 'FAIL'}")
        if args.verbose:
            for line in log:
                print(f"    · {line}")
        for r in results:
            if not r["score"]:
                print(f"    ✗ {r['key']}: {r['comment']}")

    print_table(summarize(rows), cases)
    passed = sum(p for p, _ in cases.values())
    print(f"\n{passed}/{len(rows)} cases pass every evaluator"
          f" ({skipped} restart cases left to eval.restart_scenario)")
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
        print(f"Saved {len(rows)} rows to {args.out}")
    return 0 if passed == len(rows) else 1


def _langsmith_evaluator(fn):
    """Adapt an evaluator to LangSmith's (run, example) signature; n/a becomes score None."""

    def wrapper(run, example) -> dict:
        result = fn(run.outputs, example.outputs)
        return result or {"key": fn.__name__, "score": None, "comment": "not applicable"}

    wrapper.__name__ = fn.__name__
    return wrapper


def run_langsmith(args: argparse.Namespace) -> int:
    from langsmith import evaluate as langsmith_evaluate

    from eval.upload_dataset import dataset_name

    if not configure_tracing()["enabled"]:
        print("LangSmith is not configured (LANGSMITH_TRACING, LANGSMITH_API_KEY).", file=sys.stderr)
        return 1
    try:
        harness = load_harness(args.harness)
    except HarnessUnavailable as exc:
        print(f"Cannot run the evaluation: {exc}", file=sys.stderr)
        return 2
    by_id = {e["metadata"]["id"]: e for e in load_examples()}

    def target(inputs: dict) -> dict:
        example = by_id[inputs["case_id"]]
        if example["metadata"]["harness_only"]:
            return {"skipped": "restart case, see eval.restart_scenario"}
        outcome, log = run_case(harness, example, by_id)
        return outcome | {"log": log}

    results = langsmith_evaluate(
        target,
        data=dataset_name(),
        evaluators=[_langsmith_evaluator(fn) for fn in ALL_EVALUATORS],
        experiment_prefix="supplyguard-eval",
        description="SupplyGuard Deep Agent on the 105 held-out cases",
        metadata={"harness": args.harness or "default"},
        max_concurrency=1,
    )
    print(f"Experiment: {results.experiment_name}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-v", "--verbose", action="store_true", help="show pauses and failures")
    parser.add_argument("--only", action="append", metavar="CASE_ID", help="run only this case")
    parser.add_argument("--out", help="save outcomes and scores as JSON")
    parser.add_argument("--harness", help="module:factory, overrides $SUPPLYGUARD_EVAL_HARNESS")
    parser.add_argument("--langsmith", action="store_true", help="run as a LangSmith experiment")
    args = parser.parse_args(argv)
    configure_tracing()
    return run_langsmith(args) if args.langsmith else run_local(args)


if __name__ == "__main__":
    sys.exit(main())
