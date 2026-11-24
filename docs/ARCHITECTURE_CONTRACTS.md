# Architecture Contracts & Domain Specification – SupplyGuard AI

**Project:** SupplyGuard AI (Agentic Supply Chain Disruption and Recovery Platform)  
**Target:** Code.Hub × PwC Agentic AI Bootcamp Capstone Project  
**Status:** Agreed & Frozen (All 5 Roles Aligned)  
**Core Orchestration Engine:** **Deep Agents (`deepagents`)**  
**Code Reference:** `src/agent/schemas.py`, `src/agent/deep_agent.py`, `src/knowledge/tools.py`

---

## 1. Executive Summary & Contracts-First Strategy

To enable 5 team members to develop simultaneously across different branches without waiting on each other and with **zero merge conflicts**, all core domain interfaces, Pydantic data schemas, tool signatures, and MCP integration boundaries are frozen on Day 1.

```text
+-------------------------------------------------------------------------------------------------+
|                                    SupplyGuard AI Contracts                                    |
|                                                                                                 |
|   DisruptionFact  <--->  OperationalImpact  <--->  SupplierGraphResult / DocumentResult         |
|         |                        |                                      |                       |
|         v                        v                                      v                       |
|   RecoveryOption  --------------->  ApprovalPayload (Strict Binding)  <--+                      |
+-------------------------------------------------------------------------------------------------+
          |                                        |                               |
          v                                        v                               v
    [Interface]                               [Workflow]                      [Knowledge]
 Chainlit UI & RBAC                 Deep Agents & Subagents               Ingestion & Seeding
(Procurement/Finance)               (Planning & Scratchpad)             (Postgres, Neo4j, Chroma)
```

Each role builds against these contracts using mocks until the Phase 3/4 integration milestones.

---

## 2. Core Pydantic Models & Schemas

### 2.1 Action Types (`ActionType`)

The system compares recovery options and executes approved state-changing actions in the simulated procurement system:

```python
from enum import Enum

class ActionType(str, Enum):
    TRANSFER_INVENTORY = "transfer_inventory"         # Move usable stock between internal factories
    EXPEDITE_ORDER = "expedite_order"                 # Expedite existing purchase order delivery
    PURCHASE_ALTERNATIVE = "purchase_alternative"     # Create purchase order with qualified alternate supplier
    REALLOCATE_COMPONENTS = "reallocate_components"   # Prioritize component allocations to tier-1 customers
    RESCHEDULE_PRODUCTION = "reschedule_production"   # Shift production runs across the 12-week schedule
    ANSWER_POLICY = "answer_policy"                   # Informative query response from documentary evidence
    REQUEST_CLARIFICATION = "request_clarification"   # Pause to prompt user for ambiguous/missing facts
```

### 2.2 Action Lifecycle Status (`ActionStatus`)

State-changing actions follow a strict state machine to guarantee human-in-the-loop safety and idempotency:

```python
class ActionStatus(str, Enum):
    PENDING = "pending"       # Strategy formulated, awaiting human approval
    APPROVED = "approved"     # Explicitly approved by authorized operator
    EXECUTED = "executed"     # Successfully executed in simulated procurement; cannot be re-executed
    REJECTED = "rejected"     # Rejected by operator; alternative plan required
```

### 2.3 User Access Scopes (`AccessScope`)

Chainlit authentication enforces role-based access control (RBAC):

```python
class AccessScope(str, Enum):
    PROCUREMENT = "procurement"  # Procurement managers: standard operational & contract docs
    FINANCE = "finance"          # Finance controllers: margin, price & penalty-confidential docs
    PUBLIC = "public"            # Read-only guests: public announcements and high-level case status
```

### 2.4 Structured Disruption Facts (`DisruptionFact`)

Extracted from incoming free-form user incident messages:

```python
from typing import Optional, List
from pydantic import BaseModel, Field

class DisruptionFact(BaseModel):
    supplier_id: Optional[str] = Field(default=None, description="Identifier of the supplier (e.g. S001)")
    supplier_name: Optional[str] = Field(default=None, description="Canonical name of the supplier")
    component_id: Optional[str] = Field(default=None, description="Disrupted component (e.g. MC-17)")
    delay_days: Optional[int] = Field(default=None, description="Announced delay duration in days (e.g. 12)")
    spending_cap: float = Field(default=75000.0, description="Spending limit in EUR (€75,000 reference)")
    is_ambiguous: bool = Field(default=False, description="True if supplier name matches multiple entities")
    ambiguity_candidates: List[str] = Field(default_factory=list, description="Potential matches if ambiguous")

    def is_complete(self) -> bool:
        """Mandatory facts needed before starting investigation."""
        return bool(self.supplier_id and self.component_id and self.delay_days and not self.is_ambiguous)
```

