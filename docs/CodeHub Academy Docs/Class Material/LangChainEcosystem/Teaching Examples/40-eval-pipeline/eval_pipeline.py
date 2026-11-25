# Complete eval pipeline: labeled dataset → run agent → judge each result → aggregate pass rate.
# This is what a CI eval gate looks like for agent quality (equivalent to pytest for code).

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")

DATASET = [
    {"question": "What's CodeHub's refund timeline?", "rubric": "States the refund timeline is 3-5 business days."},
    {"question": "What's CodeHub's uptime guarantee?", "rubric": "States a 99.9% monthly uptime guarantee."},
    {"question": "What's the SLA for critical bugs?", "rubric": "States critical bugs get a 1 hour response time."},
]


class Judgment(BaseModel):
    passed: bool = Field(description="True only if the answer satisfies the rubric")
    reasoning: str = Field(description="One sentence")


def run_agent(question: str) -> str:
    return llm.invoke(question).content


def judge(question: str, answer: str, rubric: str) -> Judgment:
    prompt = f"Question: {question!r}\nAnswer: {answer!r}\nRubric: {rubric!r}\nDoes the answer satisfy the rubric?"
    return llm.with_structured_output(Judgment, method="function_calling").invoke(prompt)


results = []
for case in DATASET:
    answer = run_agent(case["question"])
    verdict = judge(case["question"], answer, case["rubric"])
    results.append({"question": case["question"], "answer": answer, "passed": verdict.passed, "reasoning": verdict.reasoning})

for r in results:
    status = "PASS" if r["passed"] else "FAIL"
    print(f"[{status}] {r['question']}")
    print(f"       answer: {r['answer']}")
    print(f"       reason: {r['reasoning']}")

pass_rate = sum(r["passed"] for r in results) / len(results)
print(f"\nPass rate: {pass_rate:.0%} ({sum(r['passed'] for r in results)}/{len(results)})")
