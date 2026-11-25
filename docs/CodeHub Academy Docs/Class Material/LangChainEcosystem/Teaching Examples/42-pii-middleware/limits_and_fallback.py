# Demonstrates operational safety middleware: call limits, model fallbacks, and tool filtering.
# ToolCallLimitMiddleware/ModelCallLimitMiddleware prevent runaway loops.
# ModelFallbackMiddleware auto-switches to backup model on failure.
# LLMToolSelectorMiddleware pre-filters available tools for large agent systems.

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import (
    LLMToolSelectorMiddleware,
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
backup_llm = ChatAnthropic(model="claude-haiku-4-5")


@tool
def get_weather(city: str) -> str:
    """Return the current weather for a city."""
    return f"{city}: sunny, 27C"


@tool
def get_stock_price(ticker: str) -> str:
    """Return the current price of a stock ticker."""
    return f"{ticker}: $192.31"


capped_agent = create_agent(
    llm,
    tools=[get_weather],
    middleware=[
        ToolCallLimitMiddleware(max_calls=1),
        ModelCallLimitMiddleware(max_calls=3),
    ],
)
result = capped_agent.invoke({"messages": [{"role": "user", "content": "What's the weather in Athens?"}]})
print("[capped]", result["messages"][-1].content)

broken_llm = ChatAnthropic(model="this-model-does-not-exist", max_retries=0)
fallback_agent = create_agent(
    broken_llm,
    tools=[get_weather],
    middleware=[ModelFallbackMiddleware(fallback_models=[backup_llm])],
)
result = fallback_agent.invoke({"messages": [{"role": "user", "content": "What's the weather in Rhodes?"}]})
print("[fallback]", result["messages"][-1].content)

selector_agent = create_agent(
    llm,
    tools=[get_weather, get_stock_price],
    middleware=[LLMToolSelectorMiddleware(model=llm, max_tools=1)],
)
result = selector_agent.invoke({"messages": [{"role": "user", "content": "What's AAPL trading at?"}]})
print("[tool selector]", result["messages"][-1].content)
