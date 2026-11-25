"""Restart scenario phases (#90) against a reference harness whose state survives "restarts".

The live run against Docker is in docs/RESTART_TEST_SCENARIO.md. Here, a restart is simulated by
building a new harness instance over the same persisted store, as a new process would do.
"""

import re

import pytest

import eval_fakes
from eval import restart_scenario

STORE: dict = {}


def build_persistent():
    """A new process: fresh harness object, same persisted threads."""
    return eval_fakes.ReferenceHarness(eval_fakes.harness_for_dataset().expected_by_message, STORE)


@pytest.fixture(autouse=True)
def fresh_store(monkeypatch):
    STORE.clear()
    monkeypatch.setattr(eval_fakes, "build_persistent", build_persistent, raising=False)
    monkeypatch.setattr(restart_scenario, "db_executions", lambda action_id: None)


def run(*args, capsys):
    code = restart_scenario.main(["--harness", "eval_fakes:build_persistent", *args])
    return code, capsys.readouterr().out


def printed(name, out):
    return re.search(rf"^{name}=(\S+)$", out, re.M).group(1)


def test_restart_while_pending_then_approve_and_verify(capsys):
    code, out = run("start", capsys=capsys)
    assert code == 0, out
    thread, fingerprint = printed("THREAD", out), printed("FINGERPRINT", out)

    code, out = run("approve", thread, "--fingerprint", fingerprint, capsys=capsys)
    assert code == 0, out
    code, out = run("verify", thread, capsys=capsys)
    assert code == 0, out
    assert "still 1 execution after approve again (double click)" in out


def test_changed_payload_after_restart_is_caught(capsys):
    _, out = run("start", capsys=capsys)
    thread = printed("THREAD", out)
    STORE[thread]["payloads"][-1]["quantity"] = 6000
    code, out = run("approve", thread, "--fingerprint", printed("FINGERPRINT", out), capsys=capsys)
    assert code == 1
    assert "FAIL  same approval payload after restart" in out


def test_duplicate_execution_on_replay_is_caught(capsys, monkeypatch):
    _, out = run("start", capsys=capsys)
    thread = printed("THREAD", out)
    run("approve", thread, capsys=capsys)

    def leaky_decide(self, thread_id, *, approved):  # executes again on every replay
        self.threads[thread_id]["executed"].append(self.threads[thread_id]["payloads"][-1]["action_id"])

    monkeypatch.setattr(eval_fakes.ReferenceHarness, "decide", leaky_decide)
    code, out = run("verify", thread, capsys=capsys)
    assert code == 1
    assert "FAIL  still 1 execution after approve again" in out


def test_crash_phase_fails_when_the_kill_point_is_not_implemented(capsys):
    code, out = run("crash", "after_graph_query", capsys=capsys)
    assert code == 1
    assert "process survived the kill point" in out


def test_resume_after_crash_before_approval(capsys):
    _, out = run("start", capsys=capsys)
    code, out = run("resume", printed("THREAD", out), "--expect", "approval", capsys=capsys)
    assert code == 0, out


def test_audit_log_disagreeing_with_state_counts_as_duplicate(monkeypatch, capsys):
    _, out = run("start", capsys=capsys)
    thread = printed("THREAD", out)
    monkeypatch.setattr(restart_scenario, "db_executions", lambda action_id: 2 if action_id else 0)
    code, out = run("approve", thread, capsys=capsys)
    assert code == 1
    assert "audit_log says 2" in out
