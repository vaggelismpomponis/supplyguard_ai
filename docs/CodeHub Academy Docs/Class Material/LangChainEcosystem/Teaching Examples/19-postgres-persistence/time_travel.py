# Time travel: browse full history and rewind to earlier checkpoints.
# Get full checkpoint history and continue from any prior state.

from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat(state: State) -> dict:
    """Invoke LLM with conversation history."""
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(State)
graph.add_node("chat", chat)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)
app = graph.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "time-travel-demo"}}
app.invoke({"messages": [HumanMessage("My favorite color is blue.")]}, config)
app.invoke({"messages": [HumanMessage("What's my favorite color?")]}, config)
app.invoke({"messages": [HumanMessage("Now say it's red instead.")]}, config)

# Full history: one snapshot per step, most recent first
history = list(app.get_state_history(config))
print(f"[history] {len(history)} checkpoints")
for snap in history:
    last = snap.values["messages"][-1] if snap.values.get("messages") else None
    print(f"  step -> next={snap.next} last_message={last.content if last else None!r}")

# Rewind: pick an EARLIER checkpoint and continue from there
earlier_checkpoint = history[-1].config if len(history) >= 3 else history[0].config
replayed = app.invoke(
    {"messages": [HumanMessage("Actually, what did I say my favorite color was?")]},
    earlier_checkpoint,
)
print("[replayed from earlier checkpoint]", replayed["messages"][-1].content)

# update_state: patch state directly, without re-running the graph
app.update_state(
    config,
    {"messages": [{"role": "assistant", "content": "(manually corrected note)"}]},
)
print("[after update_state]", app.get_state(config).values["messages"][-1].content)
