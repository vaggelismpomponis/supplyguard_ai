# 🛡️ SupplyGuard AI — User Guide
**Agentic Supply Chain Disruption & Recovery Platform | Code.Hub × PwC**

Welcome to **SupplyGuard AI**. SupplyGuard AI autonomously monitors supply chain disruption events, extracts incident entities, evaluates inventory buffers across multi-tier supplier graphs, compares recovery strategies, and submits payload-bound recovery purchase orders for human approval.

---

## 🎯 Key Capabilities
1. **Disruption Entity Triage & Clarification:**
   - Detects affected suppliers, disrupted components (e.g. `MC-17`), and announced delay windows.
   - If ambiguous (e.g. multiple suppliers share a name like "Atlas"), pauses and requests interactive clarification.
2. **Operational Impact Analysis:**
   - Evaluates physical inventory minus reserved and quarantined stock to calculate true usable inventory.
   - Traces Bill of Materials (BOM) to identify affected finished products, open customer orders, and affected assembly factories.
3. **Multi-tier Graph Investigation:**
   - Cypher graph traversal across Tier-1 suppliers and Tier-2 upstream wafer fabs (e.g., Veltro Semiconductor in Taiwan) to detect single points of failure.
4. **Deterministic Strategy Optimization:**
   - Compares >=3 viable recovery options (Transfer Stock, Expedite Orders, Purchase from Qualified Alternate Supplier).
   - Generates trade-off matrix: Recovery Cost vs Revenue at Risk.
5. **Payload-Bound Human-in-the-Loop Approval:**
   - Pauses before executing state-changing purchase orders in the simulated procurement system.
   - Bound to an immutable UUID action ID with double-click protection and container restart recovery.

---

## 📋 Quick Commands
- Enter any disruption notice in the chat (e.g. *"Atlas Components announced a 12-day delay on MC-17 microcontrollers"*).
- Review the generated Operational Impact & Strategy Comparison matrix.
- Click **✅ Approve & Execute** on the Approval Card to submit the recovery order to the procurement system.
