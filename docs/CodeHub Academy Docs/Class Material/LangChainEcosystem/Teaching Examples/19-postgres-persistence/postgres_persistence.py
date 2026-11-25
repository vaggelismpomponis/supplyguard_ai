# Database persistence with PostgreSQL: state survives process restarts.
# Each process can load previous conversation history from the same thread_id.

# uv add langgraph-checkpoint-postgres psycopg[binary] psycopg-pool


from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
DB_URI = "postgresql://langgraph:langgraph@localhost:5442/checkpoints?sslmode=disable"


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat(state: State) -> dict:
    """Invoke LLM with conversation history."""
    return {"messages": [llm.invoke(state["messages"])]}


def build_app(checkpointer):
    """Build workflow with database persistence."""
    graph = StateGraph(State)
    graph.add_node("chat", chat)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=checkpointer)


config = {"configurable": {"thread_id": "ticket-T-101"}}

# "Process A": open a connection, run one turn, then close the connection --
# simulating the process exiting entirely.
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()  # creates the checkpoint tables the first time; no-op after
    app = build_app(checkpointer)
    r1 = app.invoke(
        {"messages": [HumanMessage("My name is Nikos. Remember that.")]}, config
    )
    print("[process A]", r1["messages"][-1].content)

# "Process B": a brand new connection, same thread_id, no Python state carried
# over -- MemorySaver could never do this, it only lives in process memory.
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    app = build_app(checkpointer)
    r2 = app.invoke({"messages": [HumanMessage("What's my name?")]}, config)
    print("[process B]", r2["messages"][-1].content)
