# Functional LanggGraph API: plain Python control flow instead of graph objects.
# Same ticket workflow but using @task and @entrypoint decorators.

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.func import entrypoint, task

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


@task
def classify(ticket: str) -> str:
    """Classify support ticket into a single-word category."""
    return llm.invoke(
        f"One word category (billing/bug/general) for: {ticket!r}"
    ).content.strip()


@task
def draft_reply(ticket: str, category: str) -> str:
    """Draft a reply for a classified ticket."""
    return llm.invoke(
        f"Write a short reply to this {category} ticket: {ticket!r}"
    ).content


# @entrypoint: the workflow itself -- plain Python control flow, no graph object
@entrypoint()
def handle_ticket(ticket: str) -> dict:
    """Classify and reply to a support ticket end-to-end."""
    # Ordinary function calls -- `.result()` blocks until that task's
    # checkpointed step completes, same durability guarantee as a graph edge.
    category = classify(ticket).result()
    reply = draft_reply(ticket, category).result()
    return {"category": category, "reply": reply}


result = handle_ticket.invoke("The app crashes every time I try to export a report.")
print(f"[functional api] category={result['category']}")
print(result["reply"])


mermaid = handle_ticket.get_graph().draw_mermaid()
with open("graph.md", "w", encoding="utf-8") as f:
    f.write("```mermaid\n")
    f.write(mermaid)
    f.write("\n```")

mermaid = handle_ticket.get_graph().draw_png()
with open("graph.md", "w", encoding="utf-8") as f:
    f.write("```mermaid\n")
    f.write(mermaid)
    f.write("\n```")

