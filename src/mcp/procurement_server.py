"""Simulated Procurement System & External Risk MCP Integration.

Platform & Workflow Roles | Scope: mcp, platform
Target: Issue #38

Implements MCP-compliant tool handlers for:
1. create_purchase_order: Idempotent order execution returning PurchaseOrderReceipt
2. expedite_purchase_order: Idempotent expedite request on an open PO
3. request_stock_transfer: Idempotent internal hub/warehouse transfer (€0.12/unit, 2d)
4. update_production_schedule: Idempotent production schedule adjustment
5. get_supplier_risk: External risk evaluation querying the External Risk Service
6. check_inventory_balance: Real-time inventory calculation (usable vs quarantined)
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.contracts import PurchaseOrderReceipt, SupplierRiskInfo


def _get_risk_feed(region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query External Risk Service over HTTP or load local risk feed."""
    feed_file = REPO_ROOT / "src" / "support-data" / "external_service" / "risk_feed.json"
    risk_url = (os.getenv("EXTERNAL_RISK_URL") or "").strip().rstrip("/")

    if risk_url:
        url = f"{risk_url}/alerts"
        if region:
            url += f"?region={region}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SupplyGuard-MCP"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, dict):
                    alerts = data.get("alerts", [])
                    return [a for a in alerts if not region or a.get("region") == region]
                if isinstance(data, list):
                    return data
        except Exception:
            pass

    if feed_file.exists():
        try:
            data = json.loads(feed_file.read_text(encoding="utf-8"))
            alerts = data.get("alerts", [])
            if region:
                return [a for a in alerts if a.get("region") == region]
            return alerts
        except Exception:
            pass
    return []


def _deterministic_po_id(action_id: str) -> str:
    """Derive a collision-free PO ID from action_id that survives container restarts."""
    digest = hashlib.sha256(action_id.encode("utf-8")).hexdigest()[:8].upper()
    return f"PO-SUP-2026-{digest}"


def _op_action_id(op_key: str) -> str:
    """Derive a deterministic <=64-char audit_log action_id for complementary MCP ops."""
    digest = hashlib.sha256(op_key.encode("utf-8")).hexdigest()[:24]
    return f"op-{digest}"


