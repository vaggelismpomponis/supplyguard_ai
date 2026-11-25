# Uses LLM-as-judge with structured output to evaluate answers semantically.
# Shows position bias: when comparing answers, their order can flip the verdict.
# Solution: test both orderings to avoid bias.

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


class Judgment(BaseModel):
    passed: bool = Field(description="True if the answer correctly states the refund timeline is 3-5 business days")
    reasoning: str = Field(description="One sentence explaining the verdict")


def judge(candidate_answer: str) -> Judgment:
    prompt = (
        "Judge this candidate answer against the rubric below. Be strict about factual "
        "correctness, but don't penalize different wording of the same fact.\n\n"
        f"Rubric: the answer must state CodeHub's refund timeline is 3-5 business days.\n"
        f"Candidate answer: {candidate_answer!r}"
    )
    return llm.with_structured_output(Judgment, method="function_calling").invoke(prompt)



candidate = llm.invoke("In one sentence, what's CodeHub's refund timeline?").content
verdict = judge(candidate)
print(f"[judge] passed={verdict.passed}  reasoning={verdict.reasoning}")


class Preference(BaseModel):
    winner: str = Field(description="Exactly 'A' or 'B'")
    reasoning: str = Field(description="One sentence")


answer_concise = "3-5 business days."
answer_verbose = (
    "Great question! At CodeHub we take refunds very seriously, and our dedicated billing team "
    "works hard to process every request as quickly as possible, which typically takes 3-5 business days."
)


def judge_pair(first: str, second: str) -> Preference:
    prompt = (
        "Which answer better addresses 'What's CodeHub's refund timeline?', considering both "
        f"accuracy and conciseness?\nA: {first!r}\nB: {second!r}"
    )
    return llm.with_structured_output(Preference, method="function_calling").invoke(prompt)


order1 = judge_pair(answer_concise, answer_verbose)
order2 = judge_pair(answer_verbose, answer_concise)  # same two answers, swapped positions

print(f"\n[concise=A, verbose=B] winner={order1.winner} ({order1.reasoning})")
print(f"[verbose=A, concise=B] winner={order2.winner} ({order2.reasoning})")
print(
    "If the 'winning' answer's content flips between these two calls just because of A/B "
    "position, that's position bias -- always alternate/average over both orderings, never "
    "trust a single-order pairwise judgment."
)
