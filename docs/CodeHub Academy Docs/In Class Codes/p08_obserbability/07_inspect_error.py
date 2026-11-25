from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class Ticket(TypedDict, total=False):
    text: str
    team: str


def classify(state: Ticket) -> dict:
    if not state["text"].strip():
        raise ValueError("Ticket text is empty")
    return {"team": "helpdesk"}


builder = StateGraph(Ticket)
builder.add_node("classify", classify)
builder.add_edge(START, "classify")
builder.add_edge("classify", END)
graph = builder.compile()

for ticket_text in ["", "Printer is offline"]:
    try:
        result = graph.invoke({"text": ticket_text}, {"run_name": "07-inspect-error"})
        print(result)
    except ValueError as error:
        print(f"Expected failure: {error}")

