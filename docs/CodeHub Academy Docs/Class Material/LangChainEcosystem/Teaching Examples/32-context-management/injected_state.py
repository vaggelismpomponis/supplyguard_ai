# Injected State in Tools
# Demonstrates how tools can access and use the agent state via InjectedState annotation.
# The count_conversation_turns tool uses injected state to count messages in the conversation.

import os
from typing import Annotated

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


@tool
def count_conversation_turns(state: Annotated[dict, InjectedState]) -> str:
    """Count the number of conversation turns so far."""
    return f"{len(state['messages'])} messages so far."


agent = create_agent(llm, tools=[count_conversation_turns])

result = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello! How can I help?"},
            {"role": "user", "content": "How many messages have we exchanged?"},
        ]
    }
)
print(result["messages"][-1].content)
