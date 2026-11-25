from langchain_core.vectorstores import InMemoryVectorStore
from p06_reactAgents.model_config import make_model, getEmbeddings 

embeddings = getEmbeddings()

# 1. Sample documents.
texts = [
    "Employees have 25 days of annual leave.",
    "Employees can work remotely two days per week.",
    "The IT helpdesk is available from 09:00 to 17:00.",
]

# 2. Local embedding model.
 

# 3. Store documents and their vectors in memory.
store = InMemoryVectorStore(embedding=embeddings)
store.add_texts(texts)

# 4. Search.
question = "When can I contact technical support?"

results = store.similarity_search(question, k=1)

# 5. Print the matching document directly.
for document in results:
    print(document.page_content)