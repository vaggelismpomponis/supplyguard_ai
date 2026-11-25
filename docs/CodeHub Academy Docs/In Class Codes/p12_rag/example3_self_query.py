"""


3. Self-query: convert natural language into metadata filters
Re-ranking orders those candidates more carefully.

"""

# example3_self_query.py

from typing import Literal

from pydantic import BaseModel, Field

from p06_reactAgents.model_config import make_model
from p12_rag.rag_common import build_store, format_documents

llm = make_model()
store = build_store()


class SearchPlan(BaseModel):
    query: str = Field(
        description="The semantic search text."
    )
    category: Literal["mobile", "broadband"] | None = Field(
        default=None,
        description="Product category, only if specified by the user.",
    )
    year: int | None = Field(
        default=None,
        description="Policy year, only if specified by the user.",
    )


question = "What is the mobile cancellation notice in 2025?"

planner = llm.with_structured_output(SearchPlan)

plan = planner.invoke([
    (
        "system",
        "Convert the question into a semantic query and metadata filters. "
        "Do not invent a category or year if the user did not specify one.",
    ),
    ("human", question),
])

print("GENERATED SEARCH PLAN:")
print(plan.model_dump())

# Convert the validated plan into Chroma filter syntax.
conditions = []

if plan.category is not None:
    conditions.append({"category": {"$eq": plan.category}})

if plan.year is not None:
    conditions.append({"year": {"$eq": plan.year}})

search_arguments = {"k": 3}

if len(conditions) == 1:
    search_arguments["filter"] = conditions[0]
elif len(conditions) > 1:
    search_arguments["filter"] = {"$and": conditions}

documents = store.similarity_search(
    plan.query,
    **search_arguments,
)

print("\nRETRIEVED DOCUMENTS:")
print(format_documents(documents))

if not documents:
    print("\nNo matching policy was found.")
else:
    answer = llm.invoke([
        (
            "system",
            "Answer only from the provided passages. "
            "Cite source identifiers in square brackets. "
            "If the answer is absent, say you do not know.",
        ),
        (
            "human",
            f"Question: {question}\n\n"
            f"Passages:\n{format_documents(documents)}",
        ),
    ])

    print("\nANSWER:")
    print(answer.content)