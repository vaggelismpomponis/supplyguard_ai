"""Run twice with the same thread to demonstrate process-level persistence."""
import argparse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
from p07_persistentAgents.common import database_url, live_model, thread_config
from p07_persistentAgents.graph_app import Context, build_graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="alice")
    parser.add_argument("--thread", default="conversation-1")
    parser.add_argument("--message", default="My name is Alice.")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    with PostgresSaver.from_conn_string(database_url()) as saver:
        graph = build_graph(checkpointer=saver, model=live_model() if args.live else None)
        config = thread_config(args.user, args.thread)
        if not args.inspect:
            result = graph.invoke({"messages": [HumanMessage(content=args.message)]},
                                  config, context=Context(args.user))
            print(result["messages"][-1].content)
        snapshot = graph.get_state(config)
        print("Stored messages:", len(snapshot.values.get("messages", [])))
        for message in snapshot.values.get("messages", []):
            print(f"{message.type}: {message.content}")
        print("Recent checkpoint steps (not one checkpoint per user turn):")
        for checkpoint in graph.get_state_history(config, limit=5):
            print(checkpoint.metadata.get("step"), checkpoint.next)

if __name__ == "__main__":
    main()
