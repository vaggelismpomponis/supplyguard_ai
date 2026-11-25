
from dotenv import load_dotenv
from langchain_cohere import CohereEmbeddings
from numpy import dot
from numpy.linalg import norm

load_dotenv()

embeddings = CohereEmbeddings(model="embed-multilingual-v3.0")

chunks = [
    "Refunds for duplicate charges are processed within 3-5 business days.",
    "Critical bugs are answered within 1 hour, 24/7.",
    "CodeHub's platform guarantees 99.9% monthly uptime.",
]
query = "How long does a refund take?"

chunk_vectors = embeddings.embed_documents(chunks)
query_vector = embeddings.embed_query(query)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return dot(a, b) / (norm(a) * norm(b))


scored = sorted(
    zip(chunks, chunk_vectors),
    key=lambda pair: cosine_similarity(query_vector, pair[1]),
    reverse=True,
)

print(f"Query: {query!r}\n")
for chunk, vector in scored:
    print(f"{cosine_similarity(query_vector, vector):.3f}  {chunk}")
