# Agent Middleware Classes
# Demonstrates custom middleware for rate limiting, adding tools, and managing agent state.
# Shows how to intercept and modify agent execution at different lifecycle points.

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from typing_extensions import TypedDict

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


class RateLimitMiddleware(AgentMiddleware):
    """Limits the number of model calls to prevent excessive API usage."""

    def __init__(self, max_calls: int = 5):
        super().__init__()
        self.max_calls = max_calls

    def before_model(self, state, runtime):
        """Check and increment model call count before each invocation."""
        call_count = state.get("model_call_count", 0)
        if call_count >= self.max_calls:
            raise RuntimeError("Model call limit exceeded.")
        return {"model_call_count": call_count + 1}


class NotesMiddleware(AgentMiddleware):
    """Provides a save_note tool for the agent."""

    @tool
    def save_note(note: str) -> str:
        """Save a note."""
        return f"Saved: {note}"

    tools = [save_note]


class UserProfileState(TypedDict):
    """State schema for user profile information."""
    user_name: str


class UserProfileMiddleware(AgentMiddleware):
    """Injects user profile data into agent state."""

    state_schema = UserProfileState

    def before_agent(self, state, runtime):
        """Set user name in state before agent starts."""
        return {"user_name": "Maria"}


agent = create_agent(
    llm,
    tools=[],
    middleware=[
        RateLimitMiddleware(max_calls=3),
        NotesMiddleware(),
        UserProfileMiddleware(),
    ],
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Save a note that says 'call the customer back'.",
            }
        ]
    }
)
print("[reply]", result["messages"][-1].content)
print(
    "[state beyond messages]",
    {k: v for k, v in result.items() if k not in ("messages",)},
)
