from dotenv import load_dotenv
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_anthropic import ChatAnthropic
from langchain_cohere import CohereEmbeddings
from langchain_postgres import PGVector, PGVectorTranslator
from pydantic import BaseModel, Field

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")
embeddings = CohereEmbeddings(model="embed-multilingual-v3.0")
store = PGVector(
    embeddings=embeddings,
    connection="postgresql+psycopg://langchain:langchain@localhost:5445/vectorstore",
    collection_name="codehub_docs",
)

question = "How fast do you respond to a critical bug?"

mmr_retriever = store.as_retriever(search_type="mmr", search_kwargs={"k": 2, "fetch_k": 10})
mmr_results = mmr_retriever.invoke(question)
print("[MMR]", [d.page_content for d in mmr_results])


metadata_field_info = [
    AttributeInfo(name="topic", description="One of: billing, sla, uptime", type="string"),
]
self_query_retriever = SelfQueryRetriever.from_llm(
    llm,
    vectorstore=store,
    document_contents="CodeHub internal policy documents",
    metadata_field_info=metadata_field_info,
    structured_query_translator=PGVectorTranslator(),
)
self_query_results = self_query_retriever.invoke(question)
print("[self-query]", [d.page_content for d in self_query_results])


class Rerank(BaseModel):
    scores: list[float] = Field(description="Relevance score 0-1 for each candidate, same order as given")


candidates = store.similarity_search(question, k=5)
rerank = llm.with_structured_output(Rerank, method="function_calling").invoke(
    f"Question: {question!r}\nScore each candidate's relevance 0-1:\n"
    + "\n".join(f"{i}. {c.page_content}" for i, c in enumerate(candidates))
)
reranked = [c for _, c in sorted(zip(rerank.scores, candidates), key=lambda pair: pair[0], reverse=True)][:2]
print("[reranked]", [d.page_content for d in reranked])
