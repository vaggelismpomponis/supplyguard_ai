# Async Streaming Patterns
# Demonstrates asynchronous agent invocation and streaming updates.
# Shows how to handle agent execution with async/await and stream real-time updates.

import asyncio

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


@tool
def search_docs(query: str) -> str:
    """Search documentation for a query."""
    return "Refunds are issued within 30 days of purchase."


agent = create_deep_agent(
    llm, tools=[search_docs], system_prompt="Answer using search_docs when relevant."
)


async def run_async():
    """Execute agent asynchronously and print the final response."""
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What's our refund window?"}]}
    )
    print("[ainvoke]", result["messages"][-1].content)


asyncio.run(run_async())

# Stream updates showing which nodes are executing
print("\n[stream updates]")
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What's our refund window?"}]},
    stream_mode="updates",
):
    for node_name, _ in chunk.items():
        print(f"  -- {node_name} --")
