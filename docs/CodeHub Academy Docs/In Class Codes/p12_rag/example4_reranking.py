"""

4. Re-ranking: improve the ordering of retrieved candidates

Retrieval first finds a small candidate set. A cross-encoder 
then reads each question–passage pair together and assigns a 
relevance score. This second stage is usually more computationally 
expensive than embedding similarity, so it is applied to candidates 
rather than the entire collection


uv add sentence_transformers

"""

# example4_reranking.py

from sentence_transformers import CrossEncoder

from p06_reactAgents.model_config import make_model
from p12_rag.rag_common import build_store, format_documents

llm = make_model()
store = build_store()

question = (
    "According to the 2025 mobile policy, "
    "how many days of cancellation notice are required?"
)

# Stage 1: retrieve candidates using embeddings.
candidates = store.similarity_search(question, k=5)

print("INITIAL ORDER:")
for document in candidates:
    print(document.metadata["source"])

# Stage 2: score each question-document pair.
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    device="cpu",
)

pairs = [
    (question, document.page_content)
    for document in candidates
]

scores = reranker.predict(pairs)

ranked = sorted(
    zip(candidates, scores),
    key=lambda item: float(item[1]),
    reverse=True,
)

print("\nRERANKED ORDER:")
for document, score in ranked:
    print(
        f"{float(score):.3f}",
        document.metadata["source"],
    )

# Stage 3: give only the top passages to the LLM.
best_documents = [
    document
    for document, score in ranked[:2]
]

answer = llm.invoke([
    (
        "system",
        "Answer only from the provided passages. "
        "Match the requested product and year carefully. "
        "Cite source identifiers in square brackets. "
        "If the answer is absent, say you do not know.",
    ),
    (
        "human",
        f"Question: {question}\n\n"
        f"Passages:\n{format_documents(best_documents)}",
    ),
])

print("\nANSWER:")
print(answer.content)