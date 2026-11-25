"""PostgreSQL-backed Chainlit DataLayer with strict user & role chat history isolation.

Implements `chainlit.data.base.BaseDataLayer` directly on `src.db.connection`
(`psycopg` + `psycopg_pool`) so Chainlit's chat history sidebar, thread resume,
and Incident Report attachments persist in PostgreSQL without requiring extra
database drivers or external object storage.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
import uuid

from psycopg.rows import dict_row

from src.db.auth import ensure_auth_tables
from src.db.connection import get_pooled_connection

if TYPE_CHECKING:
    from chainlit.element import Element, ElementDict
    from chainlit.step import StepDict
    from chainlit.types import Feedback, PaginatedResponse, Pagination, ThreadDict, ThreadFilter
    from chainlit.user import PersistedUser, User

try:
    from chainlit.data.base import BaseDataLayer
    from chainlit.data.utils import queue_until_user_message
    from chainlit.types import PageInfo, PaginatedResponse
    from chainlit.user import PersistedUser
except ImportError:  # pragma: no cover - lightweight unit test stub fallback
    BaseDataLayer = object  # type: ignore[assignment,misc]

    def queue_until_user_message():  # type: ignore[misc]
        def _decorator(fn: Any) -> Any:
            return fn

        return _decorator

    PageInfo = Any  # type: ignore[assignment,misc]
    PaginatedResponse = Any  # type: ignore[assignment,misc]
    PersistedUser = Any  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


def _to_iso(val: Any) -> str:
    if val is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc).isoformat()
        return val.isoformat()
    return str(val)


def _safe_json(val: Any, default: Any) -> Any:
    if val is None:
        return default
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return default
    return val


def _row_to_step_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    meta = _safe_json(row.get("metadata"), {})
    show_inp = row.get("show_input")
    step: Dict[str, Any] = {
        "id": row["id"],
        "name": row.get("name") or "",
        "type": row.get("type") or "undefined",
        "threadId": row["thread_id"],
        "parentId": row.get("parent_id"),
        "streaming": bool(row.get("streaming", False)),
        "waitForAnswer": row.get("wait_for_answer"),
        "isError": row.get("is_error"),
        "metadata": meta,
        "tags": row.get("tags"),
        "input": row.get("input") or "" if show_inp not in (None, "false") else "",
        "output": row.get("output") or "",
        "createdAt": row.get("created_at"),
        "start": row.get("start_time"),
        "end": row.get("end_time"),
        "generation": _safe_json(row.get("generation"), None),
        "showInput": show_inp,
        "language": row.get("language"),
        "feedback": None,
    }
    if row.get("feedback_id"):
        step["feedback"] = {
            "id": row["feedback_id"],
            "forId": row["id"],
            "value": int(row.get("feedback_value", 0)),
            "comment": row.get("feedback_comment"),
        }
    return step


def _row_to_element_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "threadId": row.get("thread_id"),
        "type": row.get("type") or "file",
        "chainlitKey": None,
        "url": row.get("url") or f"/api/elements/{row['thread_id']}/{row['id']}",
        "objectKey": row.get("object_key"),
        "name": row.get("name") or "attachment",
        "props": _safe_json(row.get("props"), {}),
        "display": row.get("display") or "inline",
        "size": row.get("size"),
        "language": row.get("language"),
        "page": row.get("page"),
        "autoPlay": row.get("auto_play"),
        "playerConfig": _safe_json(row.get("player_config"), None),
        "forId": row.get("for_id"),
        "mime": row.get("mime"),
    }


def sanitize_filename(name: str) -> str:
    """Restrict attachment download filenames to safe ASCII tokens."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(name or "attachment").name)
    return cleaned or "attachment"


