# Multi-step content generation: outline → draft → polish.
# Each step builds on the previous one.

from typing import TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


class State(TypedDict):
    topic: str
    outline: str | None
    draft: str | None
    polished: str | None


def outline(state: State) -> dict:
    """Step 1: a bare-bones outline -- the smallest useful first draft."""
    prompt = f"Give a 3-bullet outline (no prose) for a help-center article about: {state['topic']}"
    return {"outline": llm.invoke(prompt).content}


def draft(state: State) -> dict:
    """Step 2: expand the outline into full sentences. Depends on step 1's output."""
    prompt = f"Expand this outline into a short article (3 short paragraphs):\n{state['outline']}"
    return {"draft": llm.invoke(prompt).content}


def polish(state: State) -> dict:
    """Step 3: tighten tone/wording. Depends on step 2's output."""
    prompt = f"Rewrite this in a friendlier, more concise tone, same content:\n{state['draft']}"
    return {"polished": llm.invoke(prompt).content}


graph = StateGraph(State)

graph.add_node("outline", outline)
graph.add_node("draft", draft)
graph.add_node("polish", polish)

graph.add_edge(START, "outline")
graph.add_edge("outline", "draft")
graph.add_edge("draft", "polish")
graph.add_edge("polish", END)

app = graph.compile()

result = app.invoke(
    {
        "topic": "resetting your CodeHub password",
        "outline": None,
        "draft": None,
        "polished": None,
    }
)
print(result["polished"])
