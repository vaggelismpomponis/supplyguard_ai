"""

 ex_c.python
 deep agent with memory and virtual directory


"""
 

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langgraph.checkpoint.memory import InMemorySaver

from p06_reactAgents.model_config import make_model

llm = make_model()

agent = create_deep_agent(
    model=llm,
    backend=StateBackend(),
    checkpointer=InMemorySaver(),
    system_prompt="Use the filesystem tools. Do not delegate.",
)

config = {"configurable": {"thread_id": "files-demo"}}

# First turn: create and modify a virtual file.
result = agent.invoke(
    {
        "messages": [{
            "role": "user",
            "content": (
                "Write /notes.txt with these two lines:\n"
                "Python lesson: Monday\n"
                "SQL lesson: Tuesday\n"
                "Then edit the SQL lesson day to Friday."
            ),
        }]
    },
    config=config,
)

print(result["messages"][-1].content)

# Second turn: the same thread retains the file.
result = agent.invoke(
    {
        "messages": [{
            "role": "user",
            "content": (
                "List the files in /. "
                "Read /notes.txt and tell me when the SQL lesson is."
            ),
        }]
    },
    config=config,
)

print(result["messages"][-1].content)

# Inspect the actual file content stored in state.
print("\nStored file:")
print("\n".join(result["files"]["/notes.txt"]["content"]))