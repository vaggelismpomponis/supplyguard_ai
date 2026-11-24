"""LangSmith tracing setup for the Deep Agents runs (#82).

One helper, ``run_config``, builds the LangChain ``RunnableConfig`` that every caller of the agent
passes to ``invoke`` / ``stream`` (Chainlit, evaluation, red-team, restart scenario). It maps
``thread_id`` to the Chainlit session for the checkpointer and puts the same id in the trace
metadata, so LangSmith groups all turns of a case in one thread view, with subagent and tool runs
nested underneath.

Check the setup (no agent needed):

    python -m eval.tracing            # print the effective settings
    python -m eval.tracing --ping     # also send one small test trace to LangSmith

Settings come from the environment (.env.example): LANGSMITH_TRACING, LANGSMITH_API_KEY,
LANGSMITH_ENDPOINT, LANGSMITH_PROJECT. Nothing is hardcoded.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Iterable, Optional

DEFAULT_PROJECT = "supplyguard-ai"
BASE_TAGS = ("supplyguard",)
_PLACEHOLDER_PREFIX = "your_"


def tracing_enabled() -> bool:
    """True when LANGSMITH_TRACING (or the older LANGCHAIN_TRACING_V2) is switched on."""
    flag = os.environ.get("LANGSMITH_TRACING") or os.environ.get("LANGCHAIN_TRACING_V2") or ""
    return flag.strip().lower() in ("true", "1", "yes")


def api_key_configured() -> bool:
    key = os.environ.get("LANGSMITH_API_KEY", "").strip()
    return bool(key) and not key.startswith(_PLACEHOLDER_PREFIX)


def configure_tracing() -> dict[str, Any]:
    """Fill defaults the LangChain stack reads, and report what is effective.

    Only sets variables that are unset; never overrides the user's .env. Tracing stays off when
    the API key is a placeholder, so a fresh clone runs without network calls to LangSmith.
    """
    os.environ.setdefault("LANGSMITH_PROJECT", DEFAULT_PROJECT)
    enabled = tracing_enabled() and api_key_configured()
    if tracing_enabled() and not api_key_configured():
        os.environ["LANGSMITH_TRACING"] = "false"
    return {
        "enabled": enabled,
        "project": os.environ["LANGSMITH_PROJECT"],
        "endpoint": os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        "api_key": "set" if api_key_configured() else "missing or placeholder",
    }


def run_config(
    thread_id: str,
    *,
    case_id: Optional[str] = None,
    user_id: Optional[str] = None,
    role: Optional[str] = None,
    run_name: str = "supplyguard_case",
    tags: Iterable[str] = (),
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """RunnableConfig for one agent call. ``thread_id`` is the Chainlit session id.

    ``metadata.thread_id`` is the key LangSmith uses to group runs into a thread. ``case_id`` and
    the evaluation tags let us filter traces of one evaluation case or experiment.
    """
    meta: dict[str, Any] = {"thread_id": thread_id}
    for key, value in (("case_id", case_id), ("user_id", user_id), ("role", role)):
        if value is not None:
            meta[key] = value
    meta.update(metadata or {})
    all_tags = list(dict.fromkeys([*BASE_TAGS, *tags, *([case_id] if case_id else [])]))
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": run_name,
        "tags": all_tags,
        "metadata": meta,
    }


def ping() -> str:
    """Send one tiny traced run and return its project name. Needs a real API key."""
    from langsmith import traceable

    @traceable(name="tracing_smoke_test", tags=["supplyguard", "smoke-test"])
    def _smoke(text: str) -> str:
        return text.upper()

    _smoke("supplyguard tracing check")  # the background sender flushes it at process exit
    return os.environ["LANGSMITH_PROJECT"]


def main() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ping", action="store_true", help="send one test trace to LangSmith")
    args = parser.parse_args()

    settings = configure_tracing()
    for key, value in settings.items():
        print(f"{key:<9} {value}")
    if not settings["enabled"]:
        print("Tracing is off: set LANGSMITH_TRACING=true and a real LANGSMITH_API_KEY in .env.")
        return 1 if args.ping else 0
    if args.ping:
        project = ping()
        print(f"Sent run 'tracing_smoke_test' to project {project!r}; check it in LangSmith.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
