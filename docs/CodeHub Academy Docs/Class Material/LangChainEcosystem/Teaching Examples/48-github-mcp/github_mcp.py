# connects to GitHub MCP server to search for Python frameworks

import asyncio

import dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient

dotenv.load_dotenv()


async def main():
    """Connect to GitHub MCP server and search for Python web frameworks."""

    print("\n" + "=" * 60)
    print("GitHub MCP - Minimal Example")
    print("=" * 60)

    llm = ChatAnthropic(model="claude-haiku-4-5")

    config = {
        "github": {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "--yes",
                "@modelcontextprotocol/server-github",
            ],
        }
    }

    try:
        print("\nConnecting to GitHub MCP server...\n")
        client = MultiServerMCPClient(config)
        tools = await client.get_tools()

        print(f"Success! Found {len(tools)} tools:\n")

        for tool in tools:
            print(f"   • {tool.name}")

        print("\n" + "=" * 60)
        print("DEMO: Using the simplest tool")
        print("=" * 60)

        print("\nQuery: Find Python web frameworks")
        print("-" * 60)

        agent = create_agent(llm, tools=tools)
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Find popular Python web frameworks on GitHub",
                    }
                ]
            }
        )

        print("\nResult:")
        print(result["messages"][-1].content)

    except FileNotFoundError:
        print("Error: GitHub MCP server not found")
        print("\nInstall it with:")
        print("   npm install -g @modelcontextprotocol/server-github")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
