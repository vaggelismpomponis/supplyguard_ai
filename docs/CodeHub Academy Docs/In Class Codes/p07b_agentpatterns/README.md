 - Pattern: Parallelization (fan-out / fan-in)
 - Pattern: Orchestrator-Workers
 - Multi-agent patterns: Supervisor and Network


# Four LangGraph coordination patterns

Python 3.11+. Tested with LangGraph 1.2.19.
No model, API keys, database, or external service is required after installation.
The agent nodes are deterministic stand-ins, not autonomous LLM agents.
These examples isolate coordination so learners can inspect every decision.

## Run with uv

From the extracted langgraph_patterns directory:

```bash
uv run --with langgraph==1.2.19 01_parallel.py
uv run --with langgraph==1.2.19 02_orchestrator_workers.py
uv run --with langgraph==1.2.19 03_supervisor.py
uv run --with langgraph==1.2.19 04_network.py
```

Alternatively install requirements in your Python environment:

```bash
python -m pip install -r requirements.txt
python 01_parallel.py
```

## 1. Parallelization

START fans out to count_words and detect_urgency. Both read the same text.
They write different state keys, so no reducer is necessary. The list-source
edge waits for both branches before combine runs once.
Expected final output: Words=5, urgent=True.
Branch print order is not guaranteed. Parallel scheduling does not imply CPU
speedup for Python CPU-bound work; this pattern is useful for independent I/O.

## 2. Orchestrator-Workers

orchestrator parses a service list into tasks; dispatch uses Send to create
one worker invocation per task. Unlike the fixed branches in example 1,
the number of workers depends on the input. Each worker receives only its
own service and contributes one item to the shared results channel.
Annotated[..., operator.add] merges concurrent writes instead of replacing
results. synthesize runs after the worker superstep and sorts the result.
Empty input goes directly to synthesize; duplicate service names are removed.

Expected report:

```
catalog: SLOW
checkout: DOWN
payments: OK
```

## 3. Supervisor

supervisor -> researcher -> supervisor -> analyst -> supervisor -> END.
All routing decisions belong to the supervisor. Specialists return state
updates and return control through their fixed edge to the supervisor.
Command combines a state update and a routing decision. The supervisor uses
state to avoid repeatedly scheduling already completed work.

Expected answer: Likely application overload; investigate capacity.
The metrics are mock data, not a real diagnosis.

## 4. Network

Each peer selects its next destination with Command. There is no central
supervisor. The example supports diagnostics -> repair, diagnostics -> review,
repair -> review, and review -> repair or END. A network need not connect
every possible pair of nodes.

Default trace: diagnostics -> repair -> review -> repair -> review -> END.
The first repair deliberately fails; the second succeeds. The business rule
limits retries, while recursion_limit is an additional execution safeguard.
An unrecognized issue ends with human escalation. No actual system is changed.

## Important distinctions

- Parallelization: independent work with a known, fixed graph structure.
- Orchestrator-workers: a runtime plan determines the work items.
- Supervisor: centralized selection of the next specialist.
- Network: specialists hand control directly to peers.

These patterns can be combined. A supervisor can invoke parallel workers,
for example. Examples 3 and 4 intentionally use explicit state fields rather
than a chat history: multi-agent coordination does not require MessagesState.

## Turn the stand-ins into LLM agents

Inside researcher or analyst, invoke a configured model or a LangChain agent
and map its response back to the appropriate state field. Keep the graph
wiring unchanged. For an LLM supervisor, use validated structured output with
an allowlisted destination and map that destination to Command(goto=...).
For an LLM orchestrator, validate a structured list of tasks before Send.
Keep completion checks and bounded retry rules outside model discretion.

## Small training exercises

1. Add a third parallel branch that detects the word 'checkout'.
2. Add 'inventory' to the orchestrator request and observe UNKNOWN.
3. Add a writer specialist after the analyst in the supervisor graph.
4. Make every repair fail and verify the network escalates after two attempts.

## References

https://docs.langchain.com/oss/python/langgraph/workflows-agents
https://docs.langchain.com/oss/python/langgraph/graph-api

All four main examples were executed successfully. Extra checks covered empty
orchestrator input, duplicate/unknown services, and network escalation.
