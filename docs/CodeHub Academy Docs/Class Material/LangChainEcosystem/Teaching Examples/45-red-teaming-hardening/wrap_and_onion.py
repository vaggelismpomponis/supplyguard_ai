# Shows wrap_model_call and wrap_tool_call for full control around model/tool calls.
# Demonstrates the "onion model": before/after hooks run in list order, wraps nest around each other.
# Also shows async hooks for non-blocking I/O.

import asyncio
import os
import time

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")

_attempts = {"count": 0}


@tool
def flaky_lookup(order_id: str) -> str:
    """Look up an order -- fails on its first two calls, to demonstrate wrap_tool_call retries."""
    _attempts["count"] += 1
    if _attempts["count"] < 3:
        raise RuntimeError("temporary lookup service error")
    return f"Order {order_id}: shipped"


class RetryToolMiddleware(AgentMiddleware):
    # wrap_tool_call: retries a failed tool call with backoff - before/after hooks can't do this
    def wrap_tool_call(self, request, handler):
        for attempt in range(3):
            try:
                return handler(request)
            except Exception as exc:
                if attempt == 2:
                    raise
                print(f"  [retry] tool call failed ({exc}), attempt {attempt + 1}/3")
                time.sleep(2**attempt)


retry_agent = create_agent(llm, tools=[flaky_lookup], middleware=[RetryToolMiddleware()])
print("[wrap_tool_call retry]")
retry_result = retry_agent.invoke({"messages": [{"role": "user", "content": "Look up order O-9."}]})
print(retry_result["messages"][-1].content)


class OrderTracker(AgentMiddleware):
    # Labeled A/B/C to demonstrate execution order: before hooks in list order,
    # wraps nest, after hooks in REVERSE order
    def __init__(self, label: str):
        super().__init__()
        self.label = label

    def before_model(self, state, runtime):
        print(f"  before_model: {self.label}")
        return None

    def wrap_model_call(self, request, handler):
        print(f"  wrap_model_call START: {self.label}")
        result = handler(request)
        print(f"  wrap_model_call END:   {self.label}")
        return result

    def after_model(self, state, runtime):
        print(f"  after_model: {self.label}")
        return None


agent = create_agent(
    llm,
    tools=[],
    middleware=[OrderTracker("A"), OrderTracker("B"), OrderTracker("C")],
)

print("[onion model order]")
agent.invoke({"messages": [{"role": "user", "content": "Say hi in 3 words."}]})


class AsyncAuditMiddleware(AgentMiddleware):
    # Async hooks: "a" prefix for non-blocking I/O (logging, telemetry, etc)
    async def abefore_model(self, state, runtime):
        await asyncio.sleep(0)
        print("  [async] audited before model call")
        return None


async_agent = create_agent(llm, tools=[], middleware=[AsyncAuditMiddleware()])


async def main():
    print("\n[async hooks]")
    result = await async_agent.ainvoke({"messages": [{"role": "user", "content": "Say hi in 3 words."}]})
    print(result["messages"][-1].content)


asyncio.run(main())
