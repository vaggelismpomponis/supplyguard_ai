"""

Each streaming mode starts a NEW graph execution.

"""
import time
from typing import TypedDict
from p06_reactAgents.model_config import make_model
 
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    topic: str
    prompt: str
    answer: str


def build_graph(model):
    def prepare(state: State):
        time.sleep(0.5)  # Make this processing step visible in the demo.
        return {'prompt': f"Explain {state['topic']} in one short sentence."}

    def generate(state: State):
        # messages mode streams model chunks even though we call invoke().
        response = model.invoke(state['prompt'])
        return {'answer': response.content}

    builder = StateGraph(State)
    builder.add_node('prepare', prepare)
    builder.add_node('generate', generate)
    builder.add_edge(START, 'prepare')
    builder.add_edge('prepare', 'generate')
    builder.add_edge('generate', END)
    app = builder.compile()
    app.get_graph().draw_mermaid_png(output_file_path="images/streaming_graph.png")
    return app


def run(graph, mode):
    print(f'\n--- {mode.upper()} ---', flush=True)
    inputs = {'topic': 'LangGraph', 'prompt': '', 'answer': ''}

    # v1 explicitly selects the simple output shapes demonstrated below.
    for chunk in graph.stream(inputs, stream_mode=mode, version='v1'):
        if mode == 'messages':
            message_chunk, metadata = chunk
            if metadata.get('langgraph_node') == 'generate':
                print(message_chunk.text, end='', flush=True)
        else:
            print(chunk, flush=True)
    print()


def main():
    model = make_model()

    graph = build_graph(model)
    modes = ['values', 'updates', 'messages']
    for mode in modes:
        run(graph, mode)


if __name__ == '__main__':
    main()
