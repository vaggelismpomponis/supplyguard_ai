"""

Central routing: specialists always return control to the supervisor.
Agents are deterministic stand-ins so the routing is easy to inspect.


"""
from typing import Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command


class State(TypedDict):
    question: str
    evidence: str
    analysis: str
    answer: str


def supervisor(state: State) -> Command[Literal['researcher', 'analyst', '__end__']]:
    if not state.get('evidence'):
        print('supervisor -> researcher')
        return Command(goto='researcher')
    if not state.get('analysis'):
        print('supervisor -> analyst')
        return Command(goto='analyst')
    print('supervisor -> END')
    return Command(update={'answer': state['analysis']}, goto=END)


def researcher(state: State):
    print('  researcher: reading mock incident metrics')
    return {'evidence': 'CPU=95%; database latency=20ms; traffic=3x normal'}


def analyst(state: State):
    print('  analyst: interpreting evidence')
    overloaded = 'CPU=95%' in state['evidence']
    return {'analysis': 'Likely application overload; investigate capacity.'
            if overloaded else 'Need additional measurements.'}


def build_graph():
    builder = StateGraph(State)
    builder.add_node('supervisor', supervisor)
    builder.add_node('researcher', researcher)
    builder.add_node('analyst', analyst)
    builder.add_edge(START, 'supervisor')
    builder.add_edge('researcher', 'supervisor')
    builder.add_edge('analyst', 'supervisor')
    # No static outgoing edge on supervisor: Command controls its destination.
    app = builder.compile()
    app.get_graph().draw_mermaid_png(output_file_path="images/supervisor_graph.png")
    return app


if __name__ == '__main__':
    result = build_graph().invoke(
        {'question': 'Why is checkout slow?'}, {'recursion_limit': 10}
    )
    print(result['answer'])
