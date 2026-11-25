"""Deep agent with subagent that uses MCP tools to look up ticket information."""
import asyncio
import os
import sys
from pathlib import Path

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(model=os.environ["OPENAI_MODEL"])

SERVER_PATH = Path(__file__).parent / "server.py"


async def main():
    """Create deep agent with ticket-specialist subagent and query ticket SLA."""
    client = MultiServerMCPClient({
        "codehub-tickets": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(SERVER_PATH)],
        }
    })
    mcp_tools = await client.get_tools()
    print("Tools discovered over MCP:", [t.name for t in mcp_tools])

    ticket_specialist = {
        "name": "ticket-specialist",
        "description": "Looks up ticket priority and SLA using the MCP ticket tools.",
        "system_prompt": "Use the MCP tools to find the priority and SLA hours for the ticket asked about.",
        "tools": mcp_tools,
    }

    agent = create_deep_agent(
        llm,
        system_prompt="Delegate any ticket-priority/SLA question to the ticket-specialist subagent.",
        subagents=[ticket_specialist],
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": "What's the SLA for ticket T-101?"}]})
    print(result["messages"][-1].content)


asyncio.run(main())
