# Common agent utilities: reusable across all examples.
# Standard ticket triage workflow (classify → reply).

from typing import TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


class State(TypedDict):
    ticket: str
    category: str | None
    reply: str | None


def classify(state: State) -> dict:
    """Classify ticket by category."""
    return {
        "category": llm.invoke(
            f"One word category (billing/bug/general): {state['ticket']!r}"
        ).content.strip()
    }


def reply(state: State) -> dict:
    """Draft a reply based on category."""
    prompt = (
        f"Write a short reply to this {state['category']} ticket: {state['ticket']!r}"
    )
    return {"reply": llm.invoke(prompt).content}


def build_graph():
    """Build and compile the standard ticket triage graph."""
    graph = StateGraph(State)
    graph.add_node("classify", classify)
    graph.add_node("reply", reply)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "reply")
    graph.add_edge("reply", END)
    return graph.compile()
