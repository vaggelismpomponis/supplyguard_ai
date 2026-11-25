from typing import Optional, TypedDict

import chainlit as cl
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


class State(TypedDict):
    ticket: str
    category: str | None
    reply: str | None


def classify(state: State) -> dict:
    return {"category": llm.invoke(f"One word category (billing/bug/general): {state['ticket']!r}").content.strip()}


def reply(state: State) -> dict:
    prompt = f"Write a short reply to this {state['category']} ticket: {state['ticket']!r}"
    return {"reply": llm.invoke(prompt).content}


graph = StateGraph(State)
graph.add_node("classify", classify)
graph.add_node("reply", reply)
graph.add_edge(START, "classify")
graph.add_edge("classify", "reply")
graph.add_edge("reply", END)
agent = graph.compile()


@cl.on_chat_start
async def start():
    await cl.Message(content="Hi! Paste a support ticket and I'll classify it and draft a reply.").send()


@cl.on_message
async def on_message(message: cl.Message):
    ui_message = cl.Message(content="")
    await ui_message.send()

    input_state = {"ticket": message.content, "category": None, "reply": None}
    async for event in agent.astream_events(input_state, version="v2"):
        if event["event"] == "on_chat_model_stream" and event["metadata"].get("langgraph_node") == "reply":
            await ui_message.stream_token(event["data"]["chunk"].content)

    await ui_message.update()
