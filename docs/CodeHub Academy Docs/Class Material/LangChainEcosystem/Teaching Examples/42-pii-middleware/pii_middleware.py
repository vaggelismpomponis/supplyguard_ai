# Built-in PIIMiddleware demonstrates automatic PII detection and filtering.
# Different strategies per PII type: redact (remove from input) or block (reject outright).

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import PIIDetectionError, PIIMiddleware
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")

agent = create_agent(
    llm,
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="block", apply_to_input=True),
    ],
)

# Redacted, not blocked -- the agent still gets a message, just without the raw email.
result = agent.invoke({"messages": [{"role": "user", "content": "Please refund jane@example.com for order 123."}]})
print("[email -> redacted]", result["messages"][-1].content)

try:
    agent.invoke({"messages": [{"role": "user", "content": "My card is 4111 1111 1111 1111, please charge it again."}]})
except PIIDetectionError as exc:
    print("[credit_card -> blocked]", exc)
