"""
file: model_config.py
Select a tool-calling model using .env; imported only by live demos.
"""
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, ChatOpenAI


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
