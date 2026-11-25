---
name: disruption-triage
description: SupplyGuard rules for extracting disruption facts, detecting ambiguous suppliers, and delegating investigation.
---

# SupplyGuard Disruption Triage Skill

Follow these steps in order for every incoming disruption report:

## Step 1 - Extract mandatory facts
- `supplier_id` / `supplier_name` (from `suppliers.csv`)
- `component_id` (canonical form `MC-<number>`)
- `delay_days` (integer days)
- `spending_cap` (default EUR 75,000 unless explicitly authorized higher)

## Step 2 - Never guess ambiguous entities
If a supplier name matches more than one master record (e.g. `Atlas` -> `S001 Atlas Components` vs `S006 Atlas Logistik GmbH`) or any mandatory field is missing, stop and ask the operator for clarification via interrupt.

## Step 3 - Delegate specialist investigation
Once `DisruptionFact.is_complete()` is true, delegate to:
1. `impact_subagent`: usable vs reserved vs quarantined stock, BOM products, factory cover, open orders.
2. `contract_subagent`: RBAC-scoped documents, source precedence, ISO 9001 validity, prompt-injection scan.
3. `graph_subagent`: Neo4j multi-tier upstream dependencies (`[:SOURCES_FROM]`) and external risk alerts.
