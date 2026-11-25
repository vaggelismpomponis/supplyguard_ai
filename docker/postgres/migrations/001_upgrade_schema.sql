-- ==============================================================================
-- SupplyGuard AI: PostgreSQL Database Schema Upgrade Migration
-- File: docker/postgres/migrations/001_upgrade_schema.sql
--
-- Non-destructive upgrade migration for existing PostgreSQL volumes (postgres_data).
-- Adds thread_states, incident_memories, SupplyGuard audit_log columns,
-- purchase_orders.action_id, LangGraph checkpoints, and vector indexes.
-- ==============================================================================

BEGIN;

-- 1. Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Durable Thread Case State Table
CREATE TABLE IF NOT EXISTS thread_states (
    thread_id TEXT PRIMARY KEY,
    case_state JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_thread_states_updated_at ON thread_states(updated_at DESC);

-- 3. Audit Log Table (Idempotency Guard & Audit Trail)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action_id VARCHAR(64) UNIQUE NOT NULL,
    thread_id VARCHAR(128) NOT NULL,
    action_type VARCHAR(64) NOT NULL,
    actor VARCHAR(128),
    component_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    parameters JSONB DEFAULT '{}',
    rationale TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor VARCHAR(128);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS component_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_audit_log_action_id ON audit_log(action_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_thread_id ON audit_log(thread_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_status ON audit_log(status);

-- 4. LangGraph Checkpoints (PostgresSaver)
CREATE TABLE IF NOT EXISTS checkpoint_migrations (
    v INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    task_path TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_blobs_thread_id ON checkpoint_blobs(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread_id ON checkpoint_writes(thread_id);

-- 5. Policy Chunks & Incident Memories Vector Stores
CREATE TABLE IF NOT EXISTS policy_chunks (
    doc_id VARCHAR(64) NOT NULL,
    effective_date DATE NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    embedding vector(1536) NOT NULL,
    access_scope VARCHAR(32) DEFAULT 'procurement',
    metadata JSONB DEFAULT '{}',
    doc_type VARCHAR(32),
    supplier_id VARCHAR(32),
    version INTEGER,
    trusted BOOLEAN NOT NULL DEFAULT TRUE,
    security_flags TEXT[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (doc_id, effective_date, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_policy_doc_effective ON policy_chunks(doc_id, effective_date DESC);
CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding ON policy_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS incident_memories (
    memory_id         TEXT PRIMARY KEY,
    kind              TEXT NOT NULL CHECK (kind IN ('historical_case', 'approved_memory')),
    case_id           TEXT NOT NULL,
    supplier_id       TEXT,
    component_id      TEXT,
    component_type    TEXT,
    disruption_type   TEXT,
    delay_days        INT,
    severity          TEXT CHECK (severity IN ('minor', 'moderate', 'major')),
    strategy          TEXT,
    recovery_cost_eur NUMERIC(14, 2),
    outcome           TEXT,
    access_scope      TEXT NOT NULL,
    content           TEXT NOT NULL,
    embedding         vector(1536) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incident_memories_embedding ON incident_memories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_incident_memories_filters ON incident_memories(component_type, severity);

-- 6. SupplyGuard purchase_orders idempotency tracking
ALTER TABLE IF EXISTS purchase_orders ADD COLUMN IF NOT EXISTS action_id VARCHAR(64) UNIQUE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_purchase_orders_action_id_unique ON purchase_orders(action_id);

COMMIT;
