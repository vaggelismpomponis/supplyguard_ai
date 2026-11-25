"""

Lesson 4: isolated tool/node tests and deterministic graph checks.
how to test
uv run pytest src/reactAgents/04_test_training.py -v -s

"""
from unittest.mock import Mock
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from p06_reactAgents.react_graph import build_graph, make_agent_node
from p06_reactAgents.tools_lib import TOOLS, calculate_total, get_unit_price


def call(name="get_unit_price", args=None, call_id="call_1"):
    return AIMessage(content="", tool_calls=[{
        "name": name, "args": {"product": "laptop"} if args is None else args,
        "id": call_id, "type": "tool_call",
    }])


def test_tool_in_isolation():
    assert get_unit_price.invoke({"product": " Laptop "}) == 900.0
    assert calculate_total.invoke({"unit_price": 900, "quantity": 3}) == 2700.0


@pytest.mark.parametrize("args", [
    {"unit_price": -1, "quantity": 3}, {"unit_price": 900, "quantity": 0},
])
def test_invalid_total(args):
    with pytest.raises(ValueError):
        calculate_total.invoke(args)


def test_unknown_product():
    with pytest.raises(ValueError, match="Unknown product"):
        get_unit_price.invoke({"product": "spaceship"})


def isolated_tool_graph():
    # A one-node harness supplies ToolNode's graph runtime; no model is involved.
    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    return builder.compile()


def test_tool_node_preserves_call_id():
    result = isolated_tool_graph().invoke({"messages": [call()]})
    message = result["messages"][-1]
    assert isinstance(message, ToolMessage)
    assert message.tool_call_id == "call_1"
    assert float(message.content) == 900.0


def test_tool_error_becomes_observation():
    result = isolated_tool_graph().invoke({
        "messages": [call(args={"product": "spaceship"})]
    })
    assert result["messages"][-1].status == "error"
    assert result["messages"][-1].tool_call_id == "call_1"


def test_routing_in_isolation():
    assert tools_condition({"messages": [call()]}) == "tools"
    assert tools_condition({"messages": [AIMessage(content="Done")]}) == END


def test_agent_node_in_isolation():
    model = Mock()
    model.invoke.return_value = AIMessage(content="Hello")
    original = [HumanMessage(content="Hi")]
    update = make_agent_node(model)({"messages": original})
    assert len(update["messages"]) == 1
    assert update["messages"][0].content == "Hello"
    sent = model.invoke.call_args.args[0]
    assert isinstance(sent[0], SystemMessage)
    assert sent[1:] == original
    assert len(original) == 1


def test_complete_react_loop_without_api():
    model = Mock()
    model.bind_tools.return_value = model
    model.invoke.side_effect = [
        call(),
        call("calculate_total", {"unit_price": 900, "quantity": 3}, "call_2"),
        AIMessage(content="Total: EUR 2700, excluding tax and shipping."),
    ]
    result = build_graph(model).invoke({"messages": [HumanMessage(content="3 laptops")]})
    assert [m.type for m in result["messages"]] == [
        "human", "ai", "tool", "ai", "tool", "ai"
    ]
    assert [float(m.content) for m in result["messages"] if isinstance(m, ToolMessage)] == [900, 2700]
    assert model.invoke.call_count == 3


def test_memory_and_thread_isolation():
    model = Mock()
    model.bind_tools.return_value = model
    model.invoke.side_effect = lambda messages: AIMessage(content="Acknowledged")
    graph = build_graph(model, InMemorySaver())
    a = {"configurable": {"thread_id": "a"}}
    b = {"configurable": {"thread_id": "b"}}
    graph.invoke({"messages": [HumanMessage(content="I want laptops")]}, a)
    graph.invoke({"messages": [HumanMessage(content="Make it five")]}, a)
    seen = model.invoke.call_args.args[0]
    assert [m.content for m in seen if isinstance(m, HumanMessage)] == [
        "I want laptops", "Make it five"
    ]
    graph.invoke({"messages": [HumanMessage(content="Hello")]}, b)
    seen = model.invoke.call_args.args[0]
    assert [m.content for m in seen if isinstance(m, HumanMessage)] == ["Hello"]
    assert len(graph.get_state(a).values["messages"]) == 4
    assert len(graph.get_state(b).values["messages"]) == 2


def test_unending_tool_calls_are_bounded():
    model = Mock()
    model.bind_tools.return_value = model
    model.invoke.side_effect = lambda messages: call()
    with pytest.raises(GraphRecursionError):
        build_graph(model).invoke(
            {"messages": [HumanMessage(content="Loop")]}, {"recursion_limit": 4}
        )
