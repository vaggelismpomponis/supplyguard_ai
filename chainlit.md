# 🏭🛡️ SupplyGuard AI — Operator & Executive User Guide
**An Agentic Supply Chain Disruption and Recovery Platform | Code.Hub × PwC Capstone**

Welcome to **SupplyGuard AI**. This platform assists procurement managers, finance controllers, operations analysts, and incident coordinators in investigating supplier disruptions, quantifying operational and financial impact, comparing recovery strategies with deterministic calculators, and executing payload-bound recovery plans under strict human approval.

---

## 🔐 1. Role-Based Access Control (RBAC)

SupplyGuard AI enforces role-based document retrieval scopes and approval authority based on `config/users.csv`:

| Role | Operator | Document Scopes | Approval Authority |
| :--- | :--- | :--- | :--- |
| **Procurement Manager** | Maria Keller (`u-pm-01`) | `public`, `internal`, `procurement` | Approve / Reject / Modify plans up to **`€75,000`** |
| **Finance Controller** | Paul Novak (`u-fc-01`) | `public`, `internal`, `procurement`, `finance-confidential` | Full access incl. **`DOC-FIN-01-v1`** margin/penalty sheet & **`€90,000`** cap |
| **Read-Only Guest** | Read Only Guest (`u-ro-01`) | `public` | Read-only viewer (cannot approve or execute Purchase Orders) |

Use the **Role Switcher buttons** on the welcome screen or type `/role procurement`, `/role finance`, or `/role guest` at any time.

---

## 📋 2. Typical Disruption Workflow

### Step 1 · Report a Disruption Incident
Paste the incoming disruption message into the chat:
> **Reference Scenario:** *"Supplier Atlas Components has announced a 12-day delay for component MC-17. Determine which customer commitments are at risk, investigate alternative sources, and recommend a recovery plan. Additional spending must not exceed €75,000. Do not create a purchase order without approval."*

### Step 2 · Clarification for Ambiguous Entities
SupplyGuard AI never guesses missing or ambiguous identifiers. If a message only says *"Atlas says the motor board is late"*, the **Triage Subagent** pauses and asks you to clarify between **Atlas Components (`S001`, Stuttgart)** and **Atlas Logistik GmbH (`S006`, Hamburg)**.

### Step 3 · Follow Live Subagent Telemetry & Operational Impact Dashboard
Watch live `cl.Step` progress indicators across all 6 specialist subagents:
1. **Triage & Entity Extraction Subagent** (`S001`, `MC-17`, `12-day delay`, `€75k` cap)
2. **Operational Impact Analyzer Subagent** (`3,200` usable of `5,200` physical units; `1,400` reserved for 6 Tier-1 orders; `600` quarantined in `LOT-KAT-0932`; Lyon `3.3d` and Katowice `4.0d` run out first; `6` products, `77` open customer orders, `5,350` uncovered units)
3. **Contract & Provenance Specialist Subagent** (flags conflicts between formal notices, contracts, and emails; ignores superseded `DOC-CON-S001-v2`; blocks Borealis `S003` due to expired ISO 9001 certificate)
4. **Supply Graph Dependency Subagent** (detects shared Tier-2 upstream manufacturer **Veltro Semiconductor `U01`** between Atlas `S001` and Delta `S005`)
5. **Recovery Strategy Optimizer Subagent** (compares strategies A–E, separating **Recovery Cost** from **Revenue at Risk**)
6. **Adversarial Challenger & Guardrail Subagent** (neutralizes and reports the prompt injection in `DOC-NOT-HELIOS-PRICE`)

### Step 4 · Review the Payload-Bound Approval Card
The approval card binds cryptographically (`SHA-256` payload digest) to the exact supplier, quantity, unit price, and total cost (`€30,378.00`, within the `€75,000.00` cap):
- Click **✅ Approve** to execute idempotently in the Simulated Procurement System (`PO-SUP-2026-...`, `EXP-PO-2026-9002`, `TRF-2026-...`) and download the **Markdown (`.md`) and PDF (`.pdf`) Incident Report**.
- Click **✏️ Modify Plan** to change quantities or budget caps—any change invalidates the prior payload and triggers revalidation and a fresh approval card.
- Click **❌ Reject** to abort execution without altering any procurement state.

---

## 💬 3. Multi-Turn Follow-Up Questions & Container Restart Recovery

Ask follow-up questions directly from the persisted case memory:
- *"Why did you reject Supplier Helios?"*
- *"What changes if we increase the spending limit to €90,000?"*
- *"Can we protect our highest-priority customers using existing stock?"*
- *"Show me the margin by customer tier."* *(Requires Finance Controller role)*
- *"Resume the case I was reviewing yesterday."* or `/resume <thread_id>` after `docker compose restart app`
