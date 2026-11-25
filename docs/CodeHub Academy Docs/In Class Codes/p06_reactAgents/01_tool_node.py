"""
file: 01_tool_node.py
Lesson 1: 
a prebuilt ToolNode inside a minimal graph. No LLM call.
Pattern: ReAct (reasoning + acting loop) built from scratch

"""
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from p06_reactAgents.tools_lib import TOOLS


def build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    app = builder.compile()
    app.get_graph().draw_mermaid_png(output_file_path="images/simple.png")
    return app


if __name__ == "__main__":
    # Normally the model emits this structured request. Here we construct it.
    request = AIMessage(content="", tool_calls=[{
        "name": "get_unit_price", "args": {"product": "laptop"},
        "id": "price_1", "type": "tool_call",
    }])
    result = build_graph().invoke({"messages": [request]})
    for message in result["messages"]:
        message.pretty_print()
    # The ToolMessage has content 900.0 and tool_call_id='price_1'.
