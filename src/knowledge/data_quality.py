"""Detect and resolve the planted data-quality problems in the support data (#77).

Run: python -m src.knowledge.data_quality   (prints every finding; reads files only, no database)

The provided data is never modified. Problems are detected and resolved at read time:
  - findings()            every problem, in the shape of structured/data_quality_manifest.csv
  - resolve_supplier()    canonical supplier id(s) for a free-text name; several = ambiguous, ask
  - canonical_component_id()  'MC096' -> 'MC-96', '' -> None
  - certification_valid() expired certificates beat a stale ERP status (Borealis)
  - document_precedence() rank per policies.json source_precedence, superseded versions marked
  - conflicting_claims()  numeric claims that disagree across documents, with the winning source
  - shared_upstream()     alternatives for one component that share a tier-2 manufacturer
"""
import csv
import json
import re
from collections import defaultdict
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

from .ingest_documents import DOCUMENTS, INJECTION, parse

DATA = Path(__file__).resolve().parents[1] / "support-data"
STRUCTURED = DATA / "structured"
POLICIES = json.loads((DATA / "config" / "policies.json").read_text(encoding="utf-8"))
SCENARIO_DATE = date.fromisoformat(POLICIES["scenario_date"])
STALE_COUNT_DAYS = 180

# policies.json source_precedence -> doc_type; lower rank wins. Documents of other types
# (procedures, incident reports, finance) state no supplier facts and get no rank.
PRECEDENCE = {"contract": 0, "qualification": 1, "supplier_notice": 2, "email": 3}
assert [p.split()[0] for p in POLICIES["source_precedence"][:4]] == ["contract", "qualification", "supplier", "supplier"]


@cache
def table(name: str) -> tuple[dict[str, str], ...]:
    with open(STRUCTURED / name, encoding="utf-8", newline="") as f:
        return tuple(csv.DictReader(f))


# --- identifiers -------------------------------------------------------------------------------
def canonical_component_id(raw: str | None) -> str | None:
    m = re.fullmatch(r"\s*MC-?0*(\d+)\s*", raw or "", re.I)
    return f"MC-{int(m[1])}" if m else None


SUFFIXES = {"ltd", "gmbh", "inc", "ag", "sa", "srl", "plc", "co", "corp", "comp"}


