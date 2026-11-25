"""Peer handoffs: each specialist chooses the next specialist, without a boss.
This is a small network, not an all-to-all graph. All actions are simulations.
"""
from typing import Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command


class State(TypedDict):
    issue: str
    diagnosis: str
    fixed: bool
    attempts: int
    answer: str


def diagnostics(state: State) -> Command[Literal['repair', 'review']]:
    if 'timeout' in state['issue'].lower() and not state['fixed']:
        print('diagnostics -> repair')
        return Command(update={'diagnosis': 'Connection pool exhausted'}, goto='repair')
    print('diagnostics -> review')
    return Command(update={'diagnosis': 'Needs manual investigation'}, goto='review')


def repair(state: State) -> Command[Literal['review']]:
    print('repair -> review (simulated action)')
    attempts = state['attempts'] + 1
    # Deliberately fail once to demonstrate a peer-to-peer retry loop.
    return Command(update={'attempts': attempts, 'fixed': attempts >= 2}, goto='review')


def review(state: State) -> Command[Literal['repair', '__end__']]:
    if state['fixed']:
        print('review -> END')
        return Command(update={'answer': 'Simulated health check passed.'}, goto=END)
    if state['diagnosis'] == 'Connection pool exhausted' and state['attempts'] < 2:
        print('review -> repair: retry requested')
        return Command(goto='repair')
    print('review -> END: escalate')
    return Command(update={'answer': 'Escalate to a human operator.'}, goto=END)


def build_graph():
    builder = StateGraph(State)
    builder.add_node('diagnostics', diagnostics)
    builder.add_node('repair', repair)
    builder.add_node('review', review)
    builder.add_edge(START, 'diagnostics')
    # Every node routes through Command; no static outgoing edges needed.
    app = builder.compile()
    app.get_graph().draw_mermaid_png(output_file_path="images/network_graph.png")
    return app


if __name__ == '__main__':
    result = build_graph().invoke(
        {'issue': 'Checkout timeout', 'fixed': False, 'attempts': 0},
        {'recursion_limit': 10},
    )
    print(result['answer'])
