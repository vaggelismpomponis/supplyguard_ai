# Agent Skills
# Demonstrates how agents can use pre-defined skills from the filesystem.
# Skills are modular, reusable sets of instructions and tools for specialized tasks.

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
# Use filesystem backend to load skills from local directory
backend = FilesystemBackend(root_dir=Path(__file__).parent)

agent = create_deep_agent(
    llm,
    backend=backend,
    skills=["/skills/ticket-triage/"],
    system_prompt="You are a CodeHub support triage assistant.",
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "I was charged twice for my subscription this month."}]
})
print(result["messages"][-1].content)
