from dotenv import load_dotenv
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")

graph = Neo4jGraph(url="bolt://localhost:7687", username="neo4j", password="codehubpassword")

graph.query("""
MATCH (n) DETACH DELETE n
""")

graph.query("""
CREATE (t1:Ticket {id: 'T-101', text: 'App crashes on login'})-[:HAS_CATEGORY]->(:Category {name: 'bug'}),
       (t1)-[:ESCALATED_TO]->(:Specialist {name: 'tech-specialist'}),
       (t2:Ticket {id: 'T-102', text: 'Charged twice'})-[:HAS_CATEGORY]->(:Category {name: 'billing'}),
       (t2)-[:ESCALATED_TO]->(:Specialist {name: 'billing-specialist'})
""")
graph.refresh_schema()

qa_chain = GraphCypherQAChain.from_llm(
    llm,
    graph=graph,
    allow_dangerous_requests=True,
    verbose=True,
)

result = qa_chain.invoke({"query": "Which specialist handled ticket T-101?"})
print(result["result"])
