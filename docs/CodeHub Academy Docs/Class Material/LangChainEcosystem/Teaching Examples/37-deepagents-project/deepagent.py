import asyncio
from pathlib import Path

# FOR ASYNC SUPPORT, add:
# import asyncio
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

load_dotenv()


llm = AzureChatOpenAI(model="gpt-4.1-mini")


@tool
def get_account_status(customer_email: str) -> str:
    """Look up a CodeHub customer's account status and plan."""
    return "active, Pro plan, member since 2024"


billing_specialist = {
    "name": "billing-specialist",
    "description": "Handles billing questions: charges, refunds, invoices, subscriptions.",
    "system_prompt": "You are CodeHub's billing specialist. Refund timeline is 3-5 business days.",
    "tools": [get_account_status],
}

tech_specialist = {
    "name": "tech-specialist",
    "description": "Handles technical bug reports: crashes, errors, broken features.",
    "system_prompt": "You are CodeHub's technical support specialist. Ask for reproduction steps if missing.",
}

agent = create_deep_agent(
    llm,
    backend=FilesystemBackend(root_dir=Path(__file__).parent),
    skills=["/skills/ticket-triage/"],
    subagents=[billing_specialist, tech_specialist],
    system_prompt="You triage CodeHub support tickets using the ticket-triage skill, then delegate.",
)

# --- SYNCHRONOUS INVOCATION (current) ---
# result = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": "Hi i am Customer jane@example.com and I was charged twice this month for her subscription.",
#             }
#         ]
#     }
# )
# print(result["messages"][-1].content)


# --- FOR ASYNC INVOCATION ---
async def run_async():
    """Execute agent asynchronously."""
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Hi, I'm jane@example.com. The CodeHub editor crashes every time I open a large project file, and after that I can't log in again — it just shows a blank screen.",
                }
            ]
        }
    )
    print("[ainvoke]", result["messages"][-1].content)


asyncio.run(run_async())

# --- FOR STREAMING UPDATES ---
# print("\n[stream updates]")
# with langsmith_client.trace(
#     run_type="chain",
#     name="support-ticket-triage",
#     project_name="AccentureGTGH"
# ) as run:
#     for chunk in agent.stream(
#         {"messages": [{
#             "role": "user",
#             "content": "Hi i am Customer jane@example.com and I was charged twice this month for her subscription.",
#         }]},
#         stream_mode="updates",
#     ):
#         for node_name in chunk:
#             print(f"  -- {node_name} --")
