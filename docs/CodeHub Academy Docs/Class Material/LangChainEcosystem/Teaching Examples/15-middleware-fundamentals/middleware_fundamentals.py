# Middleware hooks for agent lifecycle: before/after agent and model calls.
# Enables logging, monitoring, and intervention at every step.

import logging

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import (
    after_agent,
    after_model,
    before_agent,
    before_model,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(name)-10s] %(message)s")
logger = logging.getLogger("middleware")

llm = ChatAnthropic(model="claude-haiku-4-5")


@tool
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"


@before_agent
def before_agent_middleware(state, _):
    """Log when agent execution begins."""
    logger.info("agent starting")
    return {}


@before_model
def before_model_middleware(state, _):
    """Log before model invocation."""
    logger.info("model about to be called")
    return None


@after_model
def after_model_middleware(state, _):
    """Log after model completes response."""
    logger.info("model just replied")
    return None


@after_agent
def after_agent_middleware(state, _):
    """Log when agent execution completes."""
    logger.info("agent finished")
    return None


agent = create_agent(
    llm,
    tools=[greet],
    middleware=[
        before_agent_middleware,
        before_model_middleware,
        after_model_middleware,
        after_agent_middleware,
    ],
)

agent.invoke({"messages": [{"role": "user", "content": "Say hello to Alice"}]})
