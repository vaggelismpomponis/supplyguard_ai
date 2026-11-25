Building and Testing Stateful ReAct Agents with Tools

"- The tool node and integrating tools into a graph (prebuilt ToolNode)
 - Pattern: ReAct (reasoning + acting loop) built from scratch
 - State and short-term memory: the conversational loop
 - Testing nodes and tools in isolation"


## Lesson 1 — ToolNode 

 

Teaching points:
- `@tool` turns a typed function and docstring into a callable tool with a schema.
- A tool call is structured data in an `AIMessage`, not executable Python text.
- `ToolNode` executes the named tool and returns a `ToolMessage`.
- `tool_call_id` links the result to the request. Expected price: `900.0`.
- The tiny graph supplies the runtime expected by the current ToolNode implementation.

Exercise: request the monitor price, then supply two tool calls in the same AIMessage. Match returned results by call ID. Use independent calls; the total tool cannot consume a price result until a later step.

## Lesson 2 — ReAct loop from scratch 


The control flow is built explicitly with StateGraph, nodes and edges; it does not use an agent factory. The tool executor itself is the prebuilt ToolNode introduced in lesson 1.

1. The agent node reads the conversation and calls a model with bound tool schemas.
2. `tools_condition` selects the tool node when the model returns tool calls.
3. The tool node appends results; its edge returns control to the agent.
4. A response without tool calls terminates the graph.

For three laptops, the expected total is EUR 2700, excluding tax and shipping. Model phrasing and exact call sequence may vary. The printed trace shows observable calls/results and final answers, not private chain-of-thought. ReAct here means iterative model decisions, actions, and observations.

`recursion_limit` bounds graph supersteps, not tokens or seconds. Model requests also have a timeout and bounded retries. `handle_tool_errors=True` is explicit for the classroom so tool failures become observations the model can respond to; production error handling should avoid exposing internal exception details.

Exercise: ask for an unknown product. Observe the error ToolMessage and the model's response. Add a read-only `get_stock` tool and ask for both price and availability.

## Lesson 3 — State and conversation memory 


`MessagesState` includes a message reducer: new messages append, while messages with an existing ID update that message. Nodes therefore return new messages only.

State accumulates within a single graph invocation even without a checkpointer. The checkpointer makes state available across separate invocations using the same thread ID. Send only the new user message on each turn.

Expected behavior:
- `customer-a`: 3 laptops cost EUR 2700; the follow-up for 5 costs EUR 4500.
- `customer-b`: has no earlier product request and should not claim one.

`InMemorySaver` is process-local and disappears when Python exits. It is short-term thread memory, not durable or shared user memory. Reusing a thread ID reuses that conversation. Real applications must authorize thread access and manage context growth; a thread ID is not authentication. Use a database-backed checkpointer when persistence across process restarts is required.

Exercise: give the follow-up a different thread ID. Explain why the product context is missing. Then discuss what would happen if two users accidentally shared a thread ID.

## Lesson 4 — Testing in isolation 

The 11 test cases cover tool calculations, invalid inputs, call IDs, tool error observations, routing, agent-node inputs and outputs, a complete two-tool loop, conversation retention, thread isolation, and the graph step limit.

Tool functions and the agent node are tested independently. ToolNode uses a one-node harness to supply graph runtime. Complete-graph tests inject a mock model with scripted responses, so they are repeatable and need no network or credentials. These verify orchestration, not the quality of a real model's reasoning or tool selection.

Exercise: change the total calculation to addition and confirm a test fails. Restore it. Add a test for a monitor order of quantity 4 (EUR 1000).