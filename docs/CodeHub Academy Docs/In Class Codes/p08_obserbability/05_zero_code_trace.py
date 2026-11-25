"""


"""


from typing import TypedDict

from langgraph.graph import END, START, StateGraph


from dotenv import load_dotenv
load_dotenv()
"""
How do i see the LangSmith tracking?

https://smith.langchain.com/

"""


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

print(graph.invoke({"text": "Lab WiFi is down"}))

