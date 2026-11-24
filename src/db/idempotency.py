"""Idempotency guard, audit logging, and thread state persistence for SupplyGuard AI.

Guarantees that state-changing procurement actions (purchase orders, expedites,
stock transfers, schedule updates) are never executed more than once across
container restarts, network replays, or crash recovery.
Adheres to architecture contracts (docs/ARCHITECTURE_CONTRACTS.md) and
the schema defined in docker/postgres/init.sql.

Platform Role | Scope: db, docker
"""

from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Dict, Optional, Tuple

from psycopg.rows import dict_row

from src.db.connection import get_pooled_connection


def _ensure_audit_columns(cur: Any) -> None:
    """Ensure SupplyGuard actor/component_id columns exist on older Postgres volumes."""
    cur.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor VARCHAR(128);")
    cur.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS component_id VARCHAR(64);")


def record_action(
    action_id: str,
    thread_id: str,
    action_type: str,
    actor: Optional[str] = None,
    component_id: Optional[str] = None,
    status: str = "pending",
    parameters: Optional[Dict[str, Any]] = None,
    rationale: str = "",
) -> Dict[str, Any]:
    """Record or update an action proposal in audit_log.

    Guarantees unique action_id tracking per Day 1 contracts.
    Preserves terminal 'executed' status to prevent lifecycle regressions on conflict.
    """
    params_json = json.dumps(parameters or {}, default=str)
    with get_pooled_connection() as conn:
        with conn.transaction():
            with conn.cursor(row_factory=dict_row) as cur:
                _ensure_audit_columns(cur)
                cur.execute(
                    """
                    INSERT INTO audit_log (
                        action_id, thread_id, action_type, actor, component_id,
                        status, parameters, rationale
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (action_id)
                    DO UPDATE SET
                        thread_id = EXCLUDED.thread_id,
                        actor = COALESCE(EXCLUDED.actor, audit_log.actor),
                        component_id = COALESCE(EXCLUDED.component_id, audit_log.component_id),
                        status = CASE
                            WHEN audit_log.status = 'executed' THEN 'executed'
                            ELSE EXCLUDED.status
                        END,
                        rationale = CASE
                            WHEN audit_log.status = 'executed' THEN audit_log.rationale
                            ELSE EXCLUDED.rationale
                        END,
                        parameters = CASE
                            WHEN audit_log.status = 'executed' THEN audit_log.parameters
                            ELSE EXCLUDED.parameters
                        END
                    RETURNING *;
                    """,
                    (
                        action_id,
                        thread_id,
                        action_type,
                        actor,
                        component_id,
                        status,
                        params_json,
                        rationale,
                    ),
                )
                return cur.fetchone()


def get_action_record(action_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the full audit_log row for an action_id."""
    with get_pooled_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM audit_log WHERE action_id = %s;",
                (action_id,),
            )
            return cur.fetchone()


def get_action_status(action_id: str) -> Optional[str]:
    """Retrieve the current lifecycle status of an action."""
    with get_pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM audit_log WHERE action_id = %s;",
                (action_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None


def is_action_executed(action_id: str) -> bool:
    """Check if the action has already been executed."""
    return get_action_status(action_id) == "executed"


def execute_idempotent(
    action_id: str,
    execution_fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Tuple[bool, Any]:
    """Atomically execute an action proposal with strict idempotency guard.

    Guarantees:
    1. Short-circuits if status is already 'executed', preventing duplicate side effects.
    2. Rejects any status other than 'approved' (e.g. 'pending', 'rejected', 'invalidated'),
       ensuring unapproved actions are never invoked.
    3. Serializes execution using PostgreSQL row-level locking (SELECT ... FOR UPDATE).
    4. Persists any returned receipt inside audit_log.parameters atomically with status='executed'.

    Returns:
        (executed, result):
            - (True, result) if action was executed in this call.
            - (False, "already_executed") if action was already completed previously.
    """
    with get_pooled_connection() as conn:
        with conn.transaction():
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT status FROM audit_log WHERE action_id = %s FOR UPDATE;",
                    (action_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Action '{action_id}' not found in audit_log")

                current_status = row["status"]

                if current_status == "executed":
                    return False, "already_executed"

                if current_status != "approved":
                    raise ValueError(
                        f"Action '{action_id}' cannot be executed with status '{current_status}'. "
                        "State-changing actions require explicit human approval."
                    )

                sig = inspect.signature(execution_fn)
                if "action_id" in sig.parameters and "action_id" not in kwargs:
                    kwargs["action_id"] = action_id

                result = execution_fn(*args, **kwargs)

                receipt_data = result.model_dump() if hasattr(result, "model_dump") else result
                if isinstance(receipt_data, dict):
                    cur.execute(
                        """
                        UPDATE audit_log
                        SET status = 'executed',
                            executed_at = CURRENT_TIMESTAMP,
                            parameters = COALESCE(parameters, '{}'::jsonb) || jsonb_build_object('receipt', %s::jsonb)
                        WHERE action_id = %s;
                        """,
                        (json.dumps(receipt_data, default=str), action_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE audit_log
                        SET status = 'executed',
                            executed_at = CURRENT_TIMESTAMP
                        WHERE action_id = %s;
                        """,
                        (action_id,),
                    )
                return True, result


def save_thread_state(thread_id: str, case_state: Dict[str, Any]) -> None:
    """Persist serialized thread state to PostgreSQL for container-restart durability."""
    payload_json = json.dumps(case_state, default=str)
    with get_pooled_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS thread_states (
                        thread_id TEXT PRIMARY KEY,
                        case_state JSONB NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                cur.execute(
                    """
                    INSERT INTO thread_states (thread_id, case_state, updated_at)
                    VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
                    ON CONFLICT (thread_id)
                    DO UPDATE SET
                        case_state = EXCLUDED.case_state,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (thread_id, payload_json),
                )


def load_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Load persisted thread state from PostgreSQL."""
    with get_pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT case_state
                FROM thread_states
                WHERE thread_id = %s;
                """,
                (thread_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])


def load_latest_thread_state() -> Optional[Tuple[str, Dict[str, Any]]]:
    """Load the most recently updated SupplyGuard thread state from PostgreSQL."""
    with get_pooled_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT thread_id, case_state
                FROM thread_states
                ORDER BY updated_at DESC
                LIMIT 1;
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            raw = row[1] if isinstance(row[1], dict) else json.loads(row[1])
            return str(row[0]), raw
