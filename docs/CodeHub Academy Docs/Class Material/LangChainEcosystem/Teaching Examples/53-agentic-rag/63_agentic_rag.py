from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_cohere import CohereEmbeddings
from langchain_core.tools.retriever import create_retriever_tool
from langchain_postgres import PGVector

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
embeddings = CohereEmbeddings(model="embed-multilingual-v3.0")

store = PGVector(
    embeddings=embeddings,
    connection="postgresql+psycopg://langchain:langchain@localhost:5445/vectorstore",
    collection_name="codehub_docs",
)

retriever_tool = create_retriever_tool(
    store.as_retriever(search_kwargs={"k": 2}),
    name="search_codehub_docs",
    description="Search CodeHub's internal policy docs (refunds, SLA, uptime).",
)

agent = create_agent(
    llm,
    tools=[retriever_tool],
    system_prompt="Use search_codehub_docs for any question about CodeHub's policies. Answer directly otherwise.",
)

r1 = agent.invoke(
    {"messages": [{"role": "user", "content": "What's CodeHub's refund timeline?"}]}
)
print("[policy question]", r1["messages"][-1].content)

r2 = agent.invoke({"messages": [{"role": "user", "content": "What's 12 * 12?"}]})
print("[general question]", r2["messages"][-1].content)
