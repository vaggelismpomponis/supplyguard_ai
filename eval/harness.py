"""Integration contract between the Quality runners and the SupplyGuard agent.

Every Quality script (evaluation run, red-team run, restart scenario, pre-demo check) drives the
agent through the small step API below and reads one ``CaseOutcome`` back. Workflow implements it
once, on top of the Deep Agents graph, and exposes a factory that returns an ``AgentHarness``.

The factory is found through ``SUPPLYGUARD_EVAL_HARNESS`` (``module:function``), by default
``src.agent.eval_harness:build_harness``. Until that module exists the runners stop with a clear
message instead of failing on an import error.

Status values returned by ``pending``:

- ``"clarification"``: the agent asked the user a question and waits for ``reply``.
- ``"approval"``: an ``ApprovalPayload`` waits for ``decide``.
- ``None``: the turn finished.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from typing import Any, Literal, Optional, Protocol, runtime_checkable

from typing_extensions import NotRequired, TypedDict

DEFAULT_HARNESS = "src.agent.eval_harness:build_harness"
HARNESS_ENV = "SUPPLYGUARD_EVAL_HARNESS"

# The procurement manager from src/support-data/config/users.csv: procurement scope, no finance.
DEFAULT_USER = "u-pm-01"

Pending = Optional[Literal["clarification", "approval"]]


class Citation(TypedDict):
    doc_id: str
    effective_date: str


class CaseOutcome(TypedDict):
    """What the evaluators read from a thread after a turn. Field names follow the contracts.

    Lists are cumulative for the thread (everything executed so far), while ``answer`` is the
    reply to the latest turn only, so a follow-up is judged on its own answer.
    """

    thread_id: str
    facts: Optional[dict[str, Any]]  # DisruptionFact.model_dump(), or None if not extracted
    clarification_asked: bool  # the agent paused for clarification in this thread
    impact: Optional[dict[str, Any]]  # OperationalImpact.model_dump() plus the keys below
    # impact extras: "affected_products": list[str], "open_orders_due_within_60d": int
    options: list[dict[str, Any]]  # RecoveryOption.model_dump() for every option compared
    approval_payloads: list[dict[str, Any]]  # every ApprovalPayload shown to the user
    approval_requested: bool  # the agent paused for approval at least once
    executed_action_ids: list[str]  # one entry per call to the procurement MCP, duplicates kept
    executed_before_approval: bool  # an action ran while its status was not "approved"
    tool_calls: list[str]  # names of every tool called, in order (calculators included)
    revenue_at_risk: Optional[float]  # from calculate_revenue_at_risk, never LLM arithmetic
    recovery_cost: Optional[float]  # from calculate_recovery_costs, reported separately
    security_findings: list[str]  # doc ids or short descriptions of flagged injection attempts
    refused: bool  # the agent declined the user's instruction in the latest turn
    citations: list[Citation]
    answer: str  # final assistant message of the latest turn
    action_statuses: NotRequired[dict[str, str]]  # action_id -> pending/approved/executed/rejected


@runtime_checkable
class AgentHarness(Protocol):
    """Step API over the agent. One ``thread_id`` maps to one Chainlit session."""

    def send(self, thread_id: str, message: str, *, user_id: str = DEFAULT_USER) -> Pending:
        """Send a user message (new or existing thread) and run until the next pause."""

    def pending(self, thread_id: str) -> Pending:
        """What the thread waits for now, read from the checkpoint (survives restarts)."""

    def reply(self, thread_id: str, answer: str) -> Pending:
        """Answer a clarification question."""

    def decide(self, thread_id: str, *, approved: bool) -> Pending:
        """Approve or reject the pending ApprovalPayload. Replaying it must not re-execute."""

    def resume(self, thread_id: str) -> Pending:
        """Continue a thread that was interrupted by a crash, from its last checkpoint."""

    def approval_payload(self, thread_id: str) -> Optional[dict[str, Any]]:
        """The ApprovalPayload waiting for a decision, or None."""

    def outcome(self, thread_id: str) -> CaseOutcome:
        """Everything the evaluators need, read from the persisted thread state."""


class HarnessUnavailable(RuntimeError):
    """The agent harness is not implemented yet or cannot be imported."""


def load_harness(spec: Optional[str] = None) -> AgentHarness:
    """Build the harness named by ``spec``, ``$SUPPLYGUARD_EVAL_HARNESS`` or the default."""
    spec = spec or os.environ.get(HARNESS_ENV) or DEFAULT_HARNESS
    module_name, _, attr = spec.partition(":")
    try:
        factory = getattr(importlib.import_module(module_name), attr or "build_harness")
    except (ImportError, AttributeError) as exc:
        raise HarnessUnavailable(
            f"agent harness {spec!r} is not available ({exc}). Workflow provides it once the "
            f"Deep Agents graph exists; see docs/EVALUATION.md#agent-harness."
        ) from exc
    harness = factory()
    if not isinstance(harness, AgentHarness):
        raise HarnessUnavailable(f"{spec!r} did not return an AgentHarness")
    return harness


PAYLOAD_BINDING_FIELDS = (
    "action_type",
    "target_supplier_id",
    "component_id",
    "quantity",
    "unit_price",
    "total_cost",
)


def payload_fingerprint(payload: dict[str, Any]) -> str:
    """Hash of the fields an approval is bound to. Any change gives a different fingerprint."""
    bound = {k: payload.get(k) for k in PAYLOAD_BINDING_FIELDS}
    if hasattr(bound["action_type"], "value"):
        bound["action_type"] = bound["action_type"].value
    raw = json.dumps(bound, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def drive(
    harness: AgentHarness,
    thread_id: str,
    message: str,
    *,
    user_id: str = DEFAULT_USER,
    clarification_reply: Optional[str] = None,
    approval_decision: Optional[str] = None,
    max_pauses: int = 5,
) -> list[str]:
    """Send one message and answer pauses from the example. Returns a short log.

    ``approval_decision`` is ``"approved"``, ``"rejected"`` or None (leave the approval pending,
    which is the safe default: most cases must not execute anything).
    """
    log = []
    waiting = harness.send(thread_id, message, user_id=user_id)
    for _ in range(max_pauses):
        if waiting == "clarification":
            log.append(f"clarification -> {clarification_reply!r}")
            if clarification_reply is None:
                break
            waiting = harness.reply(thread_id, clarification_reply)
        elif waiting == "approval":
            payload = harness.approval_payload(thread_id) or {}
            label = f"{payload.get('target_supplier_id')} x{payload.get('quantity')}"
            log.append(f"approval {label} -> {approval_decision or 'left pending'}")
            if approval_decision is None:
                break
            waiting = harness.decide(thread_id, approved=approval_decision == "approved")
        else:
            break
    return log
