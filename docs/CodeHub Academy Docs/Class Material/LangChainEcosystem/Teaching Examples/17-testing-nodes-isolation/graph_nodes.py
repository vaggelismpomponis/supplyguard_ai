# Node function for testing: plain Python function that classifies tickets.
# Nodes are testable in isolation without building the full graph.

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


def classify(state: dict) -> dict:
    """Reads 'ticket', writes only 'category' -- same shape as a real graph node."""
    category = (
        llm.invoke(f"Classify as billing/bug/general: {state['ticket']!r}")
        .content.strip()
        .lower()
    )
    return {"category": category}
