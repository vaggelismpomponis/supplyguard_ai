# Context Management with Middleware
# Demonstrates filesystem and summarization middleware to manage token usage.
# Shows how to automatically evict files and summarize conversation history.

import os

from deepagents.middleware.filesystem import FilesystemMiddleware
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


@tool
def fetch_full_error_log() -> str:
    """Fetch the full error log."""
    return "ERROR: connection refused\n" * 500


agent = create_agent(
    llm,
    tools=[fetch_full_error_log],
    middleware=[
        # Automatically evict files from context when token limit reached
        FilesystemMiddleware(tool_token_limit_before_evict=200),
        # Summarize conversation when it exceeds 6 messages, keeping the latest 2
        SummarizationMiddleware(
            model=llm, trigger=("messages", 6), keep=("messages", 2)
        ),
    ],
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Fetch the full error log and summarize it in one sentence.",
            }
        ]
    }
)

print(result["messages"][-1].content)
print("\nFiles after the run:", list(result.get("files", {}).keys()))
