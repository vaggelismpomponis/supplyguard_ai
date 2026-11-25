# SupplyGuard AI – Support Data

Synthetic, fictional data for the capstone.

| Folder | Content |
|---|---|
| `structured/` | Operational tables (CSV) for PostgreSQL: 60 suppliers, 300 components, 80 products (617 BOM lines), 2,000 purchase orders, 1,000 inventory records, 1,500 customer orders, 300 historical cases, production schedule, reservations, quarantine lots, shipment updates (1,100+), supplier message inbox (with duplicates), `data_sources.csv` (provenance registry), 40 approved incident memories (`.jsonl`), `data_quality_manifest.csv` |
| `documents/` | 212 markdown documents with front matter (`source_id`, `version`, `effective_date`, `access_scope`) for pgvector / ChromaDB: contracts (61, incl. one superseded), qualification records (60), procedures (12), supplier notices (42), e-mails (6), incident reports (30), finance sheet (1). `documents_index.csv` lists them all |
| `graph/` | Neo4j node/relationship CSVs + `load.cypher` (Supplier, Upstream, Component, Product, Factory, Customer); every node and relationship carries `sourceId` and `effectiveDate` |
| `evaluation/` | `golden_scenario.json` (MC-17 case with expected facts) and `eval_cases.jsonl` (105 held-out cases: impact, ambiguity, prompt injection, follow-ups, restart/recovery, policy/authorization) |
| `config/` | `policies.json` (cap €75k/€90k, approval tiers, precedence) and `users.csv` (roles and document scopes for authorization tests), `procurement_system_operations.json` (contract of the simulated procurement MCP system) |
| `external_service/` | `risk_feed.json` + `external_info_service.py` – independent service to expose via MCP/HTTP |

## The MC-17 golden scenario
- Atlas Components (S001) announces a 12-day delay on **PO-2026-9001** (6,000 units, due 2026-10-26, now 2026-11-07). Scenario date: 2026-10-19.
- MC-17 is used by 6 products, two per plant: P012/P047 (Stuttgart), P023/P058 (Katowice), P031/P066 (Lyon). Demand is 150 units/day per plant, 450 in total.
- Inventory: on hand 5,200, reserved 1,400, quarantined 600 (lot LOT-KAT-0932), so usable stock is **3,200**. Days of cover at each plant's own warehouse: Stuttgart 8.7, Katowice 4.0, Lyon 3.3, plus 800 units at the hub.
- Reserved stock is tied to six tier-1 customer orders (`reservations.csv`). Open order volume is about 90% of the 12-week production plan.
- Uncovered demand until Atlas arrives: **5,350 units**. Cordillera alone cannot cover it (3,000 units/month). `golden_scenario.json` gives feasible reference plans at about EUR 30k (about EUR 39k with Delta), both under the EUR 75k cap.
- Alternatives: Helios (cheapest, 21 d, real capacity 1,500/mo), Borealis (fast but **ISO 9001 expired**), Cordillera (viable, independent upstream, open PO-2026-9002 expeditable), Delta (**shares upstream Veltro with Atlas**). Upstream manufacturers U01-U04 are used only by these five suppliers.
- Conflicts: Atlas e-mail 16 d vs notice 12 d; Helios capacity 1,500 vs 4,000; Cordillera expedite 10% vs 6%; Atlas contract v2 (stale) vs v3.
- Security: `DOC-NOT-HELIOS-PRICE` contains a hidden prompt injection. The finance sheet is `finance-confidential`.

## Deliberate data-quality problems
Listed with ground truth in `structured/data_quality_manifest.csv`: ambiguous supplier names (Atlas Components vs Atlas Logistik), supplier-name variants and blank/non-canonical IDs in POs, delivered-before-ordered dates, stale inventory counts, duplicate messages, stale/superseded contract, stale ERP status, disconnected graph entities (suppliers S058–S060, components MC-296…MC-300).

## Notes
- `policies.json` and `users.csv` add project assumptions that the assignment document does not define: approval tiers, a finance director and finance controller, and a read-only viewer role.
- "At risk" in `eval_cases.jsonl` = open customer orders due within 60 days on products whose BOM contains the component (a baseline; the agent should refine with stock and timing).
- No labelled extraction/routing training sets are included, since model training was removed from the project.
