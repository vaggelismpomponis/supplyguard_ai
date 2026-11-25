from time import sleep
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class Ticket(TypedDict, total=False):
    text: str
    team: str


def classify(state: Ticket) -> dict:
    team = "network" if "wifi" in state["text"].lower() else "helpdesk"
    return {"team": team}


def assign(state: Ticket) -> dict:
    sleep(0.3)  # Simulate a slow directory lookup.
    return {"team": state["team"] + " support"}


builder = StateGraph(Ticket)
builder.add_node("classify", classify)
builder.add_node("assign", assign)
builder.add_edge(START, "classify")
builder.add_edge("classify", "assign")
builder.add_edge("assign", END)
graph = builder.compile()
print(graph.invoke({"text": "Lab WiFi is down"}, {"run_name": "06-inspect-latency"}))

