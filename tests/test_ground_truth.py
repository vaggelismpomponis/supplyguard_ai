"""#78: the Knowledge tools reproduce the ground truth of the held-out evaluation cases.

The 64 extraction_and_impact cases of eval_cases.jsonl state, per component, the affected products
and the open customer orders due within 60 days. Quality's evaluators compare the agent against
these numbers, so the tools the agent calls must return exactly them. Mock tests read the CSVs;
the tool test needs DATABASE_URL with the tables loaded (it loads them itself).
"""
import json
import os

import pytest

from src.knowledge import mocks
from src.knowledge.ingest_documents import DOCUMENTS

CASES = [
    c for c in map(json.loads, (DOCUMENTS.parent / "evaluation" / "eval_cases.jsonl").read_text(encoding="utf-8").splitlines())
    if "affected_products" in c["expected"]
]


def impact(bom):
    return [p.product_id for p in bom.products], len(bom.open_orders)


def expected(case):
    e = case["expected"]
    return sorted(e["affected_products"]), e["open_orders_due_within_60d"]


def test_all_impact_cases_are_covered():
    assert len(CASES) == 64


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_mock_bom_matches_eval_ground_truth(case):
    assert impact(mocks.query_bom(case["expected"]["component_id"])) == expected(case)


@pytest.mark.skipif("DATABASE_URL" not in os.environ, reason="no Postgres")
def test_tool_bom_matches_eval_ground_truth():
    from src.knowledge import load_structured, tools

    load_structured.load()
    wrong = [c["id"] for c in CASES if impact(tools.query_bom(c["expected"]["component_id"])) != expected(c)]
    assert not wrong
