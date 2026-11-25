"""Local callback spans by default; opt in to LangSmith using .env."""
import argparse
import os
import time
from uuid import uuid4
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_core.tracers.langchain import wait_for_all_tracers
from p07_persistentAgents.common import live_model, load_settings
from p07_persistentAgents.graph_app import Context, build_graph


class ConsoleSpans(BaseCallbackHandler):
    """Show correlation and elapsed time without logging prompt contents."""
    def __init__(self):
        self.started = {}

    def begin(self, kind, run_id, parent_run_id, name):
        self.started[run_id] = time.perf_counter()
        print(f"START {kind} {name} run={run_id} parent={parent_run_id}")

    def finish(self, kind, run_id):
        start = self.started.pop(run_id, None)
        elapsed = time.perf_counter() - start if start is not None else 0
        print(f"END {kind} run={run_id} seconds={elapsed:.3f}")

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, **kwargs):
        self.begin("chain", run_id, parent_run_id, kwargs.get("name", "chain"))

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        self.finish("chain", run_id)

    def on_chain_error(self, error, *, run_id, **kwargs):
        print(f"ERROR run={run_id} type={type(error).__name__}")
        self.finish("chain", run_id)

    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kwargs):
        self.begin("model", run_id, parent_run_id, kwargs.get("name", "chat_model"))

    def on_llm_end(self, response, *, run_id, **kwargs):
        self.finish("model", run_id)

    def on_llm_error(self, error, *, run_id, **kwargs):
        print(f"ERROR run={run_id} type={type(error).__name__}")
        self.finish("model", run_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    load_settings()
    enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    print("LangSmith tracing:", enabled)
    run_id = uuid4()
    graph = build_graph(model=live_model() if args.live else None)
    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content="Explain the purpose of tracing.")]},
            config={"run_id": run_id, "run_name": "training-observability",
                    "tags": ["training", "lesson-4"],
                    "metadata": {"lesson": 4, "mode": "live" if args.live else "demo"},
                    "callbacks": [ConsoleSpans()]},
            context=Context("demo-user"),
        )
        print("Answer:", result["messages"][-1].content)
        print("Root run ID:", run_id)
    finally:
        # Allow background trace uploads to finish before this short script exits.
        wait_for_all_tracers()

if __name__ == "__main__":
    main()
