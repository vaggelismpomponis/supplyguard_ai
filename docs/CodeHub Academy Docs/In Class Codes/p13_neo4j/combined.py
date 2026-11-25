"""
file: combined.py



For a production system, I would extend it with:
- Neo4j: Multi-hop dependency traversal and impact analysis. 
Answers questions about service dependencies
- Chroma: Runbooks, historical incident reports, and policy retrieval. 
Answers what the documentation says. 
- LangGraph / Deep Agents: Multi-step investigation and reasoning.


- Human-in-the-loop: Approval before restarting services or performing remediation.
- PostgreSQL checkpointer: Persistent agent state across requests.

"""







# hybrid_agent.py

import os
from deepagents import create_deep_agent
from dotenv import load_dotenv

from langchain.agents import create_agent
from neo4j import GraphDatabase

from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_chroma import Chroma



# --------------------------------------------------
# 1. Azure OpenAI
# --------------------------------------------------
load_dotenv()

from p06_reactAgents.model_config import make_model, getEmbeddings 

llm = make_model()
embeddings = getEmbeddings()




# --------------------------------------------------
# 2. Neo4j - Graph Database
# --------------------------------------------------

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(
        os.environ["NEO4J_USER"],
        os.environ["NEO4J_PASSWORD"],
    ),
)

driver.verify_connectivity()

# Sample service dependency graph
#
# Checkout -> Payments API -> PostgreSQL
# Mobile App -> Payments API

with driver.session() as session:
    session.run("""
        MERGE (checkout:Service {name: 'Checkout'})
        MERGE (mobile:Service {name: 'Mobile App'})
        MERGE (payments:Service {name: 'Payments API'})
        MERGE (db:Service {name: 'PostgreSQL'})

        MERGE (checkout)-[:DEPENDS_ON]->(payments)
        MERGE (mobile)-[:DEPENDS_ON]->(payments)
        MERGE (payments)-[:DEPENDS_ON]->(db)
    """)


# --------------------------------------------------
# 3. Chroma - Vector Database
# --------------------------------------------------

vectorstore = Chroma(
    collection_name="it_support",
    embedding_function=embeddings,
    persist_directory="./chroma/chroma_db",
)

documents = [
    Document(
        page_content=(
            "If Payments API fails, first inspect application "
            "logs and database connectivity. Check the "
            "PostgreSQL connection pool before restarting."
        ),
        metadata={"source": "payments_runbook"},
    ),
    Document(
        page_content=(
            "A Payments API outage can interrupt checkout "
            "and mobile payment processing. Notify the "
            "incident management team."
        ),
        metadata={"source": "incident_policy"},
    ),
    Document(
        page_content=(
            "Restarting a production service requires "
            "human approval."
        ),
        metadata={"source": "operations_policy"},
    ),
]


# if the documents already exist in the vector store, 
# this will update them instead of creating duplicates.

# if you want to ensure that the documents are only added once,
#  you can use unique IDs for each document. This way, if you run the code multiple times, it won't create duplicates.

# run only if store does not already contain the documents.
#  This is a simple check, but in a real-world scenario, 
# you might want to implement a more robust mechanism to avoid duplicates.


# Stable IDs prevent duplicate sample documents
vectorstore.add_documents(
    documents=documents,
    ids=["runbook-1", "policy-1", "policy-2"],
)


# --------------------------------------------------
# 4. Neo4j Tool
# --------------------------------------------------

@tool
def get_service_dependencies(service: str) -> str:
    """Find services that directly depend on a given service."""

    query = """
    MATCH (dependent:Service)-[:DEPENDS_ON]->
          (target:Service {name: $service})
    RETURN dependent.name AS name
    ORDER BY name
    """

    with driver.session() as session:
        records = list(
            session.run(query, service=service)
        )

    if not records:
        return f"No direct dependents found for {service}."

    return "\n".join(
        record["name"] for record in records
    )


# --------------------------------------------------
# 5. Chroma Tool
# --------------------------------------------------

@tool
def search_runbooks(question: str) -> str:
    """Search IT troubleshooting and operations documents."""

    docs = vectorstore.similarity_search(
        question,
        k=3,
    )

    return "\n\n".join(
        f"Source: {doc.metadata['source']}\n"
        f"{doc.page_content}"
        for doc in docs
    )


# --------------------------------------------------
# 6. Create Agent
# --------------------------------------------------

agent = create_agent(
    model=llm,
    tools=[
        get_service_dependencies,
        search_runbooks,
    ],
    system_prompt=(
        "You are an IT support agent. "
        "Use get_service_dependencies for service "
        "dependency questions. "
        "Use search_runbooks for troubleshooting "
        "and operational policy questions. "
        "Use both tools when necessary. "
        "Answer only from tool results. "
        "Cite document source IDs when available. "
        "Never invent facts."
    ),
)




# --------------------------------------------------
# 7. Ask the Agent
# --------------------------------------------------

try:


    # question = (
    #     "Which services directly depend on Payments API, "
    #     "and what should I do if it fails?"
    # )

    question = input("Ask the IT support agent a question: ")
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": question}
        ]
    })

    print("\n--- TOOL CALLS ---")

    for message in result["messages"]:
        for call in getattr(message, "tool_calls", []):
            print(call["name"], call["args"])

    print("\n--- FINAL ANSWER ---")
    print(result["messages"][-1].content)

finally:
    driver.close()

