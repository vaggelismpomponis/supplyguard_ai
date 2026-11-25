"""Evaluation runner (#88), tracing config (#82) and dataset upload (#83), without the agent."""

import json

import pytest

import eval_fakes
from eval import run_eval, tracing, upload_dataset
from eval.harness import HarnessUnavailable, load_harness


@pytest.fixture
def reference_harness(monkeypatch):
    monkeypatch.setattr(eval_fakes, "build", eval_fakes.harness_for_dataset, raising=False)
    return "eval_fakes:build"


def test_full_run_with_a_correct_agent_passes(reference_harness, tmp_path, capsys):
    out = tmp_path / "results.json"
    assert run_eval.main(["--harness", reference_harness, "--out", str(out)]) == 0
    rows = json.loads(out.read_text())
    assert len(rows) == 99  # 105 cases minus 6 restart cases
    assert "99/99 cases pass every evaluator" in capsys.readouterr().out


def test_a_broken_case_is_reported_not_fatal(reference_harness, monkeypatch, capsys):
    original = eval_fakes.ReferenceHarness.outcome

    def broken(self, thread_id):
        if "EV-0002" in thread_id:
            raise RuntimeError("tool timeout")
        return original(self, thread_id)

    monkeypatch.setattr(eval_fakes.ReferenceHarness, "outcome", broken)
    code = run_eval.main(["--harness", reference_harness, "--only", "EV-0002", "--only", "EV-0003"])
    assert code == 1
    assert "run: RuntimeError: tool timeout" in capsys.readouterr().out


def test_missing_harness_exits_with_2(capsys):
    assert run_eval.main(["--harness", "src.agent.does_not_exist:build"]) == 2
    assert "Workflow provides it" in capsys.readouterr().err


def test_load_harness_rejects_objects_without_the_step_api(monkeypatch):
    monkeypatch.setattr(eval_fakes, "not_a_harness", lambda: object(), raising=False)
    with pytest.raises(HarnessUnavailable):
        load_harness("eval_fakes:not_a_harness")


def test_langsmith_adapter_reports_not_applicable_as_none():
    from types import SimpleNamespace

    from eval.evaluators import answer_grounding

    adapted = run_eval._langsmith_evaluator(answer_grounding)
    outcome, expected = eval_fakes.golden_outcome()
    result = adapted(SimpleNamespace(outputs=outcome), SimpleNamespace(outputs=expected))
    assert result == {"key": "answer_grounding", "score": None, "comment": "not applicable"}


def test_run_config_groups_traces_by_thread():
    config = tracing.run_config("thread-1", case_id="EV-0001", user_id="u-pm-01", tags=["evaluation"])
    assert config["configurable"] == {"thread_id": "thread-1"}
    assert config["metadata"] == {"thread_id": "thread-1", "case_id": "EV-0001", "user_id": "u-pm-01"}
    assert config["tags"] == ["supplyguard", "evaluation", "EV-0001"]


def test_tracing_stays_off_with_a_placeholder_key(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "your_langsmith_api_key_here")
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    settings = tracing.configure_tracing()
    assert settings["enabled"] is False
    assert settings["project"] == "supplyguard-ai"


def test_tracing_on_with_a_real_key(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_pt_test")
    assert tracing.configure_tracing()["enabled"] is True


def test_upload_dry_run_needs_no_network(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["upload_dataset", "--dry-run"])
    assert upload_dataset.main() == 0
    out = capsys.readouterr().out
    assert "Loaded 105 examples" in out and "supplyguard-eval-105" in out
