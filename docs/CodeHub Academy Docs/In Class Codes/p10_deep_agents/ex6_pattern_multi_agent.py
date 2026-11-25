"""
    Simple example for Deep agent pattern: multi-agent 


    One coordinator delegates to two specialists using Deep Agents.

Run from your project root:
    uv add deepagents
    uv run --env-file .env deep_agent_multi_agent.py

Requires your existing p06_reactAgents.model_config module and a model
that supports tool calling. No external research or actions are performed.
"""

from deepagents import create_deep_agent
from p06_reactAgents.model_config import make_model


def build_agent(llm):
    return create_deep_agent(
        model=llm,
        subagents=[
            {
                "name": "plan-analyst",
                "description": "Selects a mobile plan from supplied usage and prices.",
                "model": llm,
                "tools": [],
                "system_prompt": (
                    "Choose the cheapest supplied plan that covers the customer's "
                    "monthly data usage. Explain your calculation briefly. "
                    "Use only the supplied facts; do not invent offers."
                ),
            },
            {
                "name": "customer-writer",
                "description": "Turns a plan recommendation into a customer message.",
                "model": llm,
                "tools": [],
                "system_prompt": (
                    "Write a friendly customer message in at most three sentences. "
                    "Use the supplied recommendation, price, and reasoning. "
                    "Do not invent discounts or say the plan has been changed."
                ),
            },
        ],
        system_prompt=(
            "You coordinate two specialists. First use the task tool to delegate "
            "to plan-analyst, including ALL customer facts and available plans. "
            "Then use task to delegate to customer-writer, including the original "
            "facts AND the analyst's recommendation. Subagents have separate "
            "contexts, so explicitly pass everything each needs. "
            "Return the writer's message as your final answer."
        ),
    )


if __name__ == "__main__":
    llm = make_model()
    agent = build_agent(llm)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": (
            "Recommend a mobile plan for Alex, who uses 12 GB per month. "
            "Available plans: Basic: 5 GB for EUR 10/month; "
            "Plus: 20 GB for EUR 18/month; "
            "Unlimited: unlimited data for EUR 30/month."
        )}]},
        config={"recursion_limit": 40},
    )

    # Show the coordinator's actual delegations.
    for message in result["messages"]:
        for call in getattr(message, "tool_calls", []):
            if call["name"] == "task":
                print("Delegated to:", call["args"]["subagent_type"])

    print("\nFinal answer:")
    print(result["messages"][-1].content)