class SupplyGuardDataLayer(BaseDataLayer):
    """Chainlit DataLayer backed by PostgreSQL with `(user_id, role)` history isolation."""

    def __init__(self, user_thread_limit: int = 200) -> None:
        self.user_thread_limit = user_thread_limit

    # ------------------------------------------------------------------
    # Synchronous PostgreSQL helpers (executed off the asyncio loop)
    # ------------------------------------------------------------------

    def _sync_get_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        if not ensure_auth_tables():
            return None
        with get_pooled_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT u.id,
                           u.identifier,
                           u.created_at,
                           u.metadata,
                           au.user_id AS auth_user_id,
                           au.username AS auth_username,
                           au.display_name AS auth_display_name,
                           au.role AS auth_role,
                           au.access_scope AS auth_scope,
                           au.document_scopes AS auth_doc_scopes,
                           au.factory_access AS auth_factories,
                           au.is_active AS auth_active
                    FROM chat_users u
                    LEFT JOIN app_users au
                           ON au.user_id = u.id OR LOWER(au.username) = LOWER(u.identifier)
                    WHERE LOWER(u.identifier) = LOWER(%s) OR u.id = %s
                    LIMIT 1;
                    """,
                    (identifier, identifier),
                )
                row = cur.fetchone()
        if not row:
            return None
        if row.get("auth_active") is False:
            return None
        meta = dict(_safe_json(row.get("metadata"), {}))
        if row.get("auth_user_id"):
            meta.update(
                {
                    "user_id": row["auth_user_id"],
                    "username": row["auth_username"],
                    "display_name": row["auth_display_name"],
                    "role": row["auth_role"],
                    "access_scope": row["auth_scope"],
                    "document_scopes": list(row.get("auth_doc_scopes") or []),
                    "factory_access": list(row.get("auth_factories") or []),
                }
            )
        return {
            "id": row["id"],
            "identifier": row["identifier"],
            "createdAt": _to_iso(row.get("created_at")),
            "metadata": meta,
            "display_name": meta.get("display_name") or row.get("auth_display_name"),
        }

    def _sync_create_user(
        self,
        identifier: str,
        display_name: Optional[str],
        metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not ensure_auth_tables():
            return None
        existing = self._sync_get_user(identifier)
        meta = dict(metadata or {})
        if display_name and "display_name" not in meta:
            meta["display_name"] = display_name
        user_id = str(meta.get("user_id") or (existing["id"] if existing else str(uuid.uuid4())))
        with get_pooled_connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_users (id, identifier, created_at, metadata)
                        VALUES (%s, %s, CURRENT_TIMESTAMP, %s::jsonb)
                        ON CONFLICT (identifier) DO UPDATE SET
                            metadata = COALESCE(chat_users.metadata, '{}'::jsonb) || EXCLUDED.metadata;
                        """,
                        (user_id, identifier, json.dumps(meta)),
                    )
        return self._sync_get_user(identifier)

    def _resolve_active_user_role(self, cur: Any, user_id: str) -> Optional[Tuple[str, str, str]]:
        """Return `(identifier, active_role, active_scope)` if user exists and is active."""
        cur.execute(
            """
            SELECT u.identifier,
                   COALESCE(au.role, u.metadata->>'role', 'viewer') AS active_role,
                   COALESCE(au.access_scope, u.metadata->>'access_scope', 'public') AS active_scope,
                   COALESCE(au.is_active, TRUE) AS is_active
            FROM chat_users u
            LEFT JOIN app_users au
                   ON au.user_id = u.id OR LOWER(au.username) = LOWER(u.identifier)
            WHERE u.id = %s
            LIMIT 1;
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row or row["is_active"] is False:
            return None
        return str(row["identifier"]), str(row["active_role"]), str(row["active_scope"])

    def _sync_fetch_threads(
        self,
        *,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        enforce_active_role: bool = True,
    ) -> List[Dict[str, Any]]:
        if not ensure_auth_tables():
            return []
        with get_pooled_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if thread_id:
                    cur.execute(
                        """
                        SELECT t.id, t.created_at, t.updated_at, t.name,
                               t.user_id, t.user_identifier, t.role, t.access_scope,
                               t.tags, t.metadata,
                               COALESCE(au.role, u.metadata->>'role', t.role) AS active_role,
                               COALESCE(au.is_active, TRUE) AS is_active
                        FROM chat_threads t
                        LEFT JOIN chat_users u ON u.id = t.user_id
                        LEFT JOIN app_users au
                               ON au.user_id = t.user_id OR LOWER(au.username) = LOWER(t.user_identifier)
                        WHERE t.id = %s
                        LIMIT 1;
                        """,
                        (thread_id,),
                    )
                    rows = cur.fetchall()
                    if enforce_active_role:
                        rows = [
                            r for r in rows
                            if r.get("is_active", True) and r.get("role") == r.get("active_role")
                        ]
                elif user_id:
                    resolved = self._resolve_active_user_role(cur, user_id)
                    if resolved is None:
                        return []
                    _, active_role, _ = resolved
                    cur.execute(
                        """
                        SELECT t.id, t.created_at, t.updated_at, t.name,
                               t.user_id, t.user_identifier, t.role, t.access_scope,
                               t.tags, t.metadata
                        FROM chat_threads t
                        WHERE t.user_id = %s AND t.role = %s
                        ORDER BY t.updated_at DESC NULLS LAST, t.created_at DESC
                        LIMIT %s;
                        """,
                        (user_id, active_role, self.user_thread_limit),
                    )
                    rows = cur.fetchall()
                else:
                    return []

                if not rows:
                    return []

                tids = [r["id"] for r in rows]
                cur.execute(
                    """
                    SELECT s.*, f.id AS feedback_id, f.value AS feedback_value, f.comment AS feedback_comment
                    FROM chat_steps s
                    LEFT JOIN chat_feedbacks f ON f.for_id = s.id
                    WHERE s.thread_id = ANY(%s)
                    ORDER BY s.created_at ASC NULLS LAST;
                    """,
                    (tids,),
                )
                step_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT id, thread_id, for_id, type, chainlit_key, url, object_key,
                           name, display, size, language, page, auto_play, player_config, mime, props
                    FROM chat_elements
                    WHERE thread_id = ANY(%s);
                    """,
                    (tids,),
                )
                elem_rows = cur.fetchall()

        steps_by_thread: Dict[str, List[Dict[str, Any]]] = {tid: [] for tid in tids}
        for sr in step_rows:
            steps_by_thread.setdefault(sr["thread_id"], []).append(_row_to_step_dict(sr))

        elems_by_thread: Dict[str, List[Dict[str, Any]]] = {tid: [] for tid in tids}
        for er in elem_rows:
            elems_by_thread.setdefault(er["thread_id"], []).append(_row_to_element_dict(er))

        threads: List[Dict[str, Any]] = []
        for r in rows:
            tid = r["id"]
            meta = dict(_safe_json(r.get("metadata"), {}))
            meta.setdefault("role", r.get("role"))
            meta.setdefault("access_scope", r.get("access_scope"))
            threads.append(
                {
                    "id": tid,
                    "createdAt": _to_iso(r.get("created_at")),
                    "name": r.get("name"),
                    "userId": r.get("user_id"),
                    "userIdentifier": r.get("user_identifier"),
                    "tags": list(r.get("tags") or []),
                    "metadata": meta,
                    "steps": steps_by_thread.get(tid, []),
                    "elements": elems_by_thread.get(tid, []),
                }
            )
        return threads

    def _sync_update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        if not ensure_auth_tables():
            return
        with get_pooled_connection() as conn:
            with conn.transaction():
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        "SELECT user_id, user_identifier, role, access_scope, name, tags, metadata FROM chat_threads WHERE id = %s;",
                        (thread_id,),
                    )
                    existing = cur.fetchone()

                    resolved_ident = existing["user_identifier"] if existing else ""
                    resolved_role = existing["role"] if existing else "viewer"
                    resolved_scope = existing["access_scope"] if existing else "public"
                    resolved_user_id = existing["user_id"] if existing else None

                    if user_id:
                        resolved_user_id = user_id
                        info = self._resolve_active_user_role(cur, user_id)
                        if info is not None:
                            resolved_ident, active_role, active_scope = info
                            if not existing or not existing.get("user_id"):
                                resolved_role = active_role
                                resolved_scope = active_scope

                    base_meta = dict(_safe_json(existing.get("metadata") if existing else {}, {}))
                    if metadata:
                        for k, v in metadata.items():
                            if v is None:
                                base_meta.pop(k, None)
                            else:
                                base_meta[k] = v
                    base_meta["role"] = resolved_role
                    base_meta["access_scope"] = resolved_scope

                    final_name = name if name is not None else (existing.get("name") if existing else None)
                    if not final_name and base_meta.get("name"):
                        final_name = str(base_meta["name"])
                    if final_name:
                        final_name = final_name.strip().splitlines()[0][:80]

                    merged_tags = list(tags if tags is not None else (existing.get("tags") or [] if existing else []))
                    if resolved_role and resolved_user_id and resolved_role not in merged_tags:
                        merged_tags = [resolved_role, *[t for t in merged_tags if t != resolved_role]]

                    cur.execute(
                        """
                        INSERT INTO chat_threads (
                            id, created_at, updated_at, name, user_id,
                            user_identifier, role, access_scope, tags, metadata
                        )
                        VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (id) DO UPDATE SET
                            updated_at = CURRENT_TIMESTAMP,
                            name = COALESCE(EXCLUDED.name, chat_threads.name),
                            user_id = COALESCE(chat_threads.user_id, EXCLUDED.user_id),
                            user_identifier = COALESCE(NULLIF(chat_threads.user_identifier, ''), EXCLUDED.user_identifier),
                            role = CASE
                                WHEN chat_threads.user_id IS NULL AND EXCLUDED.user_id IS NOT NULL THEN EXCLUDED.role
                                ELSE chat_threads.role
                            END,
                            access_scope = CASE
                                WHEN chat_threads.user_id IS NULL AND EXCLUDED.user_id IS NOT NULL THEN EXCLUDED.access_scope
                                ELSE chat_threads.access_scope
                            END,
                            tags = EXCLUDED.tags,
                            metadata = EXCLUDED.metadata;
                        """,
                        (
                            thread_id,
                            final_name,
                            resolved_user_id,
                            resolved_ident,
                            resolved_role,
                            resolved_scope,
                            merged_tags,
                            json.dumps(base_meta),
                        ),
                    )

    def _sync_upsert_step(self, step_dict: Dict[str, Any]) -> None:
        thread_id = step_dict["threadId"]
        self._sync_update_thread(thread_id)
        if not ensure_auth_tables():
            return

        show_inp = (
            str(step_dict["showInput"]).lower()
            if "showInput" in step_dict and step_dict["showInput"] is not None
            else None
        )
        # Derive a clean thread title from the first user prompt if unnamed
        if step_dict.get("type") == "user_message" and (step_dict.get("output") or "").strip():
            first_line = str(step_dict["output"]).strip().splitlines()[0][:80]
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE chat_threads SET name = COALESCE(NULLIF(name, ''), %s), updated_at = CURRENT_TIMESTAMP WHERE id = %s;",
                            (first_line, thread_id),
                        )

        with get_pooled_connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_steps (
                            id, thread_id, parent_id, name, type, streaming, wait_for_answer,
                            is_error, metadata, tags, input, output, created_at,
                            start_time, end_time, generation, show_input, language
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            parent_id = COALESCE(EXCLUDED.parent_id, chat_steps.parent_id),
                            name = COALESCE(EXCLUDED.name, chat_steps.name),
                            type = EXCLUDED.type,
                            streaming = EXCLUDED.streaming,
                            wait_for_answer = COALESCE(EXCLUDED.wait_for_answer, chat_steps.wait_for_answer),
                            is_error = COALESCE(EXCLUDED.is_error, chat_steps.is_error),
                            metadata = COALESCE(EXCLUDED.metadata, chat_steps.metadata),
                            tags = COALESCE(EXCLUDED.tags, chat_steps.tags),
                            input = COALESCE(EXCLUDED.input, chat_steps.input),
                            output = COALESCE(EXCLUDED.output, chat_steps.output),
                            created_at = COALESCE(EXCLUDED.created_at, chat_steps.created_at),
                            start_time = COALESCE(EXCLUDED.start_time, chat_steps.start_time),
                            end_time = COALESCE(EXCLUDED.end_time, chat_steps.end_time),
                            generation = COALESCE(EXCLUDED.generation, chat_steps.generation),
                            show_input = COALESCE(EXCLUDED.show_input, chat_steps.show_input),
                            language = COALESCE(EXCLUDED.language, chat_steps.language);
                        """,
                        (
                            step_dict["id"],
                            thread_id,
                            step_dict.get("parentId"),
                            step_dict.get("name"),
                            step_dict.get("type") or "undefined",
                            bool(step_dict.get("streaming", False)),
                            step_dict.get("waitForAnswer"),
                            step_dict.get("isError"),
                            json.dumps(step_dict.get("metadata") or {}),
                            step_dict.get("tags"),
                            step_dict.get("input") or "",
                            step_dict.get("output") or "",
                            step_dict.get("createdAt"),
                            step_dict.get("start"),
                            step_dict.get("end"),
                            json.dumps(step_dict["generation"]) if step_dict.get("generation") else None,
                            show_inp,
                            step_dict.get("language"),
                        ),
                    )
                    cur.execute(
                        "UPDATE chat_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = %s;",
                        (thread_id,),
                    )

    def _sync_create_element(self, elem_dict: Dict[str, Any], raw_bytes: Optional[bytes]) -> None:
        if not ensure_auth_tables():
            return
        thread_id = elem_dict.get("threadId")
        if not thread_id:
            return
        self._sync_update_thread(thread_id)
        url = elem_dict.get("url") or f"/api/elements/{thread_id}/{elem_dict['id']}"
        with get_pooled_connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_elements (
                            id, thread_id, for_id, type, chainlit_key, url, object_key,
                            name, display, size, language, page, auto_play,
                            player_config, mime, props, content
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            url = EXCLUDED.url,
                            mime = EXCLUDED.mime,
                            content = COALESCE(EXCLUDED.content, chat_elements.content);
                        """,
                        (
                            elem_dict["id"],
                            thread_id,
                            elem_dict.get("forId"),
                            elem_dict.get("type") or "file",
                            elem_dict.get("chainlitKey"),
                            url,
                            elem_dict.get("objectKey"),
                            elem_dict.get("name") or "attachment",
                            elem_dict.get("display") or "inline",
                            elem_dict.get("size"),
                            elem_dict.get("language"),
                            elem_dict.get("page"),
                            elem_dict.get("autoPlay"),
                            json.dumps(elem_dict["playerConfig"]) if elem_dict.get("playerConfig") else None,
                            elem_dict.get("mime") or "application/octet-stream",
                            json.dumps(elem_dict.get("props") or {}),
                            raw_bytes,
                        ),
                    )

    # ------------------------------------------------------------------
    # BaseDataLayer async interface
    # ------------------------------------------------------------------

    async def get_user(self, identifier: str) -> Optional["PersistedUser"]:
        data = await asyncio.to_thread(self._sync_get_user, identifier)
        if not data:
            return None
        return PersistedUser(
            id=data["id"],
            identifier=data["identifier"],
            createdAt=data["createdAt"],
            metadata=data["metadata"],
            display_name=data.get("display_name"),
        )

    async def create_user(self, user: "User") -> Optional["PersistedUser"]:
        data = await asyncio.to_thread(
            self._sync_create_user,
            user.identifier,
            getattr(user, "display_name", None),
            dict(getattr(user, "metadata", {}) or {}),
        )
        if not data:
            return None
        return PersistedUser(
            id=data["id"],
            identifier=data["identifier"],
            createdAt=data["createdAt"],
            metadata=data["metadata"],
            display_name=data.get("display_name"),
        )

    async def delete_feedback(self, feedback_id: str) -> bool:
        def _run() -> bool:
            if not ensure_auth_tables():
                return False
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM chat_feedbacks WHERE id = %s;", (feedback_id,))
            return True

        return await asyncio.to_thread(_run)

    async def upsert_feedback(self, feedback: "Feedback") -> str:
        fb_id = getattr(feedback, "id", None) or str(uuid.uuid4())

        def _run() -> str:
            if not ensure_auth_tables():
                return fb_id
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO chat_feedbacks (id, for_id, thread_id, value, comment)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                value = EXCLUDED.value,
                                comment = EXCLUDED.comment;
                            """,
                            (
                                fb_id,
                                feedback.forId,
                                getattr(feedback, "threadId", None),
                                int(feedback.value),
                                getattr(feedback, "comment", None),
                            ),
                        )
            return fb_id

        return await asyncio.to_thread(_run)

    @queue_until_user_message()
    async def create_element(self, element: "Element"):
        if not getattr(element, "for_id", None):
            return
        raw_bytes: Optional[bytes] = None
        if getattr(element, "path", None):
            path_obj = Path(str(element.path))
            if path_obj.is_file():
                raw_bytes = await asyncio.to_thread(path_obj.read_bytes)
        elif getattr(element, "content", None) is not None:
            content = element.content
            raw_bytes = content.encode("utf-8") if isinstance(content, str) else bytes(content)

        elem_dict = element.to_dict()
        if raw_bytes is not None and not elem_dict.get("url"):
            elem_dict["url"] = f"/api/elements/{element.thread_id}/{element.id}"
            element.url = elem_dict["url"]
        await asyncio.to_thread(self._sync_create_element, elem_dict, raw_bytes)

    async def get_element(self, thread_id: str, element_id: str) -> Optional["ElementDict"]:
        def _run() -> Optional[Dict[str, Any]]:
            if not ensure_auth_tables():
                return None
            with get_pooled_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT id, thread_id, for_id, type, chainlit_key, url, object_key,
                               name, display, size, language, page, auto_play, player_config, mime, props
                        FROM chat_elements
                        WHERE thread_id = %s AND id = %s
                        LIMIT 1;
                        """,
                        (thread_id, element_id),
                    )
                    row = cur.fetchone()
            return _row_to_element_dict(row) if row else None

        return await asyncio.to_thread(_run)  # type: ignore[return-value]

    @queue_until_user_message()
    async def delete_element(self, element_id: str, thread_id: Optional[str] = None):
        def _run() -> None:
            if not ensure_auth_tables():
                return
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        if thread_id:
                            cur.execute(
                                "DELETE FROM chat_elements WHERE id = %s AND thread_id = %s;",
                                (element_id, thread_id),
                            )
                        else:
                            cur.execute("DELETE FROM chat_elements WHERE id = %s;", (element_id,))

        await asyncio.to_thread(_run)

    @queue_until_user_message()
    async def create_step(self, step_dict: "StepDict"):
        await asyncio.to_thread(self._sync_upsert_step, dict(step_dict))

    @queue_until_user_message()
    async def update_step(self, step_dict: "StepDict"):
        await asyncio.to_thread(self._sync_upsert_step, dict(step_dict))

    @queue_until_user_message()
    async def delete_step(self, step_id: str):
        def _run() -> None:
            if not ensure_auth_tables():
                return
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM chat_feedbacks WHERE for_id = %s;", (step_id,))
                        cur.execute("DELETE FROM chat_steps WHERE id = %s;", (step_id,))

        await asyncio.to_thread(_run)

    async def get_thread_author(self, thread_id: str) -> str:
        def _run() -> str:
            if not ensure_auth_tables():
                return ""
            with get_pooled_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT t.user_identifier, t.role,
                               COALESCE(au.role, u.metadata->>'role', t.role) AS active_role,
                               COALESCE(au.is_active, TRUE) AS is_active
                        FROM chat_threads t
                        LEFT JOIN chat_users u ON u.id = t.user_id
                        LEFT JOIN app_users au
                               ON au.user_id = t.user_id OR LOWER(au.username) = LOWER(t.user_identifier)
                        WHERE t.id = %s
                        LIMIT 1;
                        """,
                        (thread_id,),
                    )
                    row = cur.fetchone()
            if not row or row.get("is_active") is False or row.get("role") != row.get("active_role"):
                raise ValueError(f"Authorized author not found for thread_id {thread_id}")
            return str(row["user_identifier"] or "")

        return await asyncio.to_thread(_run)

    async def delete_thread(self, thread_id: str):
        def _run() -> None:
            if not ensure_auth_tables():
                return
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM chat_threads WHERE id = %s;", (thread_id,))

        await asyncio.to_thread(_run)

    async def list_threads(
        self, pagination: "Pagination", filters: "ThreadFilter"
    ) -> "PaginatedResponse[ThreadDict]":
        if not filters.userId:
            raise ValueError("userId is required")
        all_threads = await asyncio.to_thread(
            self._sync_fetch_threads,
            user_id=filters.userId,
            enforce_active_role=True,
        )

        search_kw = filters.search.lower() if filters.search else None
        fb_val = int(filters.feedback) if filters.feedback is not None else None

        filtered: List[Dict[str, Any]] = []
        for thread in all_threads:
            if search_kw:
                in_name = search_kw in (thread.get("name") or "").lower()
                in_steps = any(
                    search_kw in (step.get("output") or "").lower()
                    or search_kw in (step.get("input") or "").lower()
                    for step in thread.get("steps", [])
                )
                if not (in_name or in_steps):
                    continue
            if fb_val is not None:
                if not any(
                    step.get("feedback") and step["feedback"].get("value") == fb_val
                    for step in thread.get("steps", [])
                ):
                    continue
            filtered.append(thread)

        start = 0
        if pagination.cursor:
            for idx, thr in enumerate(filtered):
                if thr["id"] == pagination.cursor:
                    start = idx + 1
                    break
        end = start + pagination.first
        page = filtered[start:end]
        return PaginatedResponse(
            pageInfo=PageInfo(
                hasNextPage=len(filtered) > end,
                startCursor=page[0]["id"] if page else None,
                endCursor=page[-1]["id"] if page else None,
            ),
            data=page,  # type: ignore[arg-type]
        )

    async def get_thread(self, thread_id: str) -> Optional["ThreadDict"]:
        rows = await asyncio.to_thread(
            self._sync_fetch_threads,
            thread_id=thread_id,
            enforce_active_role=True,
        )
        return rows[0] if rows else None  # type: ignore[return-value]

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        await asyncio.to_thread(
            self._sync_update_thread,
            thread_id,
            name=name,
            user_id=user_id,
            metadata=metadata,
            tags=tags,
        )

    async def build_debug_url(self) -> str:
        return ""

    async def close(self) -> None:
        return None

    async def get_favorite_steps(self, user_id: str) -> List["StepDict"]:
        def _run() -> List[Dict[str, Any]]:
            if not ensure_auth_tables():
                return []
            with get_pooled_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    resolved = self._resolve_active_user_role(cur, user_id)
                    if resolved is None:
                        return []
                    _, active_role, _ = resolved
                    cur.execute(
                        """
                        SELECT s.*, NULL AS feedback_id, NULL AS feedback_value, NULL AS feedback_comment
                        FROM chat_steps s
                        JOIN chat_threads t ON t.id = s.thread_id
                        WHERE t.user_id = %s
                          AND t.role = %s
                          AND COALESCE(s.metadata->>'favorite', 'false') = 'true'
                        ORDER BY s.created_at DESC NULLS LAST;
                        """,
                        (user_id, active_role),
                    )
                    return [_row_to_step_dict(r) for r in cur.fetchall()]

        return await asyncio.to_thread(_run)  # type: ignore[return-value]


def load_element_content_for_user(
    thread_id: str,
    element_id: str,
    user_identifier: str,
) -> Optional[Tuple[bytes, str, str]]:
    """Fetch stored element bytes only if `user_identifier` owns the thread under their active role."""
    if not ensure_auth_tables():
        return None
    with get_pooled_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT e.content, e.mime, e.name
                FROM chat_elements e
                JOIN chat_threads t ON t.id = e.thread_id
                LEFT JOIN chat_users u ON u.id = t.user_id
                LEFT JOIN app_users au
                       ON au.user_id = t.user_id OR LOWER(au.username) = LOWER(t.user_identifier)
                WHERE e.thread_id = %s
                  AND e.id = %s
                  AND (LOWER(t.user_identifier) = LOWER(%s) OR t.user_id = %s)
                  AND COALESCE(au.is_active, TRUE) = TRUE
                  AND t.role = COALESCE(au.role, u.metadata->>'role', t.role)
                LIMIT 1;
                """,
                (thread_id, element_id, user_identifier, user_identifier),
            )
            row = cur.fetchone()
    if not row or row.get("content") is None:
        return None
    raw = bytes(row["content"]) if isinstance(row["content"], memoryview) else row["content"]
    return raw, str(row.get("mime") or "application/octet-stream"), sanitize_filename(str(row.get("name") or "file"))
