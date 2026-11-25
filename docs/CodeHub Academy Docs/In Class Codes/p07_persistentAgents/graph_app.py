"""Two nodes make state updates, memory retrieval and model spans visible."""
from dataclasses import dataclass
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime


@dataclass(frozen=True)
class Context:
    user_id: str


class State(MessagesState):
    preference: str


def namespace(user_id):
    return ("users", user_id, "preferences")


def build_graph(*, checkpointer=None, store=None, model=None, demo_delay=0.0):
    def load_preference(state: State, runtime: Runtime[Context]):
        item = (runtime.store.get(namespace(runtime.context.user_id), "response_style")
                if runtime.store is not None else None)
        # Reset on every turn, including when no preference exists.
        return {"preference": item.value["style"] if item else "not set"}

    def answer(state: State):
        history = [str(m.content) for m in state["messages"] if isinstance(m, HumanMessage)]
        selected_model = model
        if selected_model is None:
            # This fake chat model emits deterministic characters when streamed.
            # It demonstrates plumbing, not actual LLM reasoning or tokenization.
            text = (f"DEMO | style={state['preference']} | "
                    f"user turns={len(history)} | history: " + " / ".join(history))
            selected_model = FakeListChatModel(responses=[text], sleep=demo_delay)
        response = selected_model.invoke([
            SystemMessage(content=(
                "You are a concise training assistant. Use the conversation history. "
                "The user's response-style preference is: " + state["preference"]
            )),
            *state["messages"],
        ])
        return {"messages": [response]}

    builder = StateGraph(State, context_schema=Context)
    builder.add_node("load_preference", load_preference)
    builder.add_node("answer", answer)
    builder.add_edge(START, "load_preference")
    builder.add_edge("load_preference", "answer")
    builder.add_edge("answer", END)
    return builder.compile(checkpointer=checkpointer, store=store)
