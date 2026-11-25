#Simple Agentic RAG System combining ChromaDB and Neo4j
import os
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from langchain_neo4j import Neo4jGraph
from langchain_anthropic import ChatAnthropic
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
import json

load_dotenv()

# Initialize LLM
llm = ChatAnthropic(model="claude-haiku-4-5")

# ============================================
# 1. Setup ChromaDB (Vector Database)
# ============================================
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(
    name="tickets",
    metadata={"hnsw:space": "cosine"}
)

# Sample documents
documents = [
    "App crashes when user tries to login with Google account",
    "User was charged twice for subscription renewal",
    "Dashboard loads slowly on mobile devices",
    "Export feature not working for PDF files",
    "Billing notification emails not being received",
]

# Add documents to ChromaDB
for i, doc in enumerate(documents):
    collection.add(
        ids=[f"doc-{i}"],
        documents=[doc],
        metadatas=[{"source": f"ticket-{i}"}]
    )

# ============================================
# 2. Setup Neo4j (Knowledge Graph)
# ============================================
graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="codehubpassword"
)

# Clear and initialize graph with sample data
graph.query("MATCH (n) DETACH DELETE n")
graph.query("""
CREATE (t1:Ticket {id: 'T-101', title: 'Login Bug', severity: 'high'})
       -[:HAS_CATEGORY]->(:Category {name: 'bug'})
       -[:OWNS]->(:Team {name: 'backend'}),
       (t1)-[:ASSIGNED_TO]->(:Developer {name: 'Alice', expertise: 'authentication'}),

       (t2:Ticket {id: 'T-102', title: 'Billing Issue', severity: 'critical'})
       -[:HAS_CATEGORY]->(:Category {name: 'billing'})
       -[:OWNS]->(:Team {name: 'payments'}),
       (t2)-[:ASSIGNED_TO]->(:Developer {name: 'Bob', expertise: 'payments'}),

       (t3:Ticket {id: 'T-103', title: 'Performance', severity: 'medium'})
       -[:HAS_CATEGORY]->(:Category {name: 'performance'})
       -[:OWNS]->(:Team {name: 'frontend'}),
       (t3)-[:ASSIGNED_TO]->(:Developer {name: 'Charlie', expertise: 'performance'})
""")
graph.refresh_schema()

# ============================================
# 3. Define RAG Tools for Agent
# ============================================

def vector_search_tool(query: str) -> str:
    """Search tickets by semantic similarity using ChromaDB"""
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    if results and results["documents"]:
        docs = "\n".join(results["documents"][0])
        return f"Vector Search Results:\n{docs}"
    return "No similar documents found"

def graph_search_tool(query: str) -> str:
    """Search the knowledge graph using Cypher queries"""
    try:
        # Simple pattern matching for different query types
        if "category" in query.lower() or "team" in query.lower():
            cypher = """
            MATCH (t:Ticket)-[:HAS_CATEGORY]->(c:Category)-[:OWNS]->(team:Team)
            RETURN t.id, c.name, team.name LIMIT 5
            """
        elif "assigned" in query.lower() or "developer" in query.lower():
            cypher = """
            MATCH (t:Ticket)-[:ASSIGNED_TO]->(dev:Developer)
            RETURN t.id, dev.name, dev.expertise LIMIT 5
            """
        elif "severity" in query.lower() or "priority" in query.lower():
            cypher = """
            MATCH (t:Ticket)
            RETURN t.id, t.title, t.severity ORDER BY t.severity DESC LIMIT 5
            """
        else:
            cypher = "MATCH (t:Ticket) RETURN t.id, t.title LIMIT 5"

        results = graph.query(cypher)
        return f"Graph Search Results:\n{json.dumps(results, indent=2)}"
    except Exception as e:
        return f"Graph search error: {str(e)}"

def combined_rag_tool(query: str) -> str:
    """Combine both vector and graph searches"""
    vector_result = vector_search_tool(query)
    graph_result = graph_search_tool(query)
    return f"{vector_result}\n\n{graph_result}"

# ============================================
# 4. Setup Agent with Tools
# ============================================

tools = [
    Tool(
        name="vector_search",
        func=vector_search_tool,
        description="Search for tickets using semantic similarity. Use this for finding tickets by content/description.",
    ),
    Tool(
        name="graph_search",
        func=graph_search_tool,
        description="Search the knowledge graph for relationships between tickets, teams, and developers. Use this for finding assignments or categories.",
    ),
    Tool(
        name="combined_rag",
        func=combined_rag_tool,
        description="Perform both vector and graph searches together. Use this when you need comprehensive results.",
    ),
]

# Create agent prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful support assistant with access to two databases:
1. Vector database (ChromaDB) - for semantic search of ticket contents
2. Knowledge graph (Neo4j) - for finding relationships and assignments

Analyze user queries and decide which search method is best:
- Use vector_search for semantic/content-based queries
- Use graph_search for relationship/assignment queries
- Use combined_rag when you need both perspectives

Provide clear, helpful answers based on the search results."""),
    ("user", "{input}"),
    ("assistant", "{agent_scratchpad}"),
])

# Create agent
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=5,
)

# ============================================
# 5. Run Example Queries
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Agentic RAG System - Demo")
    print("="*60)

    test_queries = [
        "Find tickets about login and authentication issues",
        "Who is assigned to handle billing problems?",
        "Show me all tickets and their categories and teams",
    ]

    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 60)
        result = agent_executor.invoke({"input": query})
        print(f"✅ Result: {result['output']}")
        print()
