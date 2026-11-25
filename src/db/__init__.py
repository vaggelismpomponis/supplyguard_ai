"""Database, Persistence and Idempotency package for SupplyGuard AI.

Platform Role | Scope: db, docker
"""

from src.db.checkpointer import PostgresSaver
from src.db.connection import (
    get_connection_pool,
    get_db_connection,
    get_db_url,
    get_pooled_connection,
)
from src.db.idempotency import (
    execute_idempotent,
    get_action_record,
    get_action_status,
    is_action_executed,
    load_latest_thread_state,
    load_thread_state,
    record_action,
    save_thread_state,
)

__all__ = [
    "PostgresSaver",
    "get_db_url",
    "get_db_connection",
    "get_connection_pool",
    "get_pooled_connection",
    "record_action",
    "get_action_record",
    "get_action_status",
    "is_action_executed",
    "execute_idempotent",
    "save_thread_state",
    "load_thread_state",
    "load_latest_thread_state",
]
