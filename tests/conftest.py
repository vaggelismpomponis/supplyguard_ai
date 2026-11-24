"""Shared test setup."""

import pytest


@pytest.fixture(autouse=True)
def no_live_llm(monkeypatch):
    """Keep unit/integration tests deterministic and free: never call a real chat model."""
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("OFFLINE_MODE", "true")
