"""
file: 02_react_loop.py
Lesson 2: model -> tools -> model, repeated until a final answer.

"""
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from p06_reactAgents.model_config import make_model
from p06_reactAgents.react_graph import build_graph


if __name__ == "__main__":
    graph = build_graph(make_model())
    try:
        for update in graph.stream(
            {"messages": [HumanMessage(content="What is the total for 3 laptops?")]},
            config={"recursion_limit": 20},
            stream_mode="updates",
        ):
            for node, change in update.items():
                print(f"\nNODE: {node}")
                for message in change.get("messages", []):
                    message.pretty_print()
    except GraphRecursionError:
        print("Stopped: graph step limit reached. Inspect the tool calls above.")
    # Typical trace: agent -> tools (price) -> agent -> tools (total) -> agent.
    # Trace shows public messages and tool calls, not private model reasoning.
