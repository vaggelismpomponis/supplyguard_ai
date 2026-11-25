"""Lesson 3: short-term memory is scoped to a thread_id."""
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from p06_reactAgents.model_config import make_model
from p06_reactAgents.react_graph import build_graph


def ask(graph, thread_id, text):
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
    # Send ONLY the new user message. The checkpointer restores prior messages.
    result = graph.invoke({"messages": [HumanMessage(content=text)]}, config)
    print(f"\n[{thread_id}] User: {text}")
    print("Assistant:", result["messages"][-1].content)
    print("Messages stored:", len(graph.get_state(config).values["messages"]))


if __name__ == "__main__":
    graph = build_graph(make_model(), checkpointer=InMemorySaver())
    ask(graph, "customer-a", "I need 3 laptops. What is the total?")
    ask(graph, "customer-a", "And if I buy 5 instead?")
    ask(graph, "customer-b", "Which product did I ask for earlier?")
    # A retains the laptop context; B has no previous product request.
    # InMemorySaver lasts only for this Python process, not across restarts.
