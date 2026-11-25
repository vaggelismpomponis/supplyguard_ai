"""Tests for PostgreSQL initialization schema and SupplyGuard contracts.

Validates that docker/postgres/init.sql and migrations/001_upgrade_schema.sql
include all required extensions, tables (thread_states, audit_log, checkpoints,
policy_chunks, incident_memories, and all 18 operational supply chain tables),
columns, and indexes.
"""

from pathlib import Path
import re
import unittest

INIT_SQL_PATH = Path(__file__).resolve().parent.parent / "docker" / "postgres" / "init.sql"
MIGRATION_SQL_PATH = (
    Path(__file__).resolve().parent.parent
    / "docker"
    / "postgres"
    / "migrations"
    / "001_upgrade_schema.sql"
)


class TestPostgresSchemaInit(unittest.TestCase):
    """Test suite for Postgres schema initialization script."""

    @classmethod
    def setUpClass(cls):
        cls.sql_path = INIT_SQL_PATH
        if not cls.sql_path.exists():
            raise FileNotFoundError(f"init.sql not found at {cls.sql_path}")
        cls.sql_content = cls.sql_path.read_text(encoding="utf-8")

    def test_init_sql_exists(self):
        self.assertTrue(self.sql_path.is_file())

    def test_pgvector_extension_enabled(self):
        pattern = r"CREATE\s+EXTENSION\s+IF\s+NOT\s+EXISTS\s+vector;"
        self.assertRegex(
            self.sql_content,
            pattern,
            "Postgres initialization must enable pgvector extension",
        )

    def _extract_table_body(self, table_name: str) -> str:
        """Extract the parenthesized body of a CREATE TABLE statement to scope column assertions."""
        pattern = rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table_name}\s*\((.*?)\);"
        match = re.search(pattern, self.sql_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match, f"Table declaration for '{table_name}' not found in SQL")
        return match.group(1)

    def test_no_legacy_helpdesk_tickets_table(self):
        self.assertNotIn("CREATE TABLE IF NOT EXISTS tickets", self.sql_content)

    def test_thread_states_and_audit_log_columns(self):
        ts_body = self._extract_table_body("thread_states")
        for col in ("thread_id", "owner_user_id", "owner_role", "access_scope", "case_state", "updated_at"):
            self.assertRegex(ts_body, rf"\b{col}\s+[A-Za-z0-9_]+")

    def test_auth_and_chat_history_tables_and_migration(self):
        for table in ("app_users", "chat_users", "chat_threads", "chat_steps", "chat_elements", "chat_feedbacks"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", self.sql_content)

        app_users_body = self._extract_table_body("app_users")
        for col in ("user_id", "username", "email", "display_name", "role", "access_scope", "password_hash", "is_active"):
            self.assertRegex(app_users_body, rf"\b{col}\s+[A-Za-z0-9_]+")

        threads_body = self._extract_table_body("chat_threads")
        for col in ("id", "user_id", "user_identifier", "role", "access_scope", "metadata"):
            self.assertRegex(threads_body, rf"\b{col}\s+[A-Za-z0-9_]+")

        mig_002 = INIT_SQL_PATH.parent / "migrations" / "002_auth_and_chat_history.sql"
        self.assertTrue(mig_002.is_file(), "002_auth_and_chat_history.sql migration must exist")
        mig_sql = mig_002.read_text(encoding="utf-8")
        self.assertRegex(mig_sql, r"\bBEGIN\s*;")
        self.assertRegex(mig_sql, r"\bCOMMIT\s*;")
        self.assertIn("ALTER TABLE IF EXISTS thread_states ADD COLUMN IF NOT EXISTS owner_user_id", mig_sql)
        for table in ("app_users", "chat_users", "chat_threads", "chat_steps", "chat_elements", "chat_feedbacks"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", mig_sql)

        audit_body = self._extract_table_body("audit_log")
        for col in (
            "id",
            "action_id",
            "thread_id",
            "action_type",
            "actor",
            "component_id",
            "status",
            "parameters",
            "rationale",
            "created_at",
            "executed_at",
        ):
            self.assertRegex(audit_body, rf"\b{col}\s+[A-Za-z0-9_]+", f"audit_log missing '{col}'")

    def test_langgraph_checkpoints_tables(self):
        for table in ("checkpoint_migrations", "checkpoints", "checkpoint_blobs", "checkpoint_writes"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", self.sql_content)

        table_body = self._extract_table_body("checkpoints")
        for col in ("thread_id", "checkpoint_ns", "checkpoint_id", "checkpoint", "metadata"):
            self.assertRegex(table_body, rf"\b{col}\s+[A-Za-z0-9_]+")

    def test_vector_tables_and_columns(self):
        policy_body = self._extract_table_body("policy_chunks")
        for col in ("doc_id", "title", "effective_date", "source", "content", "chunk_index", "embedding"):
            self.assertRegex(policy_body, rf"\b{col}\s+[A-Za-z0-9_]+")
        self.assertIn("vector(1536)", policy_body)

        mem_body = self._extract_table_body("incident_memories")
        for col in ("memory_id", "kind", "case_id", "component_type", "severity", "content", "embedding"):
            self.assertRegex(mem_body, rf"\b{col}\s+[A-Za-z0-9_]+")
        self.assertIn("vector(1536)", mem_body)

    def test_indexes_defined(self):
        expected_indexes = [
            "idx_thread_states_updated_at",
            "idx_thread_states_owner_role",
            "idx_app_users_role",
            "idx_chat_threads_user_role",
            "idx_chat_steps_thread_created",
            "idx_chat_elements_thread",
            "idx_audit_log_action_id",
            "idx_audit_log_thread_id",
            "idx_checkpoints_thread_id",
            "idx_policy_doc_effective",
            "idx_policy_chunks_embedding",
            "idx_incident_memories_embedding",
            "idx_incident_memories_filters",
        ]
        for idx in expected_indexes:
            self.assertIn(idx, self.sql_content, f"Missing index '{idx}'")


class TestSupplyGuardSchema(unittest.TestCase):
    """Test suite for SupplyGuard AI supply chain domain tables in init.sql."""

    @classmethod
    def setUpClass(cls):
        cls.sql_content = INIT_SQL_PATH.read_text(encoding="utf-8")

    def test_supply_chain_tables_declared(self):
        tables = [
            "upstream_manufacturers",
            "suppliers",
            "factories",
            "locations",
            "components",
            "products",
            "bill_of_materials",
            "supplier_components",
            "inventory",
            "quarantine_lots",
            "reservations",
            "customers",
            "customer_orders",
            "production_schedule",
            "purchase_orders",
            "shipment_updates",
            "historical_disruption_cases",
            "supplier_message_inbox",
        ]
        for tbl in tables:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {tbl}", self.sql_content)

        po_body = self.sql_content.split("CREATE TABLE IF NOT EXISTS purchase_orders")[1].split(");")[0]
        self.assertIn("action_id", po_body)

    def test_supply_chain_indexes_declared(self):
        for idx in (
            "idx_suppliers_name",
            "idx_suppliers_upstream",
            "idx_bom_component",
            "idx_supplier_comp_component",
            "idx_inventory_component",
            "idx_po_supplier_comp",
        ):
            self.assertIn(idx, self.sql_content)


class TestPostgresUpgradeMigration(unittest.TestCase):
    """Test suite for non-destructive SupplyGuard schema upgrade migration script."""

    @classmethod
    def setUpClass(cls):
        cls.sql_content = MIGRATION_SQL_PATH.read_text(encoding="utf-8")

    def test_transaction_and_supplyguard_tables(self):
        self.assertRegex(self.sql_content, r"\bBEGIN\s*;")
        self.assertRegex(self.sql_content, r"\bCOMMIT\s*;")
        self.assertNotIn("tickets", self.sql_content.lower())
        for table in (
            "thread_states",
            "audit_log",
            "checkpoints",
            "checkpoint_blobs",
            "checkpoint_writes",
            "checkpoint_migrations",
            "policy_chunks",
            "incident_memories",
        ):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", self.sql_content)
        self.assertIn(
            "ALTER TABLE IF EXISTS purchase_orders ADD COLUMN IF NOT EXISTS action_id VARCHAR(64) UNIQUE;",
            self.sql_content,
        )
        self.assertIn("idx_purchase_orders_action_id_unique", self.sql_content)

    def test_idempotency_loads_ensure_thread_states_table(self):
        idem_src = (
            Path(__file__).resolve().parent.parent / "src" / "db" / "idempotency.py"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(idem_src.count("_ensure_thread_states_table(cur)"), 3)


if __name__ == "__main__":
    unittest.main()
