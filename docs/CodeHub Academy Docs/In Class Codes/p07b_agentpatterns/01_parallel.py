"""

Fixed fan-out: two independent checks, followed by one explicit join.

"""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    text: str
    word_count: int
    urgent: bool
    summary: str


def count_words(state: State):
    print('  count_words')
    return {'word_count': len(state['text'].split())}


def detect_urgency(state: State):
    print('  detect_urgency')
    return {'urgent': 'urgent' in state['text'].lower()}


def combine(state: State):
    print('  combine: both branches finished')
    return {'summary': f"Words={state['word_count']}, urgent={state['urgent']}"}


def build_graph():
    builder = StateGraph(State)
    builder.add_node('count_words', count_words)
    builder.add_node('detect_urgency', detect_urgency)
    builder.add_node('combine', combine)
    builder.add_edge(START, 'count_words')
    builder.add_edge(START, 'detect_urgency')
    # List of sources = wait for BOTH branches.
    builder.add_edge(['count_words', 'detect_urgency'], 'combine')
    builder.add_edge('combine', END)
    app = builder.compile()
    app.get_graph().draw_mermaid_png(output_file_path="images/parallel_graph.png")
    return app


if __name__ == '__main__':
    result = build_graph().invoke({'text': 'Urgent: checkout service is down'})
    print(result['summary'])
