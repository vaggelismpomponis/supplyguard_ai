"""
ex_b.py
An agent that plans and completes a task 
by calling tools in a loop until a final answer is reached.
This is a simple example of a ReAct agent
 that uses a tool to answer a question.

"""

# example1_introduction.py

from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

from p06_reactAgents.model_config import make_model

llm = make_model()

"""
create_deep_agent() accepts ordinary Python functions and automatically converts them into tools, using:
- The function name as the tool name.
- The docstring as its description.
- The type hints to describe its inputs.

But the @tool decorator can also be used to customize 
the tool name, description, and input schema.
"""


def get_sales() -> str:
    """Return sample sales data."""
    return "January: 1000 EUR\nFebruary: 1500 EUR\nMarch: 1200 EUR"


agent = create_deep_agent(
    model=llm,
    tools=[get_sales],
    middleware=[TodoListMiddleware()],
    system_prompt=(
        "You are a sales assistant. "
        "Use write_todos to track your steps. "
        "Complete the work yourself without delegating."
    ),
)



result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": (
            "Get the sales data. Calculate the total. "
            "Write a short report to /sales_report.md. "
            "Mark your tasks completed and tell me the total."
        ),
    }]
})

print(result["messages"][-1].content)



print("\nTasks:")
for item in result.get("todos", []):
    print(item["status"], "-", item["content"])

print("-"*10)  


# how can i have access to the virtual files 
# created by the agent? 
# The result object contains a "files" key 
# that holds the virtual files created
#  during the agent's execution. 
# You can access and print them as follows:



print("\nVirtual files:")
for path in result.get("files", {}):
    print(path)

# the content of the virtual files can be accessed 
# using the path as a key in the "files" dictionary:
for path, content in result.get("files", {}).items():
    print(f"\nContent of {path}:")
    print(content)  

# to persist the virtual files to disk, 
# you can write them to the filesystem:
# the name of the file is the key in the "files" dictionary,    
# the local file will be created in the current working 
# directory with the same name as the virtual file.
# if you want to save the files in a different directory,
# you can modify the path accordingly.  

for path, content in result.get("files", {}).items():
    local_path = "data2/" + path.lstrip("/")  # remove leading slash for local file path
    with open(local_path, "w") as f:
        f.write(content["content"])    

print("\nVirtual files saved to disk.")