class SimulatedProcurementSystem:
    """Simulated ERP procurement engine with strict DB-backed idempotency."""

    def __init__(self) -> None:
        self._executed_orders: Dict[str, PurchaseOrderReceipt] = {}
        self._executed_ops: Dict[str, Dict[str, Any]] = {}

    def _load_persisted_op(self, op_key: str) -> Optional[Dict[str, Any]]:
        """Restore a previously executed complementary MCP operation from PostgreSQL audit_log."""
        try:
            from src.db.connection import is_postgres_available

            if not is_postgres_available():
                return None
            from src.db.idempotency import get_action_record

            rec = get_action_record(_op_action_id(op_key))
            if rec and rec.get("status") == "executed":
                params = rec.get("parameters") or {}
                if isinstance(params, str):
                    params = json.loads(params)
                receipt = params.get("receipt") if isinstance(params, dict) else None
                if isinstance(receipt, dict):
                    self._executed_ops[op_key] = receipt
                    return receipt
        except Exception:
            pass
        return None

    def _persist_op(
        self,
        op_key: str,
        *,
        action_type: str,
        thread_id: Optional[str],
        component_id: Optional[str],
        result: Dict[str, Any],
        rationale: str,
    ) -> None:
        """Persist a complementary MCP write operation to PostgreSQL audit_log."""
        try:
            from src.db.connection import get_pooled_connection, is_postgres_available

            if not is_postgres_available():
                return
            op_id = _op_action_id(op_key)
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor VARCHAR(128);")
                        cur.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS component_id VARCHAR(64);")
                        cur.execute(
                            """
                            INSERT INTO audit_log (
                                action_id, thread_id, action_type, component_id, status,
                                parameters, rationale, executed_at
                            )
                            VALUES (%s, %s, %s, %s, 'executed', %s::jsonb, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (action_id) DO NOTHING;
                            """,
                            (
                                op_id,
                                thread_id or f"thread-{op_id[:12]}",
                                action_type,
                                component_id,
                                json.dumps({"op_key": op_key, "receipt": result}, default=str),
                                rationale,
                            ),
                        )
        except Exception:
            pass

    def create_purchase_order(
        self,
        action_id: str,
        supplier_id: str,
        component_id: str,
        quantity: int,
        unit_price: float,
        delivery_date: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> PurchaseOrderReceipt:
        """Create a new purchase order with strict DB-backed idempotency.

        If action_id was already executed, returns the original persisted receipt.
        """
        # 1. Check in-memory cache
        if action_id in self._executed_orders:
            return self._executed_orders[action_id]

        order_id = _deterministic_po_id(action_id)

        # 2. Check database audit_log if DB is available
        try:
            from src.db.connection import is_postgres_available

            if is_postgres_available():
                from src.db.idempotency import get_action_record, is_action_executed

                if is_action_executed(action_id):
                    rec = get_action_record(action_id) or {}
                    params = rec.get("parameters") or {}
                    stored_receipt = params.get("receipt") if isinstance(params, dict) else None
                    if isinstance(stored_receipt, dict) and stored_receipt.get("order_id"):
                        receipt = PurchaseOrderReceipt.model_validate(stored_receipt)
                    else:
                        receipt = PurchaseOrderReceipt(
                            order_id=order_id,
                            action_id=action_id,
                            supplier_id=supplier_id,
                            component_id=component_id,
                            quantity=quantity,
                            total_amount=round(quantity * unit_price, 2),
                            status="confirmed",
                            created_at=str(rec.get("executed_at") or datetime.now(timezone.utc).isoformat()),
                        )
                    self._executed_orders[action_id] = receipt
                    return receipt
        except Exception:
            pass

        # 3. Generate new Purchase Order with collision-free ID
        total_amount = round(quantity * unit_price, 2)
        created_at = datetime.now(timezone.utc).isoformat()

        receipt = PurchaseOrderReceipt(
            order_id=order_id,
            action_id=action_id,
            supplier_id=supplier_id,
            component_id=component_id,
            quantity=quantity,
            total_amount=total_amount,
            status="confirmed",
            created_at=created_at,
        )
        self._executed_orders[action_id] = receipt

        # 4. Record execution in PostgreSQL audit_log (if not already locked by execute_idempotent) and purchase_orders
        try:
            from src.db.connection import get_pooled_connection, is_postgres_available

            if is_postgres_available():
                with get_pooled_connection() as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute(
                                "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS action_id VARCHAR(64) UNIQUE;"
                            )
                            cur.execute(
                                "CREATE UNIQUE INDEX IF NOT EXISTS idx_purchase_orders_action_id_unique "
                                "ON purchase_orders(action_id);"
                            )
                            cur.execute(
                                "SELECT status FROM audit_log WHERE action_id = %s;",
                                (action_id,),
                            )
                            existing = cur.fetchone()
                            if existing is None:
                                cur.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor VARCHAR(128);")
                                cur.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS component_id VARCHAR(64);")
                                cur.execute(
                                    """
                                    INSERT INTO audit_log (
                                        action_id, thread_id, action_type, component_id, status,
                                        parameters, rationale, executed_at
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, CURRENT_TIMESTAMP)
                                    ON CONFLICT (action_id) DO NOTHING;
                                    """,
                                    (
                                        action_id,
                                        thread_id or f"thread-{action_id[:8]}",
                                        "purchase_alternative",
                                        component_id,
                                        "executed",
                                        json.dumps({"receipt": receipt.model_dump()}),
                                        f"Simulated PO {order_id} issued to supplier {supplier_id}",
                                    ),
                                )
                            cur.execute(
                                """
                                INSERT INTO purchase_orders (
                                    po_id, supplier_id, component_id, qty, unit_price_eur,
                                    order_date, promised_date, status, action_id
                                )
                                VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s, 'confirmed', %s)
                                ON CONFLICT DO NOTHING;
                                """,
                                (
                                    order_id,
                                    supplier_id,
                                    component_id,
                                    quantity,
                                    unit_price,
                                    delivery_date or "2026-10-28",
                                    action_id,
                                ),
                            )
        except Exception:
            pass

        return receipt

    def expedite_purchase_order(
        self,
        action_id: str,
        po_id: str,
        days_gain: int = 7,
        fee_pct: float = 6.0,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently expedite an existing open purchase order (persisted in Postgres)."""
        op_key = f"{action_id}:expedite:{po_id}"
        if op_key in self._executed_ops:
            return {**self._executed_ops[op_key], "idempotent_replay": True}
        persisted = self._load_persisted_op(op_key)
        if persisted is not None:
            return {**persisted, "idempotent_replay": True}

        found = False
        expedite_allowed = False
        po_qty = 0
        unit_price = 0.0
        component_id: Optional[str] = None

        # 1. Check PostgreSQL purchase_orders when available
        try:
            from src.db.connection import get_pooled_connection, is_postgres_available

            if is_postgres_available():
                with get_pooled_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT expedite_allowed, qty, unit_price_eur, component_id
                            FROM purchase_orders
                            WHERE po_id = %s;
                            """,
                            (po_id,),
                        )
                        row = cur.fetchone()
                        if row is not None:
                            found = True
                            expedite_allowed = bool(row[0])
                            po_qty = int(row[1] or 0)
                            unit_price = float(row[2] or 0.0)
                            component_id = str(row[3]) if row[3] else None
        except Exception:
            pass

        # 2. Fall back to support-data CSV lookup
        if not found:
            po_csv = REPO_ROOT / "src" / "support-data" / "structured" / "purchase_orders.csv"
            if po_csv.exists():
                with po_csv.open("r", encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        if row.get("po_id") == po_id:
                            found = True
                            expedite_allowed = (row.get("expedite_allowed") or "").lower() in ("yes", "true", "1")
                            po_qty = int(row.get("qty") or 0)
                            unit_price = float(row.get("unit_price_eur") or 0.0)
                            component_id = row.get("component_id") or None
                            break

        if not found:
            raise ValueError(f"Purchase order '{po_id}' not found.")
        if not expedite_allowed:
            raise ValueError(f"Purchase order '{po_id}' is not eligible for expediting.")

        fee_eur = round(po_qty * unit_price * (fee_pct / 100.0), 2)
        result = {
            "operation": "expedite_purchase_order",
            "expedite_ref": f"EXP-{po_id}",
            "action_id": action_id,
            "thread_id": thread_id,
            "po_id": po_id,
            "qty": po_qty,
            "days_gain": days_gain,
            "fee_pct": fee_pct,
            "fee_eur": fee_eur,
            "status": "confirmed",
            "idempotent_replay": False,
        }
        self._executed_ops[op_key] = result
        self._persist_op(
            op_key,
            action_type="expedite_order",
            thread_id=thread_id,
            component_id=component_id,
            result=result,
            rationale=f"Expedited open PO {po_id} (+{days_gain}d, fee EUR {fee_eur:.2f})",
        )
        return result

    def request_stock_transfer(
        self,
        action_id: str,
        component_id: str,
        from_location: str,
        to_location: str,
        qty: int,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently request an internal stock transfer (€0.12/unit, 2 days; persisted in Postgres)."""
        op_key = f"{action_id}:transfer:{from_location}:{to_location}"
        if op_key in self._executed_ops:
            return {**self._executed_ops[op_key], "idempotent_replay": True}
        persisted = self._load_persisted_op(op_key)
        if persisted is not None:
            return {**persisted, "idempotent_replay": True}

        usable = self.check_inventory_balance(component_id).get("usable", 0)
        if qty > usable:
            raise ValueError(f"Requested transfer {qty} exceeds usable inventory {usable} for {component_id}.")

        digest = hashlib.sha256(op_key.encode("utf-8")).hexdigest()[:6].upper()
        result = {
            "operation": "request_stock_transfer",
            "transfer_ref": f"TRF-2026-{digest}",
            "action_id": action_id,
            "thread_id": thread_id,
            "component_id": component_id,
            "from_location": from_location,
            "to_location": to_location,
            "qty": qty,
            "transfer_days": 2,
            "cost_eur": round(qty * 0.12, 2),
            "status": "confirmed",
            "idempotent_replay": False,
        }
        self._executed_ops[op_key] = result
        self._persist_op(
            op_key,
            action_type="transfer_inventory",
            thread_id=thread_id,
            component_id=component_id,
            result=result,
            rationale=f"Transfer {qty} units of {component_id} from {from_location} to {to_location}",
        )
        return result

    def update_production_schedule(
        self,
        action_id: str,
        product_id: str,
        week_start: str,
        planned_units: int,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Idempotently update a factory production schedule slot (persisted in Postgres)."""
        op_key = f"{action_id}:schedule:{product_id}:{week_start}"
        if op_key in self._executed_ops:
            return {**self._executed_ops[op_key], "idempotent_replay": True}
        persisted = self._load_persisted_op(op_key)
        if persisted is not None:
            return {**persisted, "idempotent_replay": True}

        digest = hashlib.sha256(op_key.encode("utf-8")).hexdigest()[:6].upper()
        result = {
            "operation": "update_production_schedule",
            "schedule_ref": f"SCH-2026-{digest}",
            "action_id": action_id,
            "thread_id": thread_id,
            "product_id": product_id,
            "week_start": week_start,
            "planned_units": planned_units,
            "status": "confirmed",
            "idempotent_replay": False,
        }
        self._executed_ops[op_key] = result
        self._persist_op(
            op_key,
            action_type="reschedule_production",
            thread_id=thread_id,
            component_id=None,
            result=result,
            rationale=f"Update production schedule for {product_id} (week {week_start}, {planned_units} units)",
        )
        return result

    def get_supplier_risk(
        self,
        supplier_id: str,
        supplier_name: Optional[str] = None,
        country: Optional[str] = None,
    ) -> SupplierRiskInfo:
        """Fetch supplier risk combining regional feed and supplier attributes."""
        country_code = country or "DE"
        upstream_id = None
        sup_csv = REPO_ROOT / "src" / "support-data" / "structured" / "suppliers.csv"
        if sup_csv.exists():
            with sup_csv.open("r", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if row.get("supplier_id") == supplier_id:
                        country_code = country or row.get("country") or country_code
                        supplier_name = supplier_name or row.get("name")
                        upstream_id = row.get("upstream_manufacturer_id") or None
                        break
        else:
            canonical = {
                "S001": ("DE", "Atlas Components", "U01"),
                "S002": ("RO", "Helios Supply", "U03"),
                "S003": ("SE", "Borealis Parts", "U04"),
                "S004": ("CZ", "Cordillera Industrial", "U02"),
                "S005": ("NL", "Delta Micro Systems", "U01"),
                "S006": ("DE", "Atlas Logistik GmbH", None),
            }
            if supplier_id in canonical:
                country_code = country or canonical[supplier_id][0]
                supplier_name = supplier_name or canonical[supplier_id][1]
                upstream_id = canonical[supplier_id][2]

        alerts = _get_risk_feed(country_code)
        upstream_alerts = _get_risk_feed("TW")

        risk_score = 0.1
        geo_risk = "Low"
        logistics = "Normal"
        notes: List[str] = []

        if alerts:
            for a in alerts:
                notes.append(f"{a.get('topic')}: {a.get('text')}")
                if a.get("severity") == "high":
                    risk_score = max(risk_score, 0.8)
                    geo_risk = "High"
                elif a.get("severity") == "medium":
                    risk_score = max(risk_score, 0.5)
                    geo_risk = "Medium"
                    if "freight" in a.get("topic", "") or "port" in a.get("topic", ""):
                        logistics = "Congested"

        if (upstream_id == "U01" or supplier_id in ("S001", "S005")) and upstream_alerts:
            risk_score = max(risk_score, 0.85)
            geo_risk = "Critical"
            logistics = "Disrupted"
            notes.append("Upstream tier-2 dependency Veltro Semiconductor (TW) under maintenance.")

        return SupplierRiskInfo(
            supplier_id=supplier_id,
            supplier_name=supplier_name or f"Supplier {supplier_id}",
            country=country_code,
            risk_score=risk_score,
            geopolitical_risk=geo_risk,
            logistics_status=logistics,
            notes=" | ".join(notes) if notes else "No critical disruption alerts.",
        )

    def check_inventory_balance(self, component_id: str) -> Dict[str, Any]:
        """Compute usable vs reserved vs quarantined stock for a component."""
        try:
            from src.db.connection import get_pooled_connection, is_postgres_available

            if is_postgres_available():
                with get_pooled_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT
                                COALESCE(SUM(on_hand), 0),
                                COALESCE(SUM(reserved), 0),
                                COALESCE(SUM(quarantined), 0),
                                COALESCE(SUM(usable), 0)
                            FROM inventory
                            WHERE component_id = %s;
                            """,
                            (component_id,),
                        )
                        row = cur.fetchone()
                        if row and row[0] > 0:
                            return {
                                "component_id": component_id,
                                "on_hand": int(row[0]),
                                "reserved": int(row[1]),
                                "quarantined": int(row[2]),
                                "usable": int(row[3]),
                            }
        except Exception:
            pass

        inv_csv = REPO_ROOT / "src" / "support-data" / "structured" / "inventory.csv"
        if inv_csv.exists():
            total_on_hand = 0
            total_reserved = 0
            total_quarantined = 0
            total_usable = 0
            with open(inv_csv, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("component_id") == component_id:
                        total_on_hand += int(row.get("on_hand", 0))
                        total_reserved += int(row.get("reserved", 0))
                        total_quarantined += int(row.get("quarantined", 0))
                        total_usable += int(row.get("usable", 0))
            if total_on_hand > 0:
                return {
                    "component_id": component_id,
                    "on_hand": total_on_hand,
                    "reserved": total_reserved,
                    "quarantined": total_quarantined,
                    "usable": total_usable,
                }

        return {
            "component_id": component_id,
            "on_hand": 0,
            "reserved": 0,
            "quarantined": 0,
            "usable": 0,
        }


_PROCUREMENT_SYSTEM = SimulatedProcurementSystem()


def get_procurement_system() -> SimulatedProcurementSystem:
    """Return the singleton instance of SimulatedProcurementSystem."""
    return _PROCUREMENT_SYSTEM


# ==============================================================================
# FastMCP Server Definition (CodeHub 46-mcp-server pattern)
# ==============================================================================

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - optional when mcp package is absent
    FastMCP = None  # type: ignore[assignment,misc]


def build_fastmcp_server() -> Any:
    """Build the FastMCP server exposing SupplyGuard procurement and risk tools."""
    if FastMCP is None:
        return None
    server = FastMCP("supplyguard-procurement")

    @server.tool()
    def create_purchase_order(
        action_id: str,
        supplier_id: str,
        component_id: str,
        quantity: int,
        unit_price: float,
        delivery_date: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute an approved purchase order in the simulated procurement system."""
        return get_procurement_system().create_purchase_order(
            action_id=action_id,
            supplier_id=supplier_id,
            component_id=component_id,
            quantity=quantity,
            unit_price=unit_price,
            delivery_date=delivery_date,
            thread_id=thread_id,
        ).model_dump()

    @server.tool()
    def expedite_purchase_order(
        action_id: str,
        po_id: str,
        days_gain: int = 7,
        fee_pct: float = 6.0,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Expedite an existing open purchase order idempotently."""
        return get_procurement_system().expedite_purchase_order(
            action_id=action_id,
            po_id=po_id,
            days_gain=days_gain,
            fee_pct=fee_pct,
            thread_id=thread_id,
        )

    @server.tool()
    def request_stock_transfer(
        action_id: str,
        component_id: str,
        from_location: str,
        to_location: str,
        qty: int,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request an internal stock transfer between warehouse locations."""
        return get_procurement_system().request_stock_transfer(
            action_id=action_id,
            component_id=component_id,
            from_location=from_location,
            to_location=to_location,
            qty=qty,
            thread_id=thread_id,
        )

    @server.tool()
    def update_production_schedule(
        action_id: str,
        product_id: str,
        week_start: str,
        planned_units: int,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a factory production schedule slot idempotently."""
        return get_procurement_system().update_production_schedule(
            action_id=action_id,
            product_id=product_id,
            week_start=week_start,
            planned_units=planned_units,
            thread_id=thread_id,
        )

    @server.tool()
    def get_supplier_risk(
        supplier_id: str,
        supplier_name: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch external geopolitical and logistics risk alerts for a supplier."""
        return get_procurement_system().get_supplier_risk(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            country=country,
        ).model_dump()

    @server.tool()
    def check_inventory_balance(component_id: str) -> Dict[str, Any]:
        """Check on-hand, reserved, quarantined, and usable stock for a component."""
        return get_procurement_system().check_inventory_balance(component_id=component_id)

    return server


mcp = build_fastmcp_server()


if __name__ == "__main__":
    if mcp is None:
        raise RuntimeError("mcp package is required to run the FastMCP server.")
    mcp.run(transport="stdio")
