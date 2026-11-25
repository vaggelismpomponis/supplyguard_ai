"""
MMR selects a diverse set of relevant candidates.

2. MMR: retrieve relevant but less repetitive passages

Ordinary similarity search can return multiple passages 
saying nearly the same thing. Maximal Marginal Relevance (MMR) 
balances similarity to the question against similarity to already 
selected passages.

"""

# example2_mmr.py

from p12_rag.rag_common import build_store, format_documents

store = build_store()

query = "How can I troubleshoot my home broadband connection?"

# Standard retrieval: select the closest passages.
similar_documents = store.similarity_search(
    query,
    k=3,
    filter={"category": "broadband"},
)

# MMR: select relevant passages while reducing repetition.
diverse_documents = store.max_marginal_relevance_search(
    query,
    k=3,
    fetch_k=5,
    lambda_mult=0.3,
    filter={"category": "broadband"},
)

print("STANDARD SIMILARITY SEARCH:")
print(format_documents(similar_documents))

print("\nMMR SEARCH:")
print(format_documents(diverse_documents))