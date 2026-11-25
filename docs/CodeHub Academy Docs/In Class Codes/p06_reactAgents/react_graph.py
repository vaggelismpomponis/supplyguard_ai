"""

file: react_graph.py

Build the ReAct control flow explicitly, 
without an agent factory.


"""
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from p06_reactAgents.tools_lib import TOOLS

SYSTEM = """You are a sales assistant. Prices are in EUR.
Use get_unit_price for product prices and calculate_total for order totals.
Do not invent prices. Totals exclude tax and shipping.
Use earlier conversation messages to resolve follow-up requests.
If required information is missing, ask a short clarification question.
Give a concise final answer after receiving tool results."""


def make_agent_node(model_with_tools):
    def agent(state: MessagesState):
        response = model_with_tools.invoke(
            [SystemMessage(content=SYSTEM), *state["messages"]]
        )
        # MessagesState merges this new message into the existing history.
        # Returning all old messages again is unnecessary.
        return {"messages": [response]}
    return agent


def build_graph(model, checkpointer=None):
    model_with_tools = model.bind_tools(TOOLS)
    builder = StateGraph(MessagesState)
    builder.add_node("agent", make_agent_node(model_with_tools))
    builder.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    builder.add_edge(START, "agent")
    # tool calls -> tools; final answer -> END
    builder.add_conditional_edges(
        "agent", tools_condition, {"tools": "tools", END: END}
    )
    builder.add_edge("tools", "agent")
    app = builder.compile(checkpointer=checkpointer)
    app.get_graph().draw_mermaid_png(output_file_path="images/react_graph.png")
    return app
