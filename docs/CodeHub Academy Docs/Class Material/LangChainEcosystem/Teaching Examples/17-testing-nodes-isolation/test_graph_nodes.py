# Unit tests for graph_nodes.py: mock the LLM and test node behavior in isolation.

from unittest.mock import MagicMock

import graph_nodes
import pytest


@pytest.fixture
def mock_llm(monkeypatch):
    fake_llm = MagicMock()
    monkeypatch.setattr(graph_nodes, "llm", fake_llm)
    return fake_llm


@pytest.mark.parametrize(
    "llm_response,expected_category",
    [
        ("Billing", "billing"),
        ("BILLING", "billing"),
        ("Bug", "bug"),
        ("BUG", "bug"),
        ("General", "general"),
        ("GENERAL", "general"),
    ],
)
def test_classify_normalizes_response(mock_llm, llm_response, expected_category):

    mock_llm.invoke.return_value.content = llm_response

    result = graph_nodes.classify({"ticket": "I was charged twice"})

    assert result == {"category": expected_category}
    mock_llm.invoke.assert_called_once()


def test_classify_calls_llm_with_ticket(mock_llm):
    mock_llm.invoke.return_value.content = "Billing"
    ticket = "I was charged twice"

    graph_nodes.classify({"ticket": ticket})

    prompt_sent, *_ = mock_llm.invoke.call_args.args
    assert ticket in str(prompt_sent)
