# rag_common.py

from uuid import uuid4

from langchain_core.documents import Document
from langchain_chroma import Chroma
from p06_reactAgents.model_config import make_model, getEmbeddings 

# llm = make_model()
# embeddings = getEmbeddings()

def build_store():
    """Build a temporary vector store containing fictional policies."""

    documents = [
        Document(
            page_content=(
                "Home broadband customers can restart their router "
                "by unplugging it for 30 seconds."
            ),
            metadata={
                "source": "router_restart",
                "category": "broadband",
                "year": 2025,
            },
        ),
        Document(
            page_content=(
                "To reboot a home broadband router, disconnect its "
                "power for 30 seconds and reconnect it."
            ),
            metadata={
                "source": "router_reboot",
                "category": "broadband",
                "year": 2025,
            },
        ),
        Document(
            page_content=(
                "For slow broadband, test the connection using an "
                "Ethernet cable to distinguish Wi-Fi problems."
            ),
            metadata={
                "source": "broadband_speed",
                "category": "broadband",
                "year": 2025,
            },
        ),
        Document(
            page_content=(
                "Before troubleshooting broadband, check whether "
                "there is a service outage in the customer's area."
            ),
            metadata={
                "source": "broadband_outage",
                "category": "broadband",
                "year": 2025,
            },
        ),
        Document(
            page_content=(
                "The 2024 mobile cancellation policy requires "
                "30 days of notice."
            ),
            metadata={
                "source": "mobile_cancellation_2024",
                "category": "mobile",
                "year": 2024,
            },
        ),
        Document(
            page_content=(
                "The 2025 mobile cancellation policy requires "
                "14 days of notice."
            ),
            metadata={
                "source": "mobile_cancellation_2025",
                "category": "mobile",
                "year": 2025,
            },
        ),
        Document(
            page_content=(
                "The 2025 broadband cancellation policy requires "
                "30 days of notice."
            ),
            metadata={
                "source": "broadband_cancellation_2025",
                "category": "broadband",
                "year": 2025,
            },
        ),
    ]

    embeddings = getEmbeddings()

    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=f"demo_{uuid4().hex}",
    )


def format_documents(documents):
    """Format passages with source identifiers."""
    return "\n\n".join(
        f"[{doc.metadata['source']}]\n{doc.page_content}"
        for doc in documents
    )