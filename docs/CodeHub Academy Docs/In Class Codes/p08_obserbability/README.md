# LangGraph observability lab
Run from the extracted folder. Each numbered script runs independently with no arguments.
Python 3.11+ and uv recommended. Scripts 01–03 use only the standard library.
For 04–08, use uv run --with langgraph SCRIPT.py or install langgraph in your project.

## Local
Run 01, 02, 03 and 04 in order. Observe the event, elapsed time, related run IDs and node update. Script 03 simulates run IDs locally. Script 04 shows live updates in the terminal.

## LangSmith
Create a local .env file using the example below, replacing the placeholder with your LangSmith API key. For an agent-based workspace, set LANGSMITH_AGENT_ID and LANGSMITH_AGENT_ENVIRONMENT instead of LANGSMITH_PROJECT. Use your workspace endpoint if applicable.

    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY=your-key
    LANGSMITH_PROJECT=support-ticket-lab
    LANGCHAIN_CALLBACKS_BACKGROUND=false

Run each of 05–08 with the environment loaded, for example:

    uv run --env-file .env --with langgraph 05_zero_code_trace.py

05: Open the newest trace. Compare the root input and output with the classify child run.
06: Open 06-inspect-latency in Details. Compare classify and assign. Which one accounts for the 300 ms delay?
07: Open the failed 07-inspect-error trace. Find the failing child and its input. Compare it with the successful invocation.
08: Filter for tag support-ticket and metadata school = north. Verify that the matching root run returns network.

All examples use synthetic text. No LLM or PostgreSQL setup is needed.

