"""
file: model_config.py
Select a tool-calling model using .env; imported only by live demos.
"""
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, ChatOpenAI, OpenAIEmbeddings


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
BATCH_SIZE = 50


def make_model():
    load_dotenv()
    provider = os.getenv("MODEL_PROVIDER", "openai").lower()
    if provider == "azure":
        return AzureChatOpenAI(
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            timeout=60,
            max_retries=2,
        )
    if provider == "openai":
        return ChatOpenAI(model=os.environ["OPENAI_MODEL"], timeout=60, max_retries=2)
    raise ValueError("MODEL_PROVIDER must be openai or azure")


def getEmbeddings():
    load_dotenv()
    return  OpenAIEmbeddings(
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
        # Send text directly; avoid tokenizing by a custom deployment name.
        check_embedding_ctx_length=False,
        chunk_size=BATCH_SIZE,
        max_retries=3,
        request_timeout=60,
    )