"""Database-backed operator authentication and user store for SupplyGuard AI.

Replaces unauthenticated self-service role switching with salted `scrypt` password
authentication backed by PostgreSQL (`app_users`) and user/role-scoped metadata.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from typing import Any, Dict, Iterable, Optional

from psycopg.rows import dict_row

from src.agent.schemas import AccessScope, UserProfile, load_users_from_csv
from src.db.connection import get_pooled_connection, is_postgres_available

logger = logging.getLogger(__name__)

_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False


def hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
    """Hash a plaintext password using salted hashlib.scrypt."""
    if not password:
        raise ValueError("Password must not be empty")
    raw_salt = salt if salt is not None else secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=raw_salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${raw_salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    """Verify a plaintext password against a stored `scrypt$...` digest in constant time."""
    if not password or not stored_hash:
        return False
    parts = stored_hash.split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n_val = int(parts[1])
        r_val = int(parts[2])
        p_val = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected = bytes.fromhex(parts[5])
    except ValueError:
        return False

    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n_val,
        r=r_val,
        p=p_val,
        dklen=len(expected),
    )
    return hmac.compare_digest(derived, expected)


def _resolve_access_scope(scope_str: Optional[str], role: str, doc_scopes: Iterable[str]) -> AccessScope:
    scopes_lower = {s.lower() for s in doc_scopes}
    norm = (scope_str or "").strip().lower()
    if norm == AccessScope.FINANCE.value or role == "finance_controller" or "finance-confidential" in scopes_lower:
        return AccessScope.FINANCE
    if norm == AccessScope.PROCUREMENT.value or "procurement" in scopes_lower:
        return AccessScope.PROCUREMENT
    return AccessScope.PUBLIC


def profile_from_user_row(row: Dict[str, Any]) -> UserProfile:
    """Convert an `app_users` database row into a `UserProfile` domain model."""
    role = str(row["role"]).strip()
    doc_scopes = [str(s).strip() for s in (row.get("document_scopes") or ["public"]) if str(s).strip()]
    factories = [str(f).strip() for f in (row.get("factory_access") or []) if str(f).strip()]
    return UserProfile(
        user_id=str(row["user_id"]).strip(),
        name=str(row["display_name"]).strip(),
        role=role,
        access_scope=_resolve_access_scope(row.get("access_scope"), role, doc_scopes),
        document_scopes=doc_scopes or ["public"],
        factory_access=factories,
        username=str(row.get("username") or row["user_id"]).strip(),
        email=str(row.get("email") or "").strip() or None,
    )


def ensure_auth_tables(*, force: bool = False) -> bool:
    """Idempotently ensure auth and Chainlit chat history tables exist in PostgreSQL."""
    global _SCHEMA_READY
    if _SCHEMA_READY and not force:
        return True
    with _SCHEMA_LOCK:
        if _SCHEMA_READY and not force:
            return True
        if not is_postgres_available():
            return False
        ddl = """
        ALTER TABLE IF EXISTS thread_states ADD COLUMN IF NOT EXISTS owner_user_id TEXT;
        ALTER TABLE IF EXISTS thread_states ADD COLUMN IF NOT EXISTS owner_role TEXT;
        ALTER TABLE IF EXISTS thread_states ADD COLUMN IF NOT EXISTS access_scope TEXT;
        CREATE INDEX IF NOT EXISTS idx_thread_states_owner_role
            ON thread_states(owner_user_id, owner_role, updated_at DESC);

        CREATE TABLE IF NOT EXISTS app_users (
            user_id VARCHAR(64) PRIMARY KEY,
            username VARCHAR(128) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            role VARCHAR(64) NOT NULL,
            access_scope VARCHAR(64) NOT NULL,
            document_scopes TEXT[] NOT NULL DEFAULT '{}',
            factory_access TEXT[] NOT NULL DEFAULT '{}',
            password_hash TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users(role);

        CREATE TABLE IF NOT EXISTS chat_users (
            id TEXT PRIMARY KEY,
            identifier TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS chat_threads (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            name TEXT,
            user_id TEXT REFERENCES chat_users(id) ON DELETE CASCADE,
            user_identifier TEXT NOT NULL,
            role TEXT NOT NULL,
            access_scope TEXT NOT NULL,
            tags TEXT[] DEFAULT '{}',
            metadata JSONB NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_chat_threads_user_role
            ON chat_threads(user_id, role, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_chat_threads_identifier
            ON chat_threads(user_identifier, role);

        CREATE TABLE IF NOT EXISTS chat_steps (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
            parent_id TEXT,
            name TEXT,
            type TEXT NOT NULL,
            streaming BOOLEAN DEFAULT FALSE,
            wait_for_answer BOOLEAN,
            is_error BOOLEAN,
            metadata JSONB DEFAULT '{}',
            tags TEXT[],
            input TEXT DEFAULT '',
            output TEXT DEFAULT '',
            created_at TEXT,
            start_time TEXT,
            end_time TEXT,
            generation JSONB,
            show_input TEXT,
            language TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_chat_steps_thread_created
            ON chat_steps(thread_id, created_at ASC);

        CREATE TABLE IF NOT EXISTS chat_elements (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
            for_id TEXT,
            type TEXT NOT NULL,
            chainlit_key TEXT,
            url TEXT,
            object_key TEXT,
            name TEXT NOT NULL,
            display TEXT,
            size TEXT,
            language TEXT,
            page INTEGER,
            auto_play BOOLEAN,
            player_config JSONB,
            mime TEXT,
            props JSONB DEFAULT '{}',
            content BYTEA
        );
        CREATE INDEX IF NOT EXISTS idx_chat_elements_thread
            ON chat_elements(thread_id);

        CREATE TABLE IF NOT EXISTS chat_feedbacks (
            id TEXT PRIMARY KEY,
            for_id TEXT NOT NULL,
            thread_id TEXT REFERENCES chat_threads(id) ON DELETE CASCADE,
            value INTEGER NOT NULL,
            comment TEXT
        );
        """
        with get_pooled_connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(ddl)
        _SCHEMA_READY = True
        return True


def upsert_user(
    profile: UserProfile,
    password: str,
    *,
    is_active: bool = True,
    overwrite_password: bool = False,
) -> None:
    """Create or update an operator account in `app_users` and mirror metadata into `chat_users`."""
    ensure_auth_tables()
    username = (profile.username or profile.user_id).strip().lower()
    email = (profile.email or f"{username}@supplyguard.eu").strip().lower()
    pw_hash = hash_password(password)
    meta = {
        "user_id": profile.user_id,
        "role": profile.role,
        "access_scope": profile.access_scope.value,
        "document_scopes": list(profile.document_scopes),
        "factory_access": list(profile.factory_access),
        "display_name": profile.name,
        "username": username,
        "email": email,
    }
    password_update_sql = "password_hash = EXCLUDED.password_hash," if overwrite_password else ""
    with get_pooled_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO app_users (
                        user_id, username, email, display_name, role,
                        access_scope, document_scopes, factory_access,
                        password_hash, is_active, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        email = EXCLUDED.email,
                        display_name = EXCLUDED.display_name,
                        role = EXCLUDED.role,
                        access_scope = EXCLUDED.access_scope,
                        document_scopes = EXCLUDED.document_scopes,
                        factory_access = EXCLUDED.factory_access,
                        {password_update_sql}
                        is_active = EXCLUDED.is_active,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        profile.user_id,
                        username,
                        email,
                        profile.name,
                        profile.role,
                        profile.access_scope.value,
                        list(profile.document_scopes),
                        list(profile.factory_access),
                        pw_hash,
                        is_active,
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO chat_users (id, identifier, created_at, metadata)
                    VALUES (%s, %s, CURRENT_TIMESTAMP, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        identifier = EXCLUDED.identifier,
                        metadata = EXCLUDED.metadata;
                    """,
                    (profile.user_id, username, json.dumps(meta)),
                )


def _resolve_seed_password(role: str) -> Optional[str]:
    """Read initial password for a role strictly from environment variables."""
    role_env_key = f"AUTH_PASSWORD_{role.upper()}"
    specific = (os.getenv(role_env_key) or "").strip()
    if specific:
        return specific
    shared = (os.getenv("AUTH_DEMO_DEFAULT_PASSWORD") or "").strip()
    if shared:
        return shared
    return None


def seed_users_from_csv(*, overwrite_passwords: bool = False) -> int:
    """Seed operator accounts defined in `config/users.csv` into `app_users`."""
    if not ensure_auth_tables():
        logger.warning("PostgreSQL unavailable; skipping app_users seed.")
        return 0

    catalog = load_users_from_csv()
    unique_profiles: Dict[str, UserProfile] = {}
    for prof in catalog.values():
        unique_profiles[prof.user_id] = prof

    seeded = 0
    missing_pw_roles: list[str] = []
    for prof in unique_profiles.values():
        pw = _resolve_seed_password(prof.role)
        if not pw:
            missing_pw_roles.append(prof.role)
            continue
        upsert_user(prof, pw, is_active=True, overwrite_password=overwrite_passwords)
        seeded += 1

    if missing_pw_roles:
        logger.warning(
            "Skipped seeding passwords for roles %s because AUTH_DEMO_DEFAULT_PASSWORD / AUTH_PASSWORD_<ROLE> are unset.",
            sorted(set(missing_pw_roles)),
        )
    return seeded


def authenticate_user(username_or_email: str, password: str) -> Optional[UserProfile]:
    """Authenticate an operator by username/email/user_id and password against `app_users`."""
    ident = (username_or_email or "").strip()
    if not ident or not password:
        return None
    if not ensure_auth_tables():
        return None

    with get_pooled_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT user_id, username, email, display_name, role, access_scope,
                       document_scopes, factory_access, password_hash, is_active
                FROM app_users
                WHERE (LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s) OR user_id = %s)
                  AND is_active = TRUE
                LIMIT 1;
                """,
                (ident, ident, ident),
            )
            row = cur.fetchone()

    if not row or not verify_password(password, row.get("password_hash")):
        return None
    return profile_from_user_row(row)


def get_user_by_id(user_id: str) -> Optional[UserProfile]:
    """Fetch the active `UserProfile` for a persisted `user_id` or `username`."""
    ident = (user_id or "").strip()
    if not ident or not ensure_auth_tables():
        return None
    with get_pooled_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT user_id, username, email, display_name, role, access_scope,
                       document_scopes, factory_access, is_active
                FROM app_users
                WHERE (user_id = %s OR LOWER(username) = LOWER(%s))
                  AND is_active = TRUE
                LIMIT 1;
                """,
                (ident, ident),
            )
            row = cur.fetchone()
    if not row:
        return None
    return profile_from_user_row(row)
