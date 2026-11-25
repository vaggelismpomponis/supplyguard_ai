"""

Select one stream mode or combine all three in one graph execution.
"""
import argparse
from langchain_core.messages import HumanMessage
from p07_persistentAgents.common import live_model, load_settings
from p07_persistentAgents.graph_app import Context, build_graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["values", "updates", "messages", "all"], default="updates")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    load_settings()
    graph = build_graph(model=live_model() if args.live else None, demo_delay=0.01)
    modes = ["values", "updates", "messages"] if args.mode == "all" else args.mode
    # v2 makes the outer envelope identical for single/multiple modes.
    for part in graph.stream(
        {"messages": [HumanMessage(content="Explain persistence in two sentences.")]},
        context=Context("alice"), stream_mode=modes, version="v2",
    ):
        mode, data = part["type"], part["data"]
        if mode == "messages":
            chunk, metadata = data
            if metadata.get("langgraph_node") == "answer":
                print(chunk.text, end="", flush=True)
        elif mode == "updates":
            print("\nUPDATES:", data, flush=True)
        else:
            print("\nVALUES:", data, flush=True)
    print()

if __name__ == "__main__":
    main()
