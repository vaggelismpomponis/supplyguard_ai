"""Simple demo comparing ChromaDB vs Neo4j without the agent"""
import os
from dotenv import load_dotenv
import chromadb
from langchain_neo4j import Neo4jGraph
import json

load_dotenv()

print("\n" + "="*70)
print("RAG SYSTEM DEMO: ChromaDB vs Neo4j")
print("="*70)

# ============================================
# PART 1: ChromaDB (Vector Database)
# ============================================
print("\n\n🔵 PART 1: ChromaDB (Vector/Semantic Search)")
print("-" * 70)

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(
    name="tickets_demo",
    metadata={"hnsw:space": "cosine"}
)

documents = [
    "App crashes when user tries to login with Google account",
    "User was charged twice for subscription renewal",
    "Dashboard loads slowly on mobile devices",
    "Export feature not working for PDF files",
    "Billing notification emails not being received",
    "Search functionality returns no results",
]

print("\n📚 Adding documents to ChromaDB:")
for i, doc in enumerate(documents, 1):
    collection.add(ids=[f"doc-{i}"], documents=[doc])
    print(f"  {i}. {doc}")

print("\n🔍 Vector Search Example:")
query = "login issues and authentication problems"
print(f"Query: '{query}'")
results = collection.query(query_texts=[query], n_results=3)

print("\nResults (by semantic similarity):")
for i, (doc, distance) in enumerate(zip(results["documents"][0], results["distances"][0]), 1):
    similarity = 1 - distance  # Convert distance to similarity
    print(f"  {i}. [{similarity:.2f}] {doc}")

# ============================================
# PART 2: Neo4j (Knowledge Graph)
# ============================================
print("\n\n🟢 PART 2: Neo4j (Knowledge Graph/Relationships)")
print("-" * 70)

graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="codehubpassword"
)

# Clear and setup
print("\n🔧 Setting up knowledge graph...")
graph.query("MATCH (n) DETACH DELETE n")

graph.query("""
CREATE
    (t1:Ticket {id: 'T-101', title: 'Login Bug', severity: 'HIGH'})
    -[:HAS_CATEGORY]->(:Category {name: 'authentication'})
    -[:OWNED_BY]->(:Team {name: 'backend'}),
    (t1)-[:ASSIGNED_TO]->(:Developer {name: 'Alice', skill: 'auth-expert'}),

    (t2:Ticket {id: 'T-102', title: 'Billing Issue', severity: 'CRITICAL'})
    -[:HAS_CATEGORY]->(:Category {name: 'payments'})
    -[:OWNED_BY]->(:Team {name: 'payments'}),
    (t2)-[:ASSIGNED_TO]->(:Developer {name: 'Bob', skill: 'payments-expert'}),

    (t3:Ticket {id: 'T-103', title: 'Performance', severity: 'MEDIUM'})
    -[:HAS_CATEGORY]->(:Category {name: 'performance'})
    -[:OWNED_BY]->(:Team {name: 'frontend'}),
    (t3)-[:ASSIGNED_TO]->(:Developer {name: 'Charlie', skill: 'performance-expert'})
""")
graph.refresh_schema()

print("✅ Knowledge graph created with 3 tickets\n")

# Query 1: Find who handles specific categories
print("🔗 Graph Query 1: Who handles authentication issues?")
result = graph.query("""
    MATCH (t:Ticket)-[:HAS_CATEGORY]->(c:Category {name: 'authentication'})
    MATCH (t)-[:ASSIGNED_TO]->(dev:Developer)
    RETURN t.id, t.title, c.name, dev.name, dev.skill
""")
print(json.dumps(result, indent=2))

# Query 2: Find all tickets by team
print("\n🔗 Graph Query 2: All tickets grouped by team")
result = graph.query("""
    MATCH (t:Ticket)-[:HAS_CATEGORY]->(c:Category)-[:OWNED_BY]->(team:Team)
    RETURN team.name, collect({id: t.id, title: t.title, category: c.name}) as tickets
""")
print(json.dumps(result, indent=2))

# Query 3: Find high priority tickets
print("\n🔗 Graph Query 3: High priority tickets and their assignments")
result = graph.query("""
    MATCH (t:Ticket {severity: 'HIGH'})
    MATCH (t)-[:ASSIGNED_TO]->(dev:Developer)
    RETURN t.id, t.title, t.severity, dev.name, dev.skill
""")
print(json.dumps(result, indent=2))

# ============================================
# PART 3: Comparison
# ============================================
print("\n\n" + "="*70)
print("📊 COMPARISON: When to use each database")
print("="*70)

comparison = """
┌─────────────────────┬────────────────────┬─────────────────────┐
│ Use Case            │ ChromaDB (Vector)  │ Neo4j (Graph)       │
├─────────────────────┼────────────────────┼─────────────────────┤
│ "Find similar..."   │ ✅ PERFECT         │ ❌ Not designed for │
│                     │ (semantic search)  │                     │
├─────────────────────┼────────────────────┼─────────────────────┤
│ "Find who..."       │ ❌ Not ideal       │ ✅ PERFECT          │
│                     │ (needs keyword)    │ (relationship)      │
├─────────────────────┼────────────────────┼─────────────────────┤
│ "Find connected..." │ ❌ Not designed    │ ✅ PERFECT          │
│                     │ (no graph support) │ (traversal)         │
├─────────────────────┼────────────────────┼─────────────────────┤
│ Fuzzy matching      │ ✅ EXCELLENT       │ ❌ Exact matching   │
├─────────────────────┼────────────────────┼─────────────────────┤
│ Exact relationships │ ❌ Can't model     │ ✅ Native support   │
└─────────────────────┴────────────────────┴─────────────────────┘

🎯 Agent Strategy:
   ChromaDB: Good for understanding MEANING
   Neo4j:    Good for understanding STRUCTURE

   → Agent uses both to give COMPLETE answers!
"""

print(comparison)

print("\n" + "="*70)
print("✨ Now run 'agentic_rag.py' to see the AI agent combine both!")
print("="*70 + "\n")
