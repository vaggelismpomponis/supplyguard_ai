import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
SERVER_PATH = Path(__file__).parent / "server.py"


async def main():
    client = MultiServerMCPClient(
        {
            "codehub-tickets": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(SERVER_PATH)],
            }
        }
    )

    tools = await client.get_tools()
    print("Tools discovered over MCP:", [t.name for t in tools])

    agent = create_agent(llm, tools=tools)
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What is the priority level of ticket T-101?"}]}
    )
    print("\nAgent response:")
    print(result["messages"][-1].content)


asyncio.run(main())



# client = MultiServerMCPClient(
#     {
#         "codehub-tickets-remote": {
#             "transport": "sse",
#             "url": "https://api.example.com/mcp/sse",
#             "headers": {
#                 "Authorization": "Bearer YOUR_API_KEY",
#                 "Content-Type": "application/json"
#             }
#         }
#     }
# )