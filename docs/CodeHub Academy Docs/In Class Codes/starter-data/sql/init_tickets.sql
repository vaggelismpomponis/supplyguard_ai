-- Simulated ticketing table (PostgreSQL). Mounted by Docker Compose, or run by the Platform role.
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id        SERIAL PRIMARY KEY,
    request_id       TEXT NOT NULL,                 -- idempotency key: one executed action per request
    employee_id      TEXT NOT NULL,
    application      TEXT,
    symptom          TEXT,
    action           TEXT NOT NULL CHECK (action IN ('ANSWER','LINK_OUTAGE','RESET_CREDENTIALS','OPEN_TICKET','ESCALATE')),
    linked_outage_id TEXT,
    status           TEXT NOT NULL DEFAULT 'open',
    approved_by      TEXT,
    policy_citation  TEXT,                          -- e.g. POL-002 v2 (effective 2026-06-01)
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (request_id)                             -- a restart must not execute an approved action twice
);
-- LangGraph's PostgresSaver creates its own checkpoint tables via checkpointer.setup().
