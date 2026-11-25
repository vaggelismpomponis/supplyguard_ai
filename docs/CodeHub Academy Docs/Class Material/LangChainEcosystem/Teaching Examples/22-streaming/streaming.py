# Streaming output: stream node updates and token generation.
# Watch the graph execute step-by-step and tokens as they're generated.

import asyncio

from unit3.common import build_graph

app = build_graph()

INPUT = {"ticket": "Payment failed twice", "category": None, "reply": None}

for update in app.stream(INPUT, stream_mode="updates"):
    for node_name, node_output in update.items():
        print(f"  [{node_name} finished] -> {node_output}")


async def stream_tokens():
    print("\n=== astream_events: tokens as they're generated, inside 'reply' ===")
    async for event in app.astream_events(INPUT, version="v2"):
        if event["event"] == "on_chat_model_stream" and event["metadata"].get("langgraph_node") == "reply":
            print(event["data"]["chunk"].content, end="", flush=True)
    print()


asyncio.run(stream_tokens())