*Contract Rule:* If `is_ambiguous` is `True` (e.g. user typed only "Atlas") or mandatory fields are missing, the agent **must not guess**. It must trigger `REQUEST_CLARIFICATION`.

### 2.5 Operational Impact Analysis (`OperationalImpact`)

Synthesized from inventory tables, BOMs, and factory production commitments:

```python
class OperationalImpact(BaseModel):
    component_id: str = Field(description="Component identifier")
    total_physical_units: int = Field(description="Total stock across all warehouses (e.g. 5,200)")
    usable_units: int = Field(description="Physical minus reserved and quarantined (e.g. 3,200)")
    reserved_units: int = Field(description="Units allocated to locked assembly batches (e.g. 1,400)")
    quarantined_units: int = Field(description="Units held in QA quarantine (e.g. 600)")
    affected_factories: List[str] = Field(description="Factories running out first (e.g. ['Katowice', 'Lyon'])")
    affected_products_count: int = Field(description="Number of product BOMs containing component (e.g. 6)")
    affected_customer_orders_count: int = Field(description="Open customer orders at risk (e.g. 77)")
    uncovered_demand_units: int = Field(description="Demand deficit during delay window (e.g. 5,350)")
```

### 2.6 Recovery Strategy Comparison (`RecoveryOption`)

Calculated deterministically by the Strategy Optimizer Subagent:

```python
class RecoveryOption(BaseModel):
    strategy_id: str = Field(description="Unique strategy key (e.g. STRAT-A)")
    action_type: ActionType = Field(description="Type of recovery action")
    supplier_id: Optional[str] = Field(default=None, description="Target supplier if purchase/expedite")
    supplier_name: Optional[str] = Field(default=None, description="Target supplier name")
    quantity: int = Field(description="Units provided or reallocated")
    lead_time_days: int = Field(description="Estimated delivery / execution lead time")
    recovery_cost: float = Field(description="Deterministic cost to execute (freight, price difference)")
    revenue_at_risk: float = Field(description="Protected or remaining revenue exposure")
    is_viable: bool = Field(description="Whether the strategy satisfies operational & policy constraints")
    rejection_reason: Optional[str] = Field(default=None, description="Detailed explanation if rejected")
```

### 2.7 Payload-Bound Human Approval Contract (`ApprovalPayload`)

Encapsulates the immutable payload presented on the Chainlit Approval Card:

```python
from typing import Dict, Any

class ApprovalPayload(BaseModel):
    action_id: str = Field(description="Unique UUID for strict idempotency tracking")
    case_id: str = Field(description="Unique incident case ID")
    action_type: ActionType = Field(description="Approved action type")
    target_supplier_id: Optional[str] = Field(default=None, description="Supplier code (e.g. S002)")
    target_supplier_name: Optional[str] = Field(default=None, description="Supplier name")
    component_id: str = Field(description="Component code (e.g. MC-17)")
    quantity: int = Field(description="Exact purchase or transfer quantity")
    unit_price: float = Field(description="Contracted unit price in EUR")
    total_cost: float = Field(description="Total expenditure (must be <= spending_cap)")
    spending_cap: float = Field(default=75000.0, description="Authorized budget cap")
    supporting_evidence: List[Dict[str, str]] = Field(default_factory=list, description="Citations and sources")
    status: ActionStatus = Field(default=ActionStatus.PENDING, description="Current approval status")
```

*Contract Rule (Payload Binding):* Human approval is strictly bound to this exact payload. If the user clicks "Modify Plan" or alters any parameter (quantity, supplier, price), the state is invalidated and a fresh validation and approval cycle is required. No Purchase Order may exist prior to approval.

---

## 3. Deep Agents Orchestration Model (`create_deep_agent`)

Orchestration is handled by **LangChain Deep Agents**, replacing low-level manual LangGraph graphs.

```text
+---------------------------------------------------------------------------------+
|                       Root Deep Agent (create_deep_agent)                      |
|                                                                                 |
|   • Planning Middleware: Dynamic task breakdown and execution loop              |
|   • Virtual Scratchpad: External memory for BOM, inventory, and notes           |
|   • Human Approval Interrupt Hook: Pauses before executing procurement          |
+---------------------------------------------------------------------------------+
          |                     |                      |                     |
          v                     v                      v                     v
   [Triage Subagent]   [Impact Subagent]      [Contract Subagent]   [Graph Subagent]
   Extract S001, MC-17 Usable vs Quarantined  Check ISO & certs     Neo4j Cypher tiers
   Clarify if needed   Katowice/Lyon deficit  Flag date conflicts   Detect shared fab
          |                     |                      |                     |
          +---------------------+----------------------+---------------------+
                                          |
                                          v
                         [Strategy Optimizer Subagent]
                         Formulates >=3 recovery options
                         Calls Deterministic Calculators (No LLM math)
                                          |
                                          v
                         [Adversarial Challenger Subagent]
                         Critiques assumptions, checks caps
                         Neutralizes planted prompt injections
                                          |
                                          v
                         [Human-in-the-Loop Interrupt]
                         Approval Card in Chainlit UI
                                          |
                                (Upon Approval)
                                          v
                         [Simulated Procurement MCP Tool]
                         Executes PO; Idempotent via Postgres
```

