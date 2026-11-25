"""Tests for database-backed authentication and role-scoped chat history."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import unittest
from unittest import mock

from src.agent.deep_agent import SupplyGuardOrchestrator
from src.agent.schemas import AccessScope, UserProfile
from src.db import auth as db_auth
from src.db import chainlit_data_layer as dl_mod


class _FakeCursor:
    def __init__(self, *, rows=None, one=None):
        self._rows = list(rows or [])
        self._one = one
        self.executed: list[tuple[str, tuple | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql: str, params=None):
        self.executed.append((sql, tuple(params) if isinstance(params, (list, tuple)) else params))

    def fetchone(self):
        if self._one is not None:
            return self._one
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor

    @contextmanager
    def transaction(self):
        yield self

    def cursor(self, *args, **kwargs):
        return self._cursor


def _make_fake_pool(cursor: _FakeCursor):
    @contextmanager
    def _pooled():
        yield _FakeConnection(cursor)

    return _pooled


class TestPasswordHashingAndAuthStore(unittest.TestCase):
    def test_scrypt_hash_and_verify_roundtrip(self) -> None:
        digest = db_auth.hash_password("S3cure!Pass")
        self.assertTrue(digest.startswith("scrypt$"))
        self.assertTrue(db_auth.verify_password("S3cure!Pass", digest))
        self.assertFalse(db_auth.verify_password("wrong-pass", digest))
        self.assertFalse(db_auth.verify_password("", digest))
        self.assertFalse(db_auth.verify_password("S3cure!Pass", "malformed"))

    def test_authenticate_user_verifies_hash_and_active_flag(self) -> None:
        pw_hash = db_auth.hash_password("alpha-secret")
        fake_row = {
            "user_id": "u-fc-01",
            "username": "paul.novak",
            "email": "paul.novak@supplyguard.eu",
            "display_name": "Paul Novak",
            "role": "finance_controller",
            "access_scope": "finance",
            "document_scopes": ["public", "internal", "procurement", "finance-confidential"],
            "factory_access": ["F1", "F2", "F3"],
            "password_hash": pw_hash,
            "is_active": True,
        }
        cur = _FakeCursor(one=fake_row)
        with (
            mock.patch.object(db_auth, "ensure_auth_tables", return_value=True),
            mock.patch.object(db_auth, "get_pooled_connection", side_effect=_make_fake_pool(cur)),
        ):
            profile = db_auth.authenticate_user("paul.novak@supplyguard.eu", "alpha-secret")
            self.assertIsNotNone(profile)
            self.assertEqual(profile.user_id, "u-fc-01")
            self.assertEqual(profile.role, "finance_controller")
            self.assertTrue(profile.can_view_finance_confidential)

            bad = db_auth.authenticate_user("paul.novak", "wrong-password")
            self.assertIsNone(bad)

    def test_seed_users_skips_when_env_passwords_unset(self) -> None:
        with (
            mock.patch.object(db_auth, "ensure_auth_tables", return_value=True),
            mock.patch.dict("os.environ", {}, clear=True),
        ):
            seeded = db_auth.seed_users_from_csv()
            self.assertEqual(seeded, 0)


    def test_connection_pool_validates_stale_connections(self) -> None:
        from psycopg_pool import ConnectionPool
        from pathlib import Path
        conn_py = (Path(__file__).resolve().parent.parent / "src" / "db" / "connection.py").read_text(encoding="utf-8")
        self.assertIn("check=ConnectionPool.check_connection", conn_py)
        self.assertTrue(hasattr(ConnectionPool, "check_connection"))


class TestRoleScopedDataLayerAndOrchestrator(unittest.IsolatedAsyncioTestCase):
    async def test_list_threads_filters_by_active_user_and_role(self) -> None:
        now = datetime.now(timezone.utc)

        class _SeqCursor(_FakeCursor):
            def __init__(self) -> None:
                super().__init__()
                self.calls = 0

            def fetchone(self):
                return {
                    "identifier": "maria.keller",
                    "active_role": "procurement_manager",
                    "active_scope": "procurement",
                    "is_active": True,
                }

            def fetchall(self):
                self.calls += 1
                if self.calls == 1:
                    return [
                        {
                            "id": "thr-pm-1",
                            "created_at": now,
                            "updated_at": now,
                            "name": "MC-17 delay",
                            "user_id": "u-pm-01",
                            "user_identifier": "maria.keller",
                            "role": "procurement_manager",
                            "access_scope": "procurement",
                            "tags": ["procurement_manager"],
                            "metadata": {},
                        }
                    ]
                if self.calls == 2:
                    return [
                        {
                            "id": "step-1",
                            "thread_id": "thr-pm-1",
                            "parent_id": None,
                            "name": "Maria Keller",
                            "type": "user_message",
                            "streaming": False,
                            "wait_for_answer": None,
                            "is_error": None,
                            "metadata": {},
                            "tags": None,
                            "input": "",
                            "output": "Atlas MC-17 12 day delay",
                            "created_at": now.isoformat(),
                            "start_time": None,
                            "end_time": None,
                            "generation": None,
                            "show_input": None,
                            "language": None,
                            "feedback_id": None,
                            "feedback_value": None,
                            "feedback_comment": None,
                        }
                    ]
                return []

        cur = _SeqCursor()
        layer = dl_mod.SupplyGuardDataLayer()
        with (
            mock.patch.object(dl_mod, "ensure_auth_tables", return_value=True),
            mock.patch.object(dl_mod, "get_pooled_connection", side_effect=_make_fake_pool(cur)),
        ):
            threads = await asyncio_to_thread_helper(
                layer._sync_fetch_threads,
                user_id="u-pm-01",
                enforce_active_role=True,
            )

        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["id"], "thr-pm-1")
        self.assertEqual(threads[0]["metadata"]["role"], "procurement_manager")
        # Verify the thread listing query strictly filtered by user_id AND role
        thread_queries = [sql for sql, _ in cur.executed if "FROM chat_threads t" in sql]
        self.assertTrue(any("t.user_id = %s AND t.role = %s" in q for q in thread_queries))

    def test_downgraded_role_hidden_from_get_thread(self) -> None:
        now = datetime.now(timezone.utc)
        cur = _FakeCursor(
            rows=[
                {
                    "id": "thr-fin-1",
                    "created_at": now,
                    "updated_at": now,
                    "name": "Margin analysis",
                    "user_id": "u-fc-01",
                    "user_identifier": "paul.novak",
                    "role": "finance_controller",
                    "access_scope": "finance",
                    "tags": ["finance_controller"],
                    "metadata": {},
                    "active_role": "viewer",
                    "is_active": True,
                }
            ]
        )
        layer = dl_mod.SupplyGuardDataLayer()
        with (
            mock.patch.object(dl_mod, "ensure_auth_tables", return_value=True),
            mock.patch.object(dl_mod, "get_pooled_connection", side_effect=_make_fake_pool(cur)),
        ):
            threads = layer._sync_fetch_threads(thread_id="thr-fin-1", enforce_active_role=True)
        self.assertEqual(threads, [])

    def test_orchestrator_enforces_user_and_role_isolation(self) -> None:
        orch = SupplyGuardOrchestrator(use_postgres=False)
        pm = UserProfile(
            user_id="u-pm-01",
            name="Maria Keller",
            role="procurement_manager",
            access_scope=AccessScope.PROCUREMENT,
            document_scopes=["public", "internal", "procurement"],
            factory_access=["F1", "F2", "F3"],
        )
        fc = UserProfile(
            user_id="u-fc-01",
            name="Paul Novak",
            role="finance_controller",
            access_scope=AccessScope.FINANCE,
            document_scopes=["public", "internal", "procurement", "finance-confidential"],
            factory_access=["F1", "F2", "F3"],
        )
        pm_downgraded = pm.model_copy(update={"role": "viewer", "access_scope": AccessScope.PUBLIC, "document_scopes": ["public"]})

        orch.handle_message(
            "thr-pm-secret",
            "Supplier Atlas Components has announced a 12-day delay for component MC-17.",
            pm,
        )

        # Owner with matching role can read state and latest state
        self.assertIsNotNone(orch.get_state("thr-pm-secret", requester=pm, raise_on_unauthorized=True))
        self.assertIsNotNone(orch.get_latest_state(requester=pm))

        # Another user (even Finance Controller) cannot hijack/resume Maria's thread
        with self.assertRaises(PermissionError):
            orch.get_state("thr-pm-secret", requester=fc, raise_on_unauthorized=True)
        self.assertIsNone(orch.get_latest_state(requester=fc))

        # Same user_id with a changed/downgraded role is also blocked
        with self.assertRaises(PermissionError):
            orch.get_state("thr-pm-secret", requester=pm_downgraded, raise_on_unauthorized=True)
        self.assertIsNone(orch.get_latest_state(requester=pm_downgraded))


async def asyncio_to_thread_helper(fn, *args, **kwargs):
    return fn(*args, **kwargs)


if __name__ == "__main__":
    unittest.main()
