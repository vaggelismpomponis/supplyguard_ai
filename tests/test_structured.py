"""#68: relational supply chain tables. Integration tests need DATABASE_URL and a running Postgres."""
import csv
import os
import re

import pytest

from src.knowledge import load_structured as ls

needs_pg = pytest.mark.skipif("DATABASE_URL" not in os.environ, reason="no Postgres")


def table_columns(table: str) -> set[str]:
    sql = ls.INIT_SQL.read_text(encoding="utf-8")
    body = re.search(rf"CREATE TABLE IF NOT EXISTS {table} \((.*?)\n\);", sql, re.S)
    assert body, f"{table} missing from init.sql"
    return {line.split()[0] for line in body[1].splitlines() if line.strip() and not line.strip().startswith(("PRIMARY", "--"))}


def test_alternative_suppliers_and_raw_ids_fit_the_schema():
    sql = ls.INIT_SQL.read_text(encoding="utf-8")
    assert "'alternative'" in sql  # supplier_components.approved_source is yes / no / alternative
    assert "component_id VARCHAR(64) REFERENCES" not in sql.split("CREATE TABLE IF NOT EXISTS purchase_orders")[1].split(");")[0]


@pytest.mark.parametrize("csv_name,table", ls.TABLES)
def test_every_csv_column_has_a_table_column(csv_name, table):
    assert set(ls.header(csv_name)) <= table_columns(table)


@pytest.fixture(scope="module")
def loaded():
    return ls.load()


@needs_pg
def test_row_counts_match_csv(loaded):
    for csv_name, table in ls.TABLES:
        with open(ls.STRUCTURED / csv_name, encoding="utf-8", newline="") as f:
            assert loaded[table] == sum(1 for _ in csv.DictReader(f)), table


@needs_pg
def test_load_is_idempotent(loaded):
    assert ls.load() == loaded


@needs_pg
def test_mc17_usable_stock_excludes_reserved_and_quarantined(loaded):
    with ls.pg() as c:
        row = c.execute(
            "SELECT sum(on_hand), sum(reserved), sum(quarantined), sum(usable) FROM inventory WHERE component_id = 'MC-17'"
        ).fetchone()
    assert row == (5200, 1400, 600, 3200)


@needs_pg
def test_blank_po_component_ids_load_as_null(loaded):
    with ls.pg() as c:
        assert c.execute("SELECT count(*) FROM purchase_orders WHERE component_id IS NULL").fetchone()[0] > 0
