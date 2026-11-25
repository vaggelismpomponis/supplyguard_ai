# Deep Agents Introduction
# Demonstrates creating and invoking a basic deep agent with custom system prompt.
# Shows how to access agent responses and inspect resulting state keys.

# messages	
# todos	
# files	
# subagent_results	
# skills

import os

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
agent = create_deep_agent(
    llm,
    system_prompt="You are a CodeHub support assistant. Answer directly from your own knowledge; you have no logs or files to check.",
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Draft a short reply telling a customer we refunded their duplicate charge."}]
})

# print(result)
# print(result["messages"][-1].content)
print(f"All State keys: {list(result.keys())}")
