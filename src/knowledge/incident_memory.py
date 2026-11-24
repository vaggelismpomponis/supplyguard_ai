"""Index the 300 historical disruption cases and 40 approved incident memories (KAN-09).

Run: python -m src.knowledge.incident_memory
Idempotent: the table is replaced in one transaction.

Kept apart from the document chunks (own pgvector table, not policy_chunks) so few-shot lookups for a new case never
mix with contract or notice retrieval. Each row is filterable by component_type (from the
component master) and delay severity (minor <= 7 d, moderate 8-14 d, major >= 15 d).
"""
import csv
import json
import re
from pathlib import Path
from typing import Any

from .common import DIM, embed, pg, vec

STRUCTURED = Path(__file__).resolve().parents[1] / "support-data" / "structured"

STRATEGIES = {
    "A": "Transfer available inventory", "B": "Expedite an existing order",
    "C": "Purchase from an approved alternative", "D": "Reallocate limited components across customer orders",
    "E": "Reschedule production",
}

DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS incident_memories (
    memory_id       text PRIMARY KEY,
    kind            text NOT NULL CHECK (kind IN ('historical_case', 'approved_memory')),
    case_id         text NOT NULL,
    supplier_id     text,
    component_id    text,
    component_type  text,
    disruption_type text,
    delay_days      int,
    severity        text CHECK (severity IN ('minor', 'moderate', 'major')),
    strategy        text,
    recovery_cost_eur numeric(14, 2),
    outcome         text,
    access_scope    text NOT NULL,
    content         text NOT NULL,
    embedding       vector({DIM}) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incident_memories_embedding ON incident_memories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_incident_memories_filters ON incident_memories(component_type, severity);
"""


def severity(delay_days: int | None) -> str | None:
    if delay_days is None:
        return None
    return "minor" if delay_days <= 7 else "moderate" if delay_days <= 14 else "major"


def component_type(description: str) -> str:
    """'Relay type E83' -> 'Relay'; descriptions without a type suffix stay whole."""
    return re.sub(r"\s+type\s+\S+$", "", description)


def records() -> list[dict[str, Any]]:
    with open(STRUCTURED / "components.csv", encoding="utf-8", newline="") as f:
        ctype = {r["component_id"]: component_type(r["description"]) for r in csv.DictReader(f)}
    with open(STRUCTURED / "historical_disruption_cases.csv", encoding="utf-8", newline="") as f:
        cases = {r["case_id"]: r for r in csv.DictReader(f)}

    out = []
    for c in cases.values():
        delay = int(c["delay_days"])
        out.append({
            "memory_id": c["case_id"], "kind": "historical_case", "case_id": c["case_id"],
            "supplier_id": c["supplier_id"], "component_id": c["component_id"],
            "component_type": ctype.get(c["component_id"]), "disruption_type": c["disruption_type"],
            "delay_days": delay, "severity": severity(delay), "strategy": STRATEGIES[c["strategy_used"]],
            "recovery_cost_eur": float(c["recovery_cost_eur"]), "outcome": c["outcome"], "access_scope": "internal",
            "content": (
                f"{c['disruption_type']} of {delay} days on {c['component_id']} ({ctype.get(c['component_id'])}) "
                f"from supplier {c['supplier_id']}. Strategy {c['strategy_used']}: {STRATEGIES[c['strategy_used']]}, "
                f"cost EUR {float(c['recovery_cost_eur']):,.0f}, outcome {c['outcome']}. Lesson: {c['lesson_learned']}"
            ),
        })
    with open(STRUCTURED / "approved_incident_memories.jsonl", encoding="utf-8") as f:
        for m in map(json.loads, filter(str.strip, f)):
            case = cases.get(m["case_id"], {})  # approved summaries lack delay and type: take them from the case
            delay = int(case["delay_days"]) if case else None
            out.append({
                "memory_id": m["memory_id"], "kind": "approved_memory", "case_id": m["case_id"],
                "supplier_id": m["supplier_id"], "component_id": m["component_id"],
                "component_type": ctype.get(m["component_id"]), "disruption_type": case.get("disruption_type"),
                "delay_days": delay, "severity": severity(delay), "strategy": m["strategy"],
                "recovery_cost_eur": float(case["recovery_cost_eur"]) if case else None,
                "outcome": case.get("outcome"), "access_scope": m["access_scope"], "content": m["approved_summary"],
            })
    return out


COLS = ["memory_id", "kind", "case_id", "supplier_id", "component_id", "component_type", "disruption_type",
        "delay_days", "severity", "strategy", "recovery_cost_eur", "outcome", "access_scope", "content"]


def ingest() -> int:
    rows = records()
    vectors = embed([r["content"] for r in rows])
    with pg() as conn:  # one transaction: all or nothing
        conn.execute(DDL)
        conn.execute("DELETE FROM incident_memories")
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO incident_memories ({', '.join(COLS)}, embedding) VALUES ({', '.join(['%s'] * len(COLS))}, %s::vector)",
                [[r[c] for c in COLS] + [vec(v)] for r, v in zip(rows, vectors)],
            )
    return len(rows)


def search(
    query: str,
    component_type: str | None = None,
    severity: str | None = None,
    kind: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Most similar past incidents, optionally filtered; every row cites its memory_id / case_id."""
    q = vec(embed([query])[0])
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            f"""SELECT {', '.join(COLS)}, 1 - (embedding <=> %(q)s::vector) AS score FROM incident_memories
                WHERE (%(ct)s::text IS NULL OR component_type = %(ct)s)
                  AND (%(sev)s::text IS NULL OR severity = %(sev)s)
                  AND (%(kind)s::text IS NULL OR kind = %(kind)s)
                ORDER BY embedding <=> %(q)s::vector LIMIT %(k)s""",
            {"q": q, "ct": component_type, "sev": severity, "kind": kind, "k": k},
        )
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def save_approved_memory(
    memory_id: str,
    case_id: str,
    supplier_id: str | None,
    component_id: str | None,
    delay_days: int | None,
    strategy: str,
    recovery_cost_eur: float | None,
    outcome: str,
    approved_summary: str,
    access_scope: str = "internal",
) -> dict[str, Any]:
    """Persist a newly approved incident resolution summary to incident_memories idempotently."""
    ctype: str | None = None
    if component_id:
        with open(STRUCTURED / "components.csv", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r["component_id"] == component_id:
                    ctype = component_type(r["description"])
                    break
    sev = severity(delay_days)
    vector = embed([approved_summary])[0]
    row = {
        "memory_id": memory_id,
        "kind": "approved_memory",
        "case_id": case_id,
        "supplier_id": supplier_id,
        "component_id": component_id,
        "component_type": ctype,
        "disruption_type": "delay",
        "delay_days": delay_days,
        "severity": sev,
        "strategy": strategy,
        "recovery_cost_eur": recovery_cost_eur,
        "outcome": outcome,
        "access_scope": access_scope,
        "content": approved_summary,
    }
    with pg() as conn:
        conn.execute(DDL)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO incident_memories ({', '.join(COLS)}, embedding)
                VALUES ({', '.join(['%s'] * len(COLS))}, %s::vector)
                ON CONFLICT (memory_id) DO UPDATE SET
                    kind = EXCLUDED.kind,
                    case_id = EXCLUDED.case_id,
                    supplier_id = EXCLUDED.supplier_id,
                    component_id = EXCLUDED.component_id,
                    component_type = EXCLUDED.component_type,
                    disruption_type = EXCLUDED.disruption_type,
                    delay_days = EXCLUDED.delay_days,
                    severity = EXCLUDED.severity,
                    strategy = EXCLUDED.strategy,
                    recovery_cost_eur = EXCLUDED.recovery_cost_eur,
                    outcome = EXCLUDED.outcome,
                    access_scope = EXCLUDED.access_scope,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding;
                """,
                [row[c] for c in COLS] + [vec(vector)],
            )
    return row


if __name__ == "__main__":
    print(f"indexed {ingest()} incident records (cases + approved memories)")
