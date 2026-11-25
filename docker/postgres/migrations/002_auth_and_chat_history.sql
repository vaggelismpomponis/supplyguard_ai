-- ==============================================================================
-- SupplyGuard AI: Authentication & Role-Scoped Chat History Migration
-- File: docker/postgres/migrations/002_auth_and_chat_history.sql
--
-- Non-destructive upgrade migration for existing PostgreSQL volumes (postgres_data).
-- Adds owner_user_id/owner_role/access_scope to thread_states and creates
-- app_users plus Chainlit chat history tables (chat_*).
-- ==============================================================================

BEGIN;

-- 1. Add user & role ownership columns to thread_states
ALTER TABLE IF EXISTS thread_states ADD COLUMN IF NOT EXISTS owner_user_id TEXT;
ALTER TABLE IF EXISTS thread_states ADD COLUMN IF NOT EXISTS owner_role TEXT;
ALTER TABLE IF EXISTS thread_states ADD COLUMN IF NOT EXISTS access_scope TEXT;

CREATE INDEX IF NOT EXISTS idx_thread_states_owner_role
    ON thread_states(owner_user_id, owner_role, updated_at DESC);

-- 2. Authenticated operator accounts & hashed credentials
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

-- 3. Role-scoped Chainlit chat history tables
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

CREATE INDEX IF NOT EXISTS idx_chat_threads_user_role ON chat_threads(user_id, role, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_threads_identifier ON chat_threads(user_identifier, role);

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

CREATE INDEX IF NOT EXISTS idx_chat_steps_thread_created ON chat_steps(thread_id, created_at ASC);

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

CREATE INDEX IF NOT EXISTS idx_chat_elements_thread ON chat_elements(thread_id);

CREATE TABLE IF NOT EXISTS chat_feedbacks (
    id TEXT PRIMARY KEY,
    for_id TEXT NOT NULL,
    thread_id TEXT REFERENCES chat_threads(id) ON DELETE CASCADE,
    value INTEGER NOT NULL,
    comment TEXT
);

COMMIT;
