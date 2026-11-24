"""Simulated Procurement System & External Risk MCP Integration.

Platform & Workflow Roles | Scope: mcp, platform
Target: Issue #38

Implements MCP-compliant tool handlers for:
1. create_purchase_order: Idempotent order execution returning PurchaseOrderReceipt
2. get_supplier_risk: External risk evaluation querying the External Risk Service
3. check_inventory_balance: Real-time inventory calculation (usable vs quarantined)
"""

from __future__ import annotations

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

from src.core.contracts import PurchaseOrderReceipt, PurchaseOrderRequest, SupplierRiskInfo


def _get_risk_feed(region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query External Risk Service over HTTP or load local risk feed."""
    feed_file = REPO_ROOT / "src" / "support-data" / "external_service" / "risk_feed.json"
    risk_url = os.getenv("EXTERNAL_RISK_URL")
    
    # If explicit external URL provided (e.g. inside Docker container), query it
    if risk_url and not risk_url.startswith("http://localhost"):
        url = f"{risk_url}/alerts"
        if region:
            url += f"?region={region}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SupplyGuard-MCP"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            pass

    # Fast local fallback
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


class SimulatedProcurementSystem:
    """Simulated ERP procurement engine with strict idempotency."""

    def __init__(self):
        self._executed_orders: Dict[str, PurchaseOrderReceipt] = {}

    def create_purchase_order(
        self,
        action_id: str,
        supplier_id: str,
        component_id: str,
        quantity: int,
        unit_price: float,
        delivery_date: Optional[str] = None,
    ) -> PurchaseOrderReceipt:
        """Create a new purchase order with idempotency check.

        If action_id was already executed, returns the previously created receipt.
        """
        # 1. Check in-memory / state cache
        if action_id in self._executed_orders:
            return self._executed_orders[action_id]

        # 2. Check database audit_log if DB is available
        try:
            from src.db.idempotency import get_action_status, is_action_executed, record_action
            if is_action_executed(action_id):
                status_rec = get_action_status(action_id)
                # Return recovered receipt
                receipt = PurchaseOrderReceipt(
                    order_id=f"PO-SUP-REC-{action_id[:8].upper()}",
                    action_id=action_id,
                    supplier_id=supplier_id,
                    component_id=component_id,
                    quantity=quantity,
                    total_amount=round(quantity * unit_price, 2),
                    status="confirmed",
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self._executed_orders[action_id] = receipt
                return receipt
        except Exception:
            pass

        # 3. Generate new Purchase Order
        order_num = len(self._executed_orders) + 9001
        order_id = f"PO-SUP-2026-{order_num}"
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

        # 4. Record execution in PostgreSQL audit_log and purchase_orders table if connected
        try:
            from src.db.connection import get_pooled_connection
            with get_pooled_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        # Record in audit_log
                        cur.execute(
                            """
                            INSERT INTO audit_log (
                                action_id, thread_id, action_type, status,
                                parameters, rationale, executed_at
                            )
                            VALUES (%s, %s, %s, %s, %s::jsonb, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (action_id) DO UPDATE SET
                                status = 'executed',
                                executed_at = CURRENT_TIMESTAMP;
                            """,
                            (
                                action_id,
                                f"thread-{action_id[:8]}",
                                "purchase_alternative",
                                "executed",
                                json.dumps(receipt.model_dump()),
                                f"Simulated PO {order_id} issued to supplier {supplier_id}",
                            ),
                        )
                        # Record in purchase_orders table
                        cur.execute(
                            """
                            INSERT INTO purchase_orders (
                                po_id, supplier_id, component_id, qty, unit_price_eur,
                                order_date, promised_date, status
                            )
                            VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s, 'confirmed')
                            ON CONFLICT (po_id) DO NOTHING;
                            """,
                            (
                                order_id,
                                supplier_id,
                                component_id,
                                quantity,
                                unit_price,
                                delivery_date or "2026-11-01",
                            ),
                        )
        except Exception:
            pass

        return receipt

    def get_supplier_risk(
        self,
        supplier_id: str,
        supplier_name: Optional[str] = None,
        country: Optional[str] = None,
    ) -> SupplierRiskInfo:
        """Fetch supplier risk combining regional feed and supplier attributes."""
        country_code = country or "DE"
        # If supplier_id S001, map to Atlas Components / Germany / Taiwan upstream
        if supplier_id == "S001":
            country_code = "DE"
            supplier_name = supplier_name or "Atlas Components"
        elif supplier_id == "S002":
            country_code = "RO"
            supplier_name = supplier_name or "Balkan MicroSystems"
        elif supplier_id == "S003":
            country_code = "SE"
            supplier_name = supplier_name or "Nordic SemiTech"

        alerts = _get_risk_feed(country_code)
        # Also check Taiwan upstream wafer fab risk (Veltro Semiconductor)
        upstream_alerts = _get_risk_feed("TW")

        risk_score = 0.1
        geo_risk = "Low"
        logistics = "Normal"
        notes = []

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

        if supplier_id == "S001" and upstream_alerts:
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

    def check_inventory_balance(self, component_id: str) -> Dict[str, int]:
        """Compute usable vs reserved vs quarantined stock for a component."""
        try:
            from src.db.connection import get_pooled_connection
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

        # Fallback reading directly from synthetic CSV
        inv_csv = REPO_ROOT / "src" / "support-data" / "structured" / "inventory.csv"
        if inv_csv.exists():
            import csv
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

        # Default fallback
        return {
            "component_id": component_id,
            "on_hand": 5200,
            "reserved": 1400,
            "quarantined": 600,
            "usable": 3200,
        }


# Singleton system instance
_PROCUREMENT_SYSTEM = SimulatedProcurementSystem()


def get_procurement_system() -> SimulatedProcurementSystem:
    """Return the singleton instance of SimulatedProcurementSystem."""
    return _PROCUREMENT_SYSTEM
