"""
Dynamic fan-out: the input determines how many worker tasks are created.
"""
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class State(TypedDict):
    request: str
    tasks: list[str]
    results: Annotated[list[tuple[str, str]], operator.add]
    report: str


class WorkerState(TypedDict):
    service: str


STATUS = {'checkout': 'DOWN', 'payments': 'OK', 'catalog': 'SLOW'}


def orchestrator(state: State):
    # A real orchestrator could use structured LLM output to create this plan.
    tasks = list(dict.fromkeys(
        item.strip().lower() for item in state['request'].split(',')
        if item.strip()
    ))
    print('Plan:', tasks)
    return {'tasks': tasks}


def dispatch(state: State):
    # Each Send invokes the SAME worker with its OWN input.
    if not state['tasks']:
        return 'synthesize'
    return [Send('worker', {'service': task}) for task in state['tasks']]


def worker(state: WorkerState):
    service = state['service']
    print('  worker:', service)
    return {'results': [(service, STATUS.get(service, 'UNKNOWN'))]}


def synthesize(state: State):
    # Completion order is not a presentation order: sort explicitly.
    rows = sorted(state['results'])
    return {'report': '\n'.join(f'{name}: {status}' for name, status in rows)
            or 'No services requested.'}


def build_graph():
    builder = StateGraph(State)
    builder.add_node('orchestrator', orchestrator)
    builder.add_node('worker', worker)
    builder.add_node('synthesize', synthesize)
    builder.add_edge(START, 'orchestrator')
    builder.add_conditional_edges('orchestrator', dispatch, ['worker', 'synthesize'])
    builder.add_edge('worker', 'synthesize')
    builder.add_edge('synthesize', END)
    app = builder.compile()
    app.get_graph().draw_mermaid_png(output_file_path="images/orchestrator_workers_graph.png")
    return app


if __name__ == '__main__':
    result = build_graph().invoke({
        'request': 'checkout, payments, catalog', 'results': []
    })
    print(result['report'])
