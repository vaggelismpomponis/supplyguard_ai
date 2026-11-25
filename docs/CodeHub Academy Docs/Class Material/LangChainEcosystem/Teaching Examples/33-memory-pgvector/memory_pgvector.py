# Persistent Memory with PostgreSQL and Vector Embeddings
# Demonstrates how multiple agent sessions can share persistent memory via PostgreSQL.
# Session A stores information, Session B retrieves it, showing cross-session memory.

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.store.postgres import PostgresStore

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
DB_URI = "postgresql://langgraph:langgraph@localhost:5444/agent_memory?sslmode=disable"


def fake_embed(texts: list[str]) -> list[list[float]]:
    """Generate simple embeddings for demonstration purposes."""
    return [[float((hash(t) >> (i * 4)) % 16) for i in range(8)] for t in texts]


# Session A: Store memory
with PostgresStore.from_conn_string(
    DB_URI,
    index={"dims": 8, "embed": fake_embed, "fields": ["content"]},
) as store:
    store.setup()

    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                store=store, namespace=lambda rt: ("codehub", "agent_memory")
            )
        },
    )

    agent = create_deep_agent(
        llm,
        backend=backend,
        memory=["/memories/AGENTS.md"],
        system_prompt="You are a CodeHub support assistant.",
    )
    session_a = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Remember this for future tickets: our refund SLA is 3 business days. "
                        "Save it to /memories/AGENTS.md."
                    ),
                }
            ],
        }
    )
    print("[session A]", session_a["messages"][-1].content)

# Session B: Retrieve shared memory
with PostgresStore.from_conn_string(
    DB_URI,
    index={"dims": 8, "embed": fake_embed, "fields": ["content"]},
) as store:
    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(
                store=store, namespace=lambda rt: ("codehub", "agent_memory")
            )
        },
    )
    agent = create_deep_agent(llm, backend=backend, memory=["/memories/AGENTS.md"])

    session_b = agent.invoke(
        {"messages": [{"role": "user", "content": "What's our refund SLA?"}]}
    )
    print("[session B]", session_b["messages"][-1].content)
