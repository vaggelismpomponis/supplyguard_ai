from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class Ticket(TypedDict, total=False):
    text: str
    team: str


def classify(state: Ticket) -> dict:
    team = "network" if "wifi" in state["text"].lower() else "helpdesk"
    return {"team": team}


builder = StateGraph(Ticket)
builder.add_node("classify", classify)
builder.add_edge(START, "classify")
builder.add_edge("classify", END)
graph = builder.compile()

for school, ticket_text in [("north", "WiFi is down"), ("south", "Printer is offline")]:
    config = {
        "run_name": "08-filter-runs",
        "tags": ["training", "support-ticket"],
        "metadata": {"school": school},
    }
    print(graph.invoke({"text": ticket_text}, config))

