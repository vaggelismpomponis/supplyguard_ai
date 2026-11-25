from langchain_chroma import Chroma
from langchain_cohere import CohereEmbeddings
from langchain_core.documents import Document

embeddings = CohereEmbeddings(model="embed-multilingual-v3.0")

store = Chroma(
    collection_name="codehub_docs",
    embedding_function=embeddings,
    host="localhost",
    port=8000,
)

docs = [
    Document(
        page_content="Refunds are processed within 3-5 business days.",
        metadata={"topic": "billing"},
    ),
    Document(
        page_content="Critical bugs get a 1 hour response time.",
        metadata={"topic": "sla"},
    ),
    Document(
        page_content="CodeHub guarantees 99.9% monthly uptime.",
        metadata={"topic": "uptime"},
    ),
]
store.add_documents(docs)

results = store.similarity_search_with_score(
    "How fast do you respond to a critical bug?", k=2
)
for doc, score in results:
    print(f"{score:.3f}  [{doc.metadata['topic']}]  {doc.page_content}")