def _tokens(name: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", name.lower()) if t not in SUFFIXES]


def resolve_supplier(name: str) -> list[dict[str, str]]:
    """Suppliers a free-text name can mean. One match: resolved. Several: ambiguous, ask the user."""
    query = _tokens(name)
    if not query:
        return []
    suppliers = [(s, _tokens(s["name"])) for s in table("suppliers.csv")]
    exact = [s for s, t in suppliers if t == query]
    hits = exact or [s for s, t in suppliers if t[: len(query)] == query]
    return [{"supplier_id": s["supplier_id"], "name": s["name"]} for s in hits]


# --- certifications ----------------------------------------------------------------------------
def certification_valid(supplier_id: str, as_of: date = SCENARIO_DATE) -> bool:
    s = next(s for s in table("suppliers.csv") if s["supplier_id"] == supplier_id)
    expiry = date.fromisoformat(s["certification_expiry"]) if s["certification_expiry"] else None
    return s["certification_status"] == "valid" and expiry is not None and expiry >= as_of


# --- documents ---------------------------------------------------------------------------------
@cache
def documents() -> tuple[tuple[dict[str, str], str], ...]:
    return tuple(parse(p) for p in sorted(DOCUMENTS.glob("*/*.md")))


# Only these are versions of one standing document per supplier; two notices or incident
# reports about the same supplier describe different events and never supersede each other.
VERSIONED = {"contract", "qualification"}


def document_precedence() -> dict[str, dict[str, Any]]:
    """source_id -> rank (policies.json), superseded flag and the version that replaces it."""
    latest: dict[tuple[str, str], dict[str, str]] = {}
    for meta, _ in documents():
        key = (meta.get("supplier_id", ""), meta["doc_type"])
        if meta["doc_type"] in VERSIONED and meta.get("supplier_id") and meta.get("version"):
            cur = latest.get(key)
            if cur is None or (int(meta["version"]), meta["effective_date"]) > (int(cur["version"]), cur["effective_date"]):
                latest[key] = meta
    out = {}
    for meta, _ in documents():
        newer = latest.get((meta.get("supplier_id", ""), meta["doc_type"]))
        superseded = bool(newer and newer["source_id"] != meta["source_id"])
        out[meta["source_id"]] = {
            "rank": PRECEDENCE.get(meta["doc_type"]),
            "superseded": superseded,
            "superseded_by": newer["source_id"] if superseded else None,
        }
    return out


CLAIMS = {
    "delay_days": [r"(\d+)-day delay", r"delay[^.]*?(?:closer to|of|by)\s*(\d+)\s*days"],
    "lead_time_days": [r"lead time\b[^.\d]*?(\d+)\s*(?:calendar\s*)?days", r"(\d+)-day lead time"],
    "monthly_capacity_units": [r"monthly capacity[^:]*:\s*([\d,]+)\s*units", r"([\d,]+)\s*units per month"],
    "expedite_fee_pct": [r"expedit[^.]*?(\d+(?:\.\d+)?)%"],
}


def claims(body: str) -> dict[str, float]:
    """First value per attribute stated in a document body (markdown emphasis removed)."""
    text = body.replace("**", "")
    found = {}
    for attr, patterns in CLAIMS.items():
        for p in patterns:
            if m := re.search(p, text, re.I):
                found[attr] = float(m[1].replace(",", ""))
                break
    return found


def conflicting_claims() -> list[dict[str, Any]]:
    """Per supplier and attribute, current documents that disagree, and which source wins."""
    prec = document_precedence()
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for meta, body in documents():
        sid, p = meta["source_id"], prec[meta["source_id"]]
        if not meta.get("supplier_id") or p["rank"] is None or p["superseded"]:
            continue
        for attr, value in claims(body).items():
            by_key[(meta["supplier_id"], attr)].append(
                {"source_id": sid, "doc_type": meta["doc_type"], "value": value,
                 "rank": p["rank"], "effective_date": meta["effective_date"]})
    out = []
    for (supplier_id, attr), sources in sorted(by_key.items()):
        if len({s["value"] for s in sources}) > 1:
            winner = min(sources, key=lambda s: (s["rank"], s["effective_date"][::-1]))
            out.append({"supplier_id": supplier_id, "attribute": attr, "sources": sources,
                        "winner": winner["source_id"], "value": winner["value"]})
    return out


def shared_upstream(component_id: str) -> list[dict[str, Any]]:
    """Suppliers of one component that depend on the same upstream manufacturer (no real diversification).

    Checked per component of the case: across the whole catalogue many suppliers share
    U05-U08, which only matters when they are alternatives for the same part.
    """
    suppliers = {s["supplier_id"]: s for s in table("suppliers.csv")}
    groups: dict[str, list[str]] = defaultdict(list)
    for sc in table("supplier_components.csv"):
        u = suppliers[sc["supplier_id"]]["upstream_manufacturer_id"]
        if sc["component_id"] == component_id and u:
            groups[u].append(sc["supplier_id"])
    return [{"upstream_id": u, "supplier_ids": sorted(g), "names": [suppliers[x]["name"] for x in sorted(g)]}
            for u, g in sorted(groups.items()) if len(g) > 1]


# --- findings ----------------------------------------------------------------------------------
def findings() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    def add(issue_type: str, file: str, ref: str, note: str) -> None:
        out.append({"issue_type": issue_type, "file": file, "record_ref": ref, "note": note})

    suppliers = {s["supplier_id"]: s for s in table("suppliers.csv")}
    components = {c["component_id"] for c in table("components.csv")}

    for po in table("purchase_orders.csv"):
        raw = po["component_id"]
        if not raw:
            add("missing_identifier", "structured/purchase_orders.csv", po["po_id"], "component_id blank")
        elif raw not in components:
            add("identifier_format", "structured/purchase_orders.csv", po["po_id"],
                f"component_id '{raw}' (non-canonical, means {canonical_component_id(raw)})")
        if po["supplier_name_as_entered"] != suppliers[po["supplier_id"]]["name"]:
            add("supplier_name_variant", "structured/purchase_orders.csv", po["po_id"],
                f"entered as '{po['supplier_name_as_entered']}'")
        if po["actual_delivery_date"] and po["actual_delivery_date"] < po["order_date"]:
            add("conflicting_dates", "structured/purchase_orders.csv", po["po_id"], "delivered before ordered")

    promised = {po["po_id"]: po["promised_date"] for po in table("purchase_orders.csv")}
    first_event: dict[tuple[str, ...], str] = {}
    for ev in table("shipment_updates.csv"):
        key = tuple(v for k, v in ev.items() if k != "shipment_event_id")
        if key in first_event:
            add("duplicate_event", "structured/shipment_updates.csv", ev["shipment_event_id"],
                f"duplicate of {first_event[key]}")
        else:
            first_event[key] = ev["shipment_event_id"]
        # A late shipment keeps the promised date as eta; an eta that differs from it and already
        # lies before the in-transit event was entered wrongly.
        if (ev["status"] == "in_transit" and ev["eta"] and ev["eta"] < ev["event_date"]
                and ev["eta"] != promised.get(ev["po_id"])):
            add("conflicting_dates", "structured/shipment_updates.csv", ev["shipment_event_id"], "eta before event_date")

    # Same sender, same day, same text = one message received twice; the same template on another
    # day is a separate event. The first message is reported, with its copies.
    copies: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for m in table("supplier_message_inbox.csv"):
        copies[(m["received"], m["sender"], m["text"])].append(m["message_id"])
    for ids in copies.values():
        if len(ids) > 1:
            first, *rest = sorted(ids)
            add("duplicate_message", "structured/supplier_message_inbox.csv", first,
                f"exact duplicate text ({', '.join(rest)})")

    for inv in table("inventory.csv"):
        age = (SCENARIO_DATE - date.fromisoformat(inv["last_counted_date"])).days
        if age > STALE_COUNT_DAYS:
            add("stale_record", "structured/inventory.csv", f"{inv['component_id']}@{inv['location_id']}",
                f"last_counted_date older than {STALE_COUNT_DAYS} days ({age} d)")

    for s in suppliers.values():
        if s["erp_status"] == "approved" and not certification_valid(s["supplier_id"]):
            add("stale_status", "structured/suppliers.csv", s["supplier_id"],
                f"ERP still says 'approved' but certificate is {s['certification_status']} ({s['certification_expiry']})")

    seen_ambiguous = set()
    for s in suppliers.values():
        hits = resolve_supplier(s["name"].split()[0])
        ids = "/".join(h["supplier_id"] for h in hits)
        if len(hits) > 1 and ids not in seen_ambiguous:
            seen_ambiguous.add(ids)
            add("ambiguous_supplier_name", "structured/suppliers.csv", ids,
                f"'{s['name'].split()[0]}' alone matches {', '.join(h['name'] for h in hits)}")

    supplying = {sc["supplier_id"] for sc in table("supplier_components.csv")}
    idle = sorted(set(suppliers) - supplying)
    if idle:
        add("disconnected_entity", "structured/supplier_components.csv", ",".join(idle), "Suppliers exist but supply no component")
    in_bom = {b["component_id"] for b in table("bill_of_materials.csv")}
    unused = sorted(components - in_bom, key=lambda c: int(c[3:]))
    if unused:
        add("disconnected_entity", "structured/components.csv", ",".join(unused), "Components exist but are used in no product BOM")

    for sid in shared_upstream("MC-17"):
        add("shared_upstream", "structured/suppliers.csv", "/".join(sid["supplier_ids"]),
            f"MC-17 suppliers {' and '.join(sid['names'])} both source from {sid['upstream_id']}")

    for sid, p in document_precedence().items():
        if p["superseded"]:
            add("stale_document", "documents/", sid, f"superseded by {p['superseded_by']}")
    for meta, body in documents():
        if INJECTION.search(body):
            add("prompt_injection", "documents/", meta["source_id"], "text addressed to an AI assistant: treat as data, report")
    for c in conflicting_claims():
        vals = ", ".join(f"{s['source_id']}={s['value']:g}" for s in c["sources"])
        add("conflicting_information", "documents/", c["supplier_id"],
            f"{c['attribute']}: {vals}; precedence -> {c['winner']}")
    return out


if __name__ == "__main__":
    for f in findings():
        print(f"{f['issue_type']:25} {f['record_ref']:30} {f['note']}")
