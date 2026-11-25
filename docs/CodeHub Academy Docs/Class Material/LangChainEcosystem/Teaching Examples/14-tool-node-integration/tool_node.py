# Agent with tool calling: LLM decides when to call a tool, ToolNode executes it.

from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


@tool
def get_ticket_count(status: str) -> int:
    """Return support ticket count by status."""
    return {"open": 42, "closed": 918}.get(status, 0)


tools = [get_ticket_count]
llm_with_tools = llm.bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def agent(state: State) -> Command[Literal["tools", "__end__"]]:
    """Decide whether to call tools or end the conversation."""
    ai_msg = llm_with_tools.invoke(state["messages"])
    goto = "tools" if ai_msg.tool_calls else END
    return Command(goto=goto, update={"messages": [ai_msg]})


graph = StateGraph(State)

graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))  # no hand-written loop -- ToolNode does it

graph.add_edge(START, "agent")
graph.add_edge("tools", "agent")

app = graph.compile()

result = app.invoke(
    {"messages": [HumanMessage("How many open tickets does CodeHub have?")]}
)
print(result["messages"][-1].content)


mermaid = app.get_graph().draw_mermaid()
with open("graph.md", "w", encoding="utf-8") as f:
    f.write("```mermaid\n")
    f.write(mermaid)
    f.write("\n```")