### Specialist Subagents Table

| Subagent Name | Role Description | Bound Tools |
|---|---|---|
| `triage_subagent` | Extracts entities, delay, and budget cap; detects ambiguity | Entity dictionary lookups, parser tools |
| `impact_subagent` | Evaluates physical vs usable inventory, BOMs, and factory lines | `query_inventory`, `query_bom`, `query_production_schedules` |
| `contract_subagent` | Audits supplier qualifications, ISO validity, and delivery terms | `retrieve_documents`, `verify_certifications` |
| `graph_subagent` | Traverses Neo4j multi-tier supplier and customer networks | `query_supplier_graph`, `check_tier2_dependencies` |
| `optimizer_subagent` | Develops recovery strategies and calculates costs deterministically | `calculate_recovery_costs`, `calculate_revenue_at_risk` |
| `challenger_subagent`| Critiques plan, checks budget limits, neutralizes malicious prompts | `verify_budget_limits`, `scan_prompt_injections` |

---

## 4. Tool Signatures & Interfaces

All tools invoked by the Deep Agents harness:

```python
def query_inventory(component_id: str, factory_id: Optional[str] = None) -> OperationalImpact:
    """Query inventory records across all warehouses, splitting physical, reserved, and quarantined units."""
    ...

def query_bom(component_id: str) -> List[Dict[str, Any]]:
    """Inspect product bills of materials containing the component, affected factory lines, and customer orders."""
    ...

def query_supplier_graph(component_id: str, max_depth: int = 2) -> Dict[str, Any]:
    """Execute Cypher on Neo4j to retrieve suppliers, capacities, lead times, and upstream tier-2 manufacturers."""
    ...

def retrieve_documents(query: str, access_scope: AccessScope = AccessScope.PROCUREMENT, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant contract and notice chunks enforcing provenance and RBAC access filtering."""
    ...

def calculate_recovery_costs(
    strategy_type: ActionType,
    units: int,
    unit_price: float,
    freight_cost: float,
    penalty_rebate: float = 0.0
) -> Dict[str, float]:
    """Deterministic business tool calculating recovery cost and revenue at risk. LLM math is forbidden."""
    ...

def execute_procurement_po(payload: ApprovalPayload) -> Dict[str, Any]:
    """Execute purchase order in the simulated procurement system via MCP with strict idempotency."""
    ...
```

---

## 5. Decision & Rejection Precedence Matrix

The system must handle the deliberate complications in the reference scenario:

| Candidate Option | Finding / Complication | Decision | Reason / Evidence |
|---|---|---|---|
| **Supplier Helios (S003)** | Lead time is 18 days (delay is 12 days) | **REJECTED** | Too slow to prevent stockout at Katowice factory. |
| **Supplier Borealis (S002)** | ISO 9001 / quality certification expired | **REJECTED** | Commercially viable, but operationally unacceptable per quality policy. |
| **Supplier Delta (S004)** | Shares upstream silicon fab with Atlas (S001) | **REJECTED** | Tier-2 concentration risk; subject to the same upstream bottleneck. |
| **Internal Stock Transfer** | 3,200 usable units available in warehouse B | **ACCEPTED (Partial)** | Low cost; covers immediate Katowice assembly line startup. |
| **Supplier Epsilon (S005)** | Fast lead time (4 days), certified, independent | **ACCEPTED (Primary)** | Complies with €75,000 spend cap (~€30,000 total); protects VIP customers. |
| **Planted Malicious Document** | Retrieved document contains prompt injection | **NEUTRALIZED** | Challenger subagent reports and isolates content; agent ignores injection. |

---

## 6. Team Sign-off Matrix (Day 1 Contracts)

| Role | Representative | Focus Area | Status | Date |
|---|---|---|---|---|
| **Platform** | @vaggelismpomponis | Docker, ChromaDB, MCP boundaries & Compose seed | **Signed-off** | 2026-11-24 |
| **Workflow** | @VickyMil-ai | Deep Agents harness, Subagents, Planning & Calculators | **Signed-off** | 2026-11-24 |
| **Interface** | @AlexZarkalis | Chainlit RBAC, Telemetry, Strategy Matrix & Approval Card | **Signed-off** | 2026-11-24 |
| **Knowledge** | @stef-fot | Data schema, Neo4j multi-tier graph, pgvector & ChromaDB | **Signed-off** | 2026-11-24 |
| **Quality** | @VickyMil-ai | 105 eval cases, retrieval benchmark, red-team & rehearsals | **Signed-off** | 2026-11-24 |

