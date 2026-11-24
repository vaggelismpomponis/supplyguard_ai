"""Tests for the SupplyGuard AgentHarness (src/agent/eval_harness.py)."""

from __future__ import annotations

import uuid

from eval.dataset import load_examples
from eval.evaluators import evaluate
from eval.harness import AgentHarness, drive
from src.agent.deep_agent import SupplyGuardOrchestrator
from src.agent.eval_harness import SupplyGuardEvalHarness, build_harness


def test_build_harness_satisfies_protocol():
    h = build_harness()
    assert isinstance(h, AgentHarness)


def test_eval_harness_golden_and_idempotency():
    h = SupplyGuardEvalHarness(orchestrator=SupplyGuardOrchestrator(use_postgres=False))
    examples = {e["metadata"]["id"]: e for e in load_examples()}
    golden = examples["EV-0001"]
    tid = f"test-harness-gold-{uuid.uuid4().hex[:8]}"

    drive(
        h,
        tid,
        golden["inputs"]["message"],
        user_id=golden["inputs"]["user_id"],
        approval_decision="approved",
    )
    # Replay decide should be a no-op
    assert h.decide(tid, approved=True) is None

    outcome = h.outcome(tid)
    results = evaluate(outcome, golden["outputs"])
    assert all(r["score"] == 1 for r in results), results
    assert len(outcome["executed_action_ids"]) == 1
