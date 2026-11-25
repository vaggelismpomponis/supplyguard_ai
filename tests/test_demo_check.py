"""Pre-demo check (#91) against the reference harness: every demo step passes."""

import eval_fakes
from eval import demo_check


def build_demo_harness():
    # The clarification answer carries the MC-17 facts, so a correct agent runs the golden case.
    golden = demo_check.golden_expected()
    return eval_fakes.harness_for_dataset({demo_check.CLARIFICATION_REPLY: golden})


def test_every_demo_step_passes(monkeypatch, capsys):
    monkeypatch.setattr(eval_fakes, "build_demo_harness", build_demo_harness, raising=False)
    assert demo_check.main(["--harness", "eval_fakes:build_demo_harness"]) == 0
    out = capsys.readouterr().out
    passed = [line for line in out.splitlines() if line.startswith("PASS  ")]
    assert len(passed) == len(demo_check.DEMO_STEPS)
    assert "approval left pending" in out


def test_demo_messages_match_the_script():
    from pathlib import Path

    script = Path(demo_check.__file__).resolve().parents[1] / "docs" / "DEMO_SCRIPT.md"
    text = script.read_text(encoding="utf-8")
    for step in demo_check.DEMO_STEPS:
        assert step.message in text, f"{step.segment}: message not in DEMO_SCRIPT.md"
