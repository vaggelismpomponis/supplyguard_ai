# LCEL = LangChain Expression Language.

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

llm = ChatAnthropic(model="claude-haiku-4-5")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Answer in one sentence."),
        ("human", "{q}"),
    ]
)

# Direct: messages + LLM
messages = prompt.invoke({"q": "What is photosynthesis?"})
result = llm.invoke(messages)
print(result.content)


# Prompt | LLM
chain = prompt | llm

# Prompt | LLM | Parser
chain = prompt | llm | StrOutputParser()


# Chain invokation modes: invoke(), batch(), stream()
# invoke()
result = chain.invoke({"q": "What is DNA?"})
print(result)

# batch()
for result in chain.batch(
    [
        {"q": "What is an atom?"},
        {"q": "What is evolution?"},
    ]
):
    print(result)

# stream()
for chunk in chain.stream({"q": "Name one planet."}):
    print(chunk, end="", flush=True)
