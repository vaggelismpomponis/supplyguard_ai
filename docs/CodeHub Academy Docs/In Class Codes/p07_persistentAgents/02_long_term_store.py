"""Explicit preference writes; retrieval works across different threads."""
import argparse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from p07_persistentAgents.common import database_url, live_model, thread_config
from p07_persistentAgents.graph_app import Context, build_graph, namespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["set", "get", "list", "delete", "ask"])
    parser.add_argument("--user", default="alice")
    parser.add_argument("--thread", default="new-conversation")
    parser.add_argument("--style", choices=["concise", "detailed", "bullet points"], default="concise")
    parser.add_argument("--message", default="Explain what a graph checkpointer does.")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    with PostgresStore.from_conn_string(database_url()) as store:
        ns = namespace(args.user)
        if args.action == "set":
            store.put(ns, "response_style", {"style": args.style})
            print("Saved:", args.style)
        elif args.action == "get":
            item = store.get(ns, "response_style")
            print(item.value if item else "No saved preference")
        elif args.action == "list":
            # Namespace listing, NOT semantic/vector search; no embeddings needed.
            for item in store.search(ns, limit=20):
                print(item.key, item.value)
        elif args.action == "delete":
            store.delete(ns, "response_style")
            print("Preference deleted; existing conversation checkpoints remain.")
        else:
            with PostgresSaver.from_conn_string(database_url()) as saver:
                graph = build_graph(checkpointer=saver, store=store,
                                    model=live_model() if args.live else None)
                result = graph.invoke({"messages": [HumanMessage(content=args.message)]},
                                      thread_config(args.user, args.thread),
                                      context=Context(args.user))
                print(result["messages"][-1].content)

if __name__ == "__main__":
    main()
