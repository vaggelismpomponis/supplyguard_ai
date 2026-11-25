# A support ticket workflow with 3 sequential steps: validate input, classify, summarize.

from typing import TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


class State(TypedDict):
    raw_text: str
    category: str | None
    summary: str | None


def validate(state: State) -> dict:
    """Node 1 -- no LLM. Reject/clean input before it reaches the model."""
    text = state["raw_text"].strip()
    if not text:
        raise ValueError("empty ticket text")
    return {"raw_text": text}


def classify(state: State) -> dict:
    """Node 2 -- one LLM call, writes only 'category'."""
    prompt = f"Classify this support ticket in one word (billing/bug/feature/other): {state['raw_text']!r}"
    return {"category": llm.invoke(prompt).content.strip().lower()}


def summarize(state: State) -> dict:
    """Node 3 -- another LLM call, reads 'category' + 'raw_text', writes only 'summary'."""
    prompt = f"In one short sentence, summarize this {state['category']} ticket: {state['raw_text']!r}"
    return {"summary": llm.invoke(prompt).content.strip()}


graph = StateGraph(State)

graph.add_node("validate", validate)
graph.add_node("classify", classify)
graph.add_node("summarize", summarize)

graph.add_edge(START, "validate")
graph.add_edge("validate", "classify")
graph.add_edge("classify", "summarize")
graph.add_edge("summarize", END)

app = graph.compile()

result = app.invoke(
    {
        "raw_text": "I was charged twice for my subscription this month",
        "category": None,
        "summary": None,
    }
)
print(result)


mermaid = app.get_graph().draw_mermaid()
with open("graph.md", "w", encoding="utf-8") as f:
    f.write("```mermaid\n")
    f.write(mermaid)
    f.write("\n```")

