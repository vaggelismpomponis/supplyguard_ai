"""Unit tests are offline; --postgres opts in to real Postgres round trips."""
import importlib
from uuid import uuid4
import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from p07_persistentAgents.common import database_url, thread_config
from p07_persistentAgents.graph_app import Context, build_graph, namespace


def ask(graph, user, thread, text):
    return graph.invoke({"messages": [HumanMessage(content=text)]},
                        thread_config(user, thread), context=Context(user))


def test_history_survives_graph_rebuild():
    saver = InMemorySaver()
    ask(build_graph(checkpointer=saver), "alice", "a", "My name is Alice")
    result = ask(build_graph(checkpointer=saver), "alice", "a", "What is my name?")
    assert len(result["messages"]) == 4
    assert "user turns=2" in result["messages"][-1].content


def test_new_thread_has_no_old_messages():
    graph = build_graph(checkpointer=InMemorySaver())
    ask(graph, "alice", "a", "My name is Alice")
    result = ask(graph, "alice", "b", "Hello")
    assert len(result["messages"]) == 2
    assert "My name is Alice" not in result["messages"][-1].content


def test_store_crosses_threads_but_not_users():
    store = InMemoryStore()
    store.put(namespace("alice"), "response_style", {"style": "concise"})
    graph = build_graph(checkpointer=InMemorySaver(), store=store)
    for thread in ["a", "b"]:
        result = ask(graph, "alice", thread, "Hello")
        assert result["preference"] == "concise"
        assert len(result["messages"]) == 2
    assert ask(graph, "bob", "a", "Hello")["preference"] == "not set"


def test_deleted_preference_is_not_reused_in_state():
    store = InMemoryStore()
    store.put(namespace("alice"), "response_style", {"style": "concise"})
    graph = build_graph(checkpointer=InMemorySaver(), store=store)
    ask(graph, "alice", "a", "Hello")
    store.delete(namespace("alice"), "response_style")
    assert ask(graph, "alice", "a", "Again")["preference"] == "not set"


def test_stream_modes_and_model_chunks():
    graph = build_graph()
    events = list(graph.stream(
        {"messages": [HumanMessage(content="Hello")]}, context=Context("alice"),
        stream_mode=["values", "updates", "messages"], version="v2",
    ))
    assert {e["type"] for e in events} == {"values", "updates", "messages"}
    updates = [e["data"] for e in events if e["type"] == "updates"]
    assert list(updates[0]) == ["load_preference"]
    assert list(updates[1]) == ["answer"]
    text = "".join(e["data"][0].text for e in events if e["type"] == "messages")
    final = [e["data"] for e in events if e["type"] == "values"][-1]
    assert text == final["messages"][-1].content
    assert len(final["messages"]) == 2


def test_callback_records_model_and_graph(capsys):
    module = importlib.import_module("04_observability")
    handler = module.ConsoleSpans()
    build_graph().invoke({"messages": [HumanMessage(content="Hello")]},
                         {"callbacks": [handler]}, context=Context("alice"))
    output = capsys.readouterr().out
    assert "START model" in output
    assert "END model" in output
    assert "START chain" in output
    assert handler.started == {}


@pytest.mark.postgres
def test_postgres_survives_connection_and_graph_reopen(request):
    if not request.config.getoption("--postgres"):
        pytest.skip("Start Docker, run setup, then pass --postgres")
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.store.postgres import PostgresStore
    user = "test-" + uuid4().hex
    config_a = thread_config(user, "a")
    config_b = thread_config(user, "b")
    try:
        with PostgresSaver.from_conn_string(database_url()) as saver, \
                PostgresStore.from_conn_string(database_url()) as store:
            store.put(namespace(user), "response_style", {"style": "concise"})
            graph = build_graph(checkpointer=saver, store=store)
            ask(graph, user, "a", "First message")
        # Close both connections and reconstruct graph/saver/store.
        with PostgresSaver.from_conn_string(database_url()) as saver, \
                PostgresStore.from_conn_string(database_url()) as store:
            graph = build_graph(checkpointer=saver, store=store)
            result = ask(graph, user, "a", "Second message")
            assert len(result["messages"]) == 4
            assert result["preference"] == "concise"
            result = ask(graph, user, "b", "New conversation")
            assert len(result["messages"]) == 2
            assert result["preference"] == "concise"
    finally:
        # Only test-owned records are removed, even after an assertion failure.
        with PostgresSaver.from_conn_string(database_url()) as saver, \
                PostgresStore.from_conn_string(database_url()) as store:
            saver.delete_thread(config_a["configurable"]["thread_id"])
            saver.delete_thread(config_b["configurable"]["thread_id"])
            store.delete(namespace(user), "response_style")
