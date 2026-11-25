import pytest


def pytest_addoption(parser):
    parser.addoption("--postgres", action="store_true", help="Run real Postgres tests")


@pytest.fixture(autouse=True)
def disable_remote_tracing(monkeypatch):
    # Tests never upload traces, even if the parent shell enables them.
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
