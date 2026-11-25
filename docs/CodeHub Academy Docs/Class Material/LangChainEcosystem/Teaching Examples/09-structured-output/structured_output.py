# Structured output
# Two approaches: with_structured_output (model native) or OutputParsers (LCEL chain).

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")


# Approach 1: with_structured_output (native model constraint)
# class City(BaseModel):
#     """Schema: city data."""

#     name: str = Field(description="City name")
#     country: str = Field(description="Country name")
#     population: int = Field(description="Approximate population")


# # The model's response is constrained to match this schema.
# structured_llm = llm.with_structured_output(City, method="function_calling")
# city: City = structured_llm.invoke("Tell me about Athens, Greece.")
# print("[structured]", city, "-> type:", type(city).__name__)


# Approach 2: Output parsers (declarative, works in LCEL chains)
# StrOutputParser: extract plain text (remove markdown/formatting)
str_chain = (
    ChatPromptTemplate.from_messages([("human", "{q}")]) | llm | StrOutputParser()
)
str_result = str_chain.invoke({"q": "Name one planet."})
print("[str parser]", repr(str_result), "-> type:", type(str_result).__name__)


# JsonOutputParser: parse JSON from the response
json_chain = (
    ChatPromptTemplate.from_messages([("human", "{q}")]) | llm | JsonOutputParser()
)

# ask strictly for JSON in prompt. Error otherwise.
data = json_chain.invoke(
    {
        "q": "Return JSON with keys 'planet' for the planet you choose. JSON only, no markdown fences."
    }
)
print("[json parser]", data, "-> type:", type(data).__name__)
