# Sandboxed Execution with Human Approval
# Creates an agent that can execute shell commands in an isolated sandbox directory.
# Agent execution is paused for human approval before running shell commands.

import os
import tempfile

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
# Create isolated temporary directory for shell command execution
sandbox_root = tempfile.mkdtemp(prefix="codehub-agent-sandbox-")
backend = LocalShellBackend(root_dir=sandbox_root)

agent = create_deep_agent(
    llm,
    backend=backend,
    system_prompt="You are a CodeHub dev assistant that can run shell commands in a scratch directory.",
    interrupt_on={"execute": {"allowed_decisions": ["approve", "reject"]}},
    checkpointer=MemorySaver(),
)

config = {"configurable": {"thread_id": "sandbox-demo"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Run `echo hello` and tell me the output."}]},
    config,
)
# Check if agent execution was interrupted and awaiting approval
if "__interrupt__" in result:
    pending = result["__interrupt__"][0].value
    print("Paused for approval:", pending)
    result = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config)

print(result["messages"][-1].content)