---

## 7. Interface & Chainlit UI Contracts (Issues #41–#53)

### 7.1 Session & `thread_id` Binding Contract
- **1:1 Deterministic Mapping**: On chat initialization (`@cl.on_chat_start`), `cl.context.session.id` is bound directly to LangGraph / Deep Agents `thread_id` (`cl.user_session.set("thread_id", session_id)`).
- **Restart & Manual Recovery**:
  - Automatic checkpoint inspection via `_restore_or_greet(thread_id)` restores any interrupted clarification or pending `ApprovalPayload` upon browser reload or container restart (`docker compose restart app`).
  - Explicit session recovery via `/resume <thread_id>` or conversational follow-up (*"Resume the case I was reviewing yesterday"*).

### 7.2 Role-Based Access Control (RBAC) & Scoped Retrieval Contract
Users are authenticated and mapped against `src/support-data/config/users.csv`:

| Role Key | User (`users.csv`) | `AccessScope` | Allowed `document_scopes` | Approval Authority |
|---|---|---|---|---|
| `procurement_manager` | Maria Keller (`u-pm-01`) | `procurement` | `public`, `internal`, `procurement` | Up to `€75,000` spending cap |
| `finance_controller` | Paul Novak (`u-fc-01`) | `finance` | `public`, `internal`, `procurement`, `finance-confidential` | Up to `€90,000` (with Finance Director cap) + `DOC-FIN-01-v1` access |
| `viewer` | Read Only Guest (`u-ro-01`) | `public` | `public` | Read-only (cannot approve, reject, or modify POs) |
| `operations_analyst` | Jon Weber (`u-an-01`) | `procurement` | `public`, `internal`, `procurement` | Factory F1 operational analysis & standard approval |
| `incident_coordinator`| Ines Duarte (`u-ic-01`) | `procurement` | `public`, `internal`, `procurement` | Factory F2/F3 coordination & standard approval |

### 7.3 Subagent Telemetry Step Event Contract
Each Deep Agent subagent emits a live `cl.Step` progress indicator in the Chainlit UI:
1. `triage_subagent`: Entity extraction (`supplier_id`, `component_id`, `delay_days`, `spending_cap`) and ambiguity detection.
2. `impact_subagent`: Warehouse stock breakdown (`on_hand`, `reserved`, `quarantined`, `usable`), factory cover timelines, BOM & customer order exposure.
3. `contract_subagent`: Scoped documentary evidence retrieval with provenance (`source_id`, `version`, `effective_date`, `access_scope`), source-precedence conflict resolution, and ISO certification validation.
4. `graph_subagent`: Multi-tier dependency traversal (detecting shared Tier-2 upstream manufacturer `U01 Veltro Semiconductor` between `S001 Atlas` and `S005 Delta`).
5. `optimizer_subagent`: Deterministic comparison of recovery strategies (`A`–`E`), separating **Recovery Cost (€)** from **Revenue at Risk (€)**.
6. `challenger_subagent`: Policy guardrail check, spending cap verification (`<= €75,000`), and adversarial prompt-injection neutralization (`DOC-NOT-HELIOS-PRICE`).

### 7.4 Payload-Bound Approval Card & Modify Plan Contract
- Every approval card binds to an immutable `ApprovalPayload` identified by `action_id` and a SHA-256 `payload_hash` computed over `(case_id, action_type, target_supplier_id, component_id, quantity, unit_price, total_cost, spending_cap)`.
- Interactive buttons: **✅ Approve**, **❌ Reject**, **✏️ Modify Plan**, guarded by per-action `asyncio.Lock` and immediate action removal to prevent double-click execution.
- Any modification via **✏️ Modify Plan** or chat command invalidates the prior `action_id` and `payload_hash`, revalidates supplier certification, monthly capacity, and spending cap constraints, and requires a fresh approval cycle.

### 7.5 Post-Approval Procurement Receipt & Report Export Contract
- Approved actions execute idempotently in the simulated procurement system (`idempotency_key = "{case_id}:{action_id}"`) and emit a structured **Procurement Execution Receipt**.
- An **Incident Report** is generated in both **Markdown (`.md`)** and **PDF (`.pdf`)** formats and attached to the Chainlit conversation via `cl.File` elements, while an approved resolution summary is persisted to case memory for future cases and multi-turn follow-up Q&A.
