-- ==============================================================================
-- SupplyGuard AI: PostgreSQL + pgvector Initialization Script
-- Executed automatically on initial container startup (/docker-entrypoint-initdb.d)
-- Scope: db | Platform & Knowledge Roles | Target: Issues #32, #33, #68
-- ==============================================================================

-- 1. Enable pgvector extension for semantic policy & document search
CREATE EXTENSION IF NOT EXISTS vector;

-- ==============================================================================
-- 2. Durable Thread Case State Table
-- Persists serialized SupplyGuard case states across container restarts
-- ==============================================================================
CREATE TABLE IF NOT EXISTS thread_states (
    thread_id TEXT PRIMARY KEY,
    owner_user_id TEXT,
    owner_role TEXT,
    access_scope TEXT,
    case_state JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_thread_states_updated_at ON thread_states(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_thread_states_owner_role ON thread_states(owner_user_id, owner_role, updated_at DESC);

-- ==============================================================================
-- 3. Audit Log & Idempotency Guard Table
-- Audit trail and idempotency guard for all proposed and executed actions
-- Guarantees state-changing operations are not executed twice upon restart
-- ==============================================================================
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

CREATE INDEX IF NOT EXISTS idx_audit_log_action_id ON audit_log(action_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_thread_id ON audit_log(thread_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_status ON audit_log(status);

-- ==============================================================================
-- 4. Deep Agents / LangGraph Checkpoints (Postgres Checkpointer)
-- Supports state serialization, interrupts, human approval, and resume on restart
-- ==============================================================================
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

-- ==============================================================================
-- 5. Policy & Document Chunks Vector Store (pgvector)
-- Stores policy and contract embeddings with metadata and access scopes
-- ==============================================================================
CREATE TABLE IF NOT EXISTS policy_chunks (
    doc_id VARCHAR(64) NOT NULL,
    effective_date DATE NOT NULL,
    chunk_index INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    access_scope VARCHAR(32) DEFAULT 'procurement',
    metadata JSONB DEFAULT '{}',
    doc_type VARCHAR(32),                          -- contract, qualification, supplier_notice, email, ... (#70)
    supplier_id VARCHAR(32),
    version INTEGER,
    trusted BOOLEAN NOT NULL DEFAULT TRUE,         -- FALSE: the text tries to instruct the assistant
    security_flags TEXT[] NOT NULL DEFAULT '{}',   -- e.g. {prompt_injection}
    PRIMARY KEY (doc_id, effective_date, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_policy_doc_effective ON policy_chunks(doc_id, effective_date DESC);
CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding ON policy_chunks USING hnsw (embedding vector_cosine_ops);

-- ==============================================================================
-- 6. SupplyGuard Relational Schema (Structured Synthetic Package)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS upstream_manufacturers (
    upstream_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(10) NOT NULL,
    city VARCHAR(100),
    erp_status VARCHAR(50) NOT NULL,
    upstream_manufacturer_id VARCHAR(32) REFERENCES upstream_manufacturers(upstream_id),
    payment_terms VARCHAR(50),
    certification_status VARCHAR(50),
    certification VARCHAR(100),
    certification_expiry DATE
);

CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);
CREATE INDEX IF NOT EXISTS idx_suppliers_upstream ON suppliers(upstream_manufacturer_id);

CREATE TABLE IF NOT EXISTS factories (
    factory_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    factory_id VARCHAR(32) REFERENCES factories(factory_id)
);

CREATE TABLE IF NOT EXISTS components (
    component_id VARCHAR(64) PRIMARY KEY,
    description TEXT NOT NULL,
    uom VARCHAR(32) NOT NULL,
    standard_cost_eur NUMERIC(12, 4) NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    factory_id VARCHAR(32) REFERENCES factories(factory_id),
    list_price_eur NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS bill_of_materials (
    product_id VARCHAR(64) REFERENCES products(product_id),
    component_id VARCHAR(64) REFERENCES components(component_id),
    qty_per_unit INTEGER NOT NULL,
    PRIMARY KEY (product_id, component_id)
);

CREATE INDEX IF NOT EXISTS idx_bom_component ON bill_of_materials(component_id);

CREATE TABLE IF NOT EXISTS supplier_components (
    supplier_id VARCHAR(32) REFERENCES suppliers(supplier_id),
    component_id VARCHAR(64) REFERENCES components(component_id),
    unit_price_eur NUMERIC(12, 4) NOT NULL,
    lead_time_days INTEGER NOT NULL,
    monthly_capacity_units INTEGER NOT NULL,
    moq_units INTEGER NOT NULL,
    approved_source VARCHAR(16) CHECK (approved_source IN ('yes', 'no', 'alternative')),  -- 'alternative' marks the MC-17 alternates
    PRIMARY KEY (supplier_id, component_id)
);

CREATE INDEX IF NOT EXISTS idx_supplier_comp_component ON supplier_components(component_id);

CREATE TABLE IF NOT EXISTS inventory (
    component_id VARCHAR(64) REFERENCES components(component_id),
    location_id VARCHAR(32) REFERENCES locations(location_id),
    on_hand INTEGER NOT NULL DEFAULT 0,
    reserved INTEGER NOT NULL DEFAULT 0,
    quarantined INTEGER NOT NULL DEFAULT 0,
    usable INTEGER NOT NULL DEFAULT 0,
    last_counted_date DATE,
    PRIMARY KEY (component_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_component ON inventory(component_id);

CREATE TABLE IF NOT EXISTS quarantine_lots (
    id SERIAL PRIMARY KEY,
    component_id VARCHAR(64) REFERENCES components(component_id),
    location_id VARCHAR(32) REFERENCES locations(location_id),
    lot_id VARCHAR(64) NOT NULL,
    qty INTEGER NOT NULL,
    reason TEXT NOT NULL,
    release_expected VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    component_id VARCHAR(64) REFERENCES components(component_id),
    location_id VARCHAR(32) REFERENCES locations(location_id),
    customer_order_id VARCHAR(64) NOT NULL,
    reserved_qty INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    priority_tier INTEGER NOT NULL,
    segment VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS customer_orders (
    order_id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(32) REFERENCES customers(customer_id),
    product_id VARCHAR(64) REFERENCES products(product_id),
    qty INTEGER NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL,
    unit_price_eur NUMERIC(12, 2) NOT NULL,
    revenue_eur NUMERIC(14, 2) NOT NULL,
    customer_priority_tier INTEGER NOT NULL,
    late_penalty_pct_per_week_capped5 NUMERIC(6, 4) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS production_schedule (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(64) REFERENCES products(product_id),
    factory_id VARCHAR(32) REFERENCES factories(factory_id),
    week_start DATE NOT NULL,
    planned_units INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id VARCHAR(64) PRIMARY KEY,
    supplier_id VARCHAR(32) REFERENCES suppliers(supplier_id),
    supplier_name_as_entered VARCHAR(255),
    component_id VARCHAR(64),  -- raw ERP value, no FK: may be blank or non-canonical (e.g. MC096), see data_quality_manifest.csv
    qty INTEGER NOT NULL,
    unit_price_eur NUMERIC(12, 4) NOT NULL,
    order_date DATE NOT NULL,
    promised_date DATE,
    actual_delivery_date DATE,
    status VARCHAR(32) NOT NULL,
    expedite_allowed BOOLEAN DEFAULT FALSE,
    expedite_fee_pct NUMERIC(6, 4) DEFAULT 0,
    expedite_days_gain INTEGER DEFAULT 0,
    action_id VARCHAR(64) UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_po_supplier_comp ON purchase_orders(supplier_id, component_id);

CREATE TABLE IF NOT EXISTS shipment_updates (
    shipment_event_id VARCHAR(64) PRIMARY KEY,
    po_id VARCHAR(64) REFERENCES purchase_orders(po_id),
    supplier_id VARCHAR(32) REFERENCES suppliers(supplier_id),
    component_id VARCHAR(64),  -- raw carrier value, no FK (same planted id problems as purchase_orders)
    status VARCHAR(32) NOT NULL,
    event_date DATE NOT NULL,
    eta DATE,
    carrier VARCHAR(100),
    note TEXT
);

CREATE TABLE IF NOT EXISTS historical_disruption_cases (
    case_id VARCHAR(32) PRIMARY KEY,
    date DATE NOT NULL,
    supplier_id VARCHAR(32),
    component_id VARCHAR(64),
    disruption_type VARCHAR(64),
    delay_days INTEGER,
    strategy_used VARCHAR(64),
    recovery_cost_eur NUMERIC(12, 2),
    outcome VARCHAR(64),
    lesson_learned TEXT
);

CREATE TABLE IF NOT EXISTS supplier_message_inbox (
    message_id VARCHAR(32) PRIMARY KEY,
    received DATE NOT NULL,
    sender VARCHAR(255) NOT NULL,
    text TEXT NOT NULL
);

-- ==============================================================================
-- 7. Incident Memories Vector Store (pgvector)
-- ==============================================================================
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

-- ==============================================================================
-- 8. Authenticated Users & Role-Scoped Chainlit Chat History
-- ==============================================================================
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
