"""Shared configuration; .env is resolved relative to these scripts."""
import os
from pathlib import Path
from dotenv import load_dotenv


def load_settings():
    load_dotenv(Path(__file__).with_name(".env"))


def database_url():
    load_settings()
    return os.getenv("DATABASE_URL", "postgresql://training:training_local_only@localhost:5433/agents?sslmode=disable")


def live_model():
    load_settings()
    from langchain_openai import AzureChatOpenAI, ChatOpenAI
    provider = os.getenv("MODEL_PROVIDER", "openai").lower()
    if provider == "azure":
        return AzureChatOpenAI(
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            streaming=True, timeout=60, max_retries=2,
        )
    if provider == "openai":
        return ChatOpenAI(model=os.environ["OPENAI_MODEL"], streaming=True,
                          timeout=60, max_retries=2)
    raise ValueError("MODEL_PROVIDER must be openai or azure")


def thread_config(user_id, thread_id, **extra):
    # Structured encoding avoids delimiter collisions. It is NOT authentication.
    import json
    return {"configurable": {"thread_id": json.dumps([user_id, thread_id])}, **extra}
