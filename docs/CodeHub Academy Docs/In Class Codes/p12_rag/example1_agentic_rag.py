"""
1. Self-query extracts explicit metadata constraints.

"""

# example1_agentic_rag.py

from deepagents import create_deep_agent
from langchain.tools import tool

from p06_reactAgents.model_config import make_model
from p12_rag.rag_common import build_store, format_documents

llm = make_model()
store = build_store()


@tool
def search_policies(query: str) -> str:
    """Search telecom policies and troubleshooting instructions."""
    documents = store.similarity_search(query, k=3)
    return format_documents(documents)


agent = create_deep_agent(
    model=llm,
    tools=[search_policies],
    system_prompt=(
        "You are a telecom support assistant. "
        "For policy and troubleshooting questions, use search_policies. "
        "Base your answer only on the retrieved passages. "
        "Cite sources using their identifiers in square brackets. "
        "If the passages do not answer the question, say so."
    ),
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "According to the 2025 policy, how much notice "
                   "is needed to cancel a mobile contract?",
    }]
})

# Show which retrieval queries the agent generated.
for message in result["messages"]:
    for call in getattr(message, "tool_calls", []):
        print("TOOL:", call["name"])
        print("ARGUMENTS:", call["args"])

print("\nANSWER:")
print(result["messages"][-1].content)