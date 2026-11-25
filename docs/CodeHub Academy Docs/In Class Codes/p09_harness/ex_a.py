"""
ex_a.py

compare three agents using the same model, tools, and question.

Run from your project where p06_reactAgents is importable:
    uv run --env-file .env compare_agents.py

make_model() must return a LangChain chat model that supports tool calling.
"""

from deepagents import create_deep_agent
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from p06_reactAgents.model_config import make_model

llm = make_model()


# Shared tools: mock telecom data.
@tool
def get_customer_usage(customer_id: str) -> dict:
    """Return a customer's typical monthly usage and current monthly fee."""
    if customer_id != "C001":
        return {"error": "Customer not found"}
    return {"data_gb": 18, "monthly_fee_eur": 35}


@tool
def list_mobile_plans() -> list[dict]:
    """Return available mobile plans with data allowances and monthly fees."""
    return [
        {"name": "Basic", "data_gb": 5, "monthly_fee_eur": 15},
        {"name": "Smart", "data_gb": 25, "monthly_fee_eur": 22},
        {"name": "Premium", "data_gb": 60, "monthly_fee_eur": 30},
    ]


tools = [get_customer_usage, list_mobile_plans]
prompt = """You are a telecom adviser. Use the tools to retrieve the data.
Recommend the cheapest plan covering the customer's typical monthly usage.
State the plan, monthly price, monthly savings, and annual savings (12 months).
Do not change the customer's plan. Answer briefly."""


question = "Which plan should customer C001 choose, and how much would they save?"


# 1. LangGraph: build the model -> tools -> model loop explicitly.
llm_with_tools = llm.bind_tools(tools)


def call_model(state: MessagesState):
    response = llm_with_tools.invoke(
        [SystemMessage(content=prompt)] + state["messages"]
    )
    return {"messages": [response]}


graph = StateGraph(MessagesState)
graph.add_node("model", call_model)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "model")
graph.add_conditional_edges("model", tools_condition)
graph.add_edge("tools", "model")
langgraph_agent = graph.compile()






# 2. LangChain: create_agent builds the agent loop for us.
langchain_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=prompt,
)


# 3. Deep Agents: adds built-in planning, file tools, and delegation.
# These extra capabilities may not be needed for this simple question.
deep_agent = create_deep_agent(
    model=llm,
    tools=tools,
    system_prompt=prompt,
)


# Run the same question independently through each agent.
for name, agent in [
    ("LangGraph", langgraph_agent),
    ("LangChain agent", langchain_agent),
    ("Deep Agents", deep_agent),
]:
    print(f"\n--- {name} ---")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 60},
    )
    print(result["messages"][-1].content)

# Expected: Smart, EUR 22/month, saving EUR 13/month or EUR 156/year.
