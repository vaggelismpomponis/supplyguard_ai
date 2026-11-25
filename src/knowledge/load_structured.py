"""Load the structured support data (CSV) into the PostgreSQL operational tables (#68).

Run: python -m src.knowledge.load_structured
Idempotent: applies docker/postgres/init.sql (all IF NOT EXISTS), then replaces every table's rows
in one transaction, so a failed load leaves the previous data untouched.
"""
import csv
from pathlib import Path

from .common import pg

ROOT = Path(__file__).resolve().parents[2]
STRUCTURED = ROOT / "src" / "support-data" / "structured"
INIT_SQL = ROOT / "docker" / "postgres" / "init.sql"

# CSV file -> table (schema in docker/postgres/init.sql, section 6), in foreign-key order.
TABLES = [
    ("factories.csv", "factories"),
    ("locations.csv", "locations"),
    ("customers.csv", "customers"),
    ("upstream_manufacturers.csv", "upstream_manufacturers"),
    ("suppliers.csv", "suppliers"),
    ("components.csv", "components"),
    ("products.csv", "products"),
    ("bill_of_materials.csv", "bill_of_materials"),
    ("supplier_components.csv", "supplier_components"),
    ("purchase_orders.csv", "purchase_orders"),
    ("shipment_updates.csv", "shipment_updates"),
    ("supplier_message_inbox.csv", "supplier_message_inbox"),
    ("inventory.csv", "inventory"),
    ("customer_orders.csv", "customer_orders"),
    ("reservations.csv", "reservations"),
    ("quarantine_lots.csv", "quarantine_lots"),
    ("production_schedule.csv", "production_schedule"),
    ("historical_disruption_cases.csv", "historical_disruption_cases"),
]


# Databases created from an older init.sql (before #68) still have a boolean approved_source and
# foreign keys on the raw ERP component ids; init.sql only runs on a fresh volume, so align them here.
# Idempotent; the tables are reloaded right after, so no data conversion is needed.
UPGRADE_SQL = """
ALTER TABLE supplier_components ALTER COLUMN approved_source DROP DEFAULT;
ALTER TABLE supplier_components ALTER COLUMN approved_source TYPE VARCHAR(16) USING NULL;
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS purchase_orders_component_id_fkey;
ALTER TABLE shipment_updates DROP CONSTRAINT IF EXISTS shipment_updates_component_id_fkey;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS action_id VARCHAR(64);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor VARCHAR(128);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS component_id VARCHAR(64);
"""


def header(csv_name: str) -> list[str]:
    with open(STRUCTURED / csv_name, encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


def load() -> dict[str, int]:
    counts: dict[str, int] = {}
    with pg() as conn:  # one transaction: all or nothing
        conn.execute(INIT_SQL.read_text(encoding="utf-8"))
        conn.execute("TRUNCATE " + ", ".join(t for _, t in TABLES) + " CASCADE")
        conn.execute(UPGRADE_SQL)
        for csv_name, table in TABLES:
            cols = ", ".join(header(csv_name))
            # CSV format: an unquoted empty field loads as NULL (blank ids, missing delivery dates).
            with conn.cursor() as cur, cur.copy(
                f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)"
            ) as copy:
                copy.write((STRUCTURED / csv_name).read_bytes())
            counts[table] = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    return counts


if __name__ == "__main__":
    for table, n in load().items():
        print(f"{table:30} {n:>6}")
