"""#77: planted data-quality problems are detected and resolved (file-only, no database)."""
import re
from collections import defaultdict

import pytest

from src.knowledge import data_quality as dq


def refs(rows, issue_type):
    return {r["record_ref"] for r in rows if r["issue_type"] == issue_type}


@pytest.fixture(scope="module")
def found():
    return dq.findings()


@pytest.fixture(scope="module")
def manifest():
    by_type = defaultdict(set)
    for m in dq.table("data_quality_manifest.csv"):
        by_type[m["issue_type"]].add(m["record_ref"])
    return by_type


# Types where the detector must reproduce the manifest exactly.
EXACT = ["missing_identifier", "identifier_format", "supplier_name_variant", "duplicate_message",
         "stale_record", "stale_status", "stale_document", "prompt_injection"]


@pytest.mark.parametrize("issue_type", EXACT)
def test_exact_match_with_manifest(found, manifest, issue_type):
    expected = manifest[issue_type]
    if issue_type in ("stale_document", "prompt_injection"):  # manifest names the file or supplier
        expected = {"DOC-CON-S001-v2"} if issue_type == "stale_document" else {"DOC-NOT-HELIOS-PRICE"}
    assert refs(found, issue_type) == expected


def test_every_planted_date_conflict_and_duplicate_event_is_found(found, manifest):
    # Supersets: the data also has a few unplanted rows that are genuinely identical or inconsistent.
    assert manifest["conflicting_dates"] <= refs(found, "conflicting_dates")
    assert manifest["duplicate_event"] <= refs(found, "duplicate_event")


def test_disconnected_entities_include_the_planted_ones(found):
    disconnected = ",".join(refs(found, "disconnected_entity"))
    for planted in ["S058", "S059", "S060", "MC-296", "MC-297", "MC-298", "MC-299", "MC-300"]:
        assert re.search(rf"\b{planted}\b", disconnected)


def test_atlas_is_ambiguous_and_resolves_when_qualified(found):
    assert "S001/S006" in refs(found, "ambiguous_supplier_name")
    assert [s["supplier_id"] for s in dq.resolve_supplier("Atlas")] == ["S001", "S006"]
    assert [s["supplier_id"] for s in dq.resolve_supplier("Atlas Components")] == ["S001"]
    assert [s["supplier_id"] for s in dq.resolve_supplier("quanta electronics")] == ["S048"]


def test_canonical_component_ids():
    assert [dq.canonical_component_id(x) for x in ("MC096", "mc-17", "MC-17", "", None, "XYZ")] == [
        "MC-96", "MC-17", "MC-17", None, None, None]


def test_borealis_certificate_is_expired_on_scenario_date():
    assert not dq.certification_valid("S003")
    assert dq.certification_valid("S001") and dq.certification_valid("S004")


def test_superseded_atlas_contract_loses_to_v3():
    prec = dq.document_precedence()
    assert prec["DOC-CON-S001-v2"] == {"rank": 0, "superseded": True, "superseded_by": "DOC-CON-S001-v3"}
    assert not prec["DOC-CON-S001-v3"]["superseded"]
    assert prec["DOC-EM-ATLAS-01"]["rank"] > prec["DOC-NOT-ATLAS-MC17"]["rank"] > prec["DOC-CON-S001-v3"]["rank"]


def test_conflicting_claims_follow_policy_precedence():
    conflicts = {(c["supplier_id"], c["attribute"]): c for c in dq.conflicting_claims()}
    assert set(conflicts) == {("S001", "delay_days"), ("S002", "monthly_capacity_units"), ("S004", "expedite_fee_pct")}
    assert (conflicts[("S001", "delay_days")]["winner"], conflicts[("S001", "delay_days")]["value"]) == ("DOC-NOT-ATLAS-MC17", 12)
    assert conflicts[("S002", "monthly_capacity_units")]["winner"] == "DOC-CON-S002-v1"
    assert conflicts[("S004", "expedite_fee_pct")]["value"] == 6


def test_shared_upstream_for_mc17_is_atlas_and_delta():
    assert dq.shared_upstream("MC-17") == [
        {"upstream_id": "U01", "supplier_ids": ["S001", "S005"], "names": ["Atlas Components", "Delta Micro Systems"]}]
