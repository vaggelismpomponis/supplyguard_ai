# Chat LLM clients from different providers
# Each provider has different auth and model naming.

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq


load_dotenv()

print("=== Chat LLM Clients ===\n")

# Anthropic (Claude)
print("--- Anthropic ---")
anthropic_llm = ChatAnthropic(
    model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)
response = anthropic_llm.invoke("Say hi in 3 words.")
print("Model:", anthropic_llm.model)
print("Response:", response.content)

# OpenAI (GPT)
# print("\n--- OpenAI ---") # error if not found ...
# openai_llm = ChatOpenAI(
#     model=os.environ["OPENAI_MODEL"],
#     api_key=os.environ["OPENAI_API_KEY"],
# )
# response = openai_llm.invoke("Say hi in 3 words.")
# print("Model:", openai_llm.model)
# print("Response:", response.content)

# Groq (fast LLaMA)

print("\n--- Groq ---")
groq_llm = ChatGroq(model="qwen3:latest")
response = groq_llm.invoke("Say hi in 3 words.")
print("Model:", groq_llm.model)
print("Response:", response.content)

