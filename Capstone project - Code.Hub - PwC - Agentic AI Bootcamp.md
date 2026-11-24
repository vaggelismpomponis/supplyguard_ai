[Logo PwC] 



<!-- Start of picture text -->
a= Code.Hub<br><!-- End of picture text -->

**<mark>P R O J E C T A S S I G N M E N T</mark>** 

**SupplyGuard AI** An Agentic Supply Chain Disruption and Recovery Platform 

**Capstone Project · Agentic AI Bootcamp** 

Code.Hub × PwC 

October 2026 

**SUPPLYGUARD AI  ·  PROJECT ASSIGNMENT** 



#### **A B S T R A C T** 

## The challenge is to build a system that investigates a supply chain disruption, determines its business impact, compares recovery strategies, and prepares an evidence-backed action plan for human approval. 

This is an end-to-end engineering project: participants must build the application, implement multiple agent patterns, integrate several retrieval approaches, and demonstrate that the system behaves reliably under failure and attack. 

_All company details and financial figures below are fictional project assumptions._ 

**3 60 €75k 12 days** F A C T O R I E S S U P P L I E R S S P E N D I N G C A P M C - 1 7 D E L A Y 

# **01  The business case** 

A European manufacturer operates three factories and purchases components from 60 suppliers. Its procurement, production, logistics, and finance teams work with disconnected systems: 

- Supplier contracts and qualification documents. 

- Purchase orders, inventory records, and production schedules. 

- Product bills of materials. 

- Shipment updates and supplier communications. 

- Internal procedures and historical incident reports. 

When a supplier announces a delay, employees manually investigate which products and customer orders are affected. They must then identify alternatives, check contractual restrictions, estimate costs, and coordinate approval. 

An apparently simple replacement can introduce further problems. An alternative supplier might have insufficient capacity, an expired certification, or the same upstream dependency as the original supplier. 

**B U S I N E S S G O A L** 

**The company wants to reduce the time needed to produce a defensible recovery recommendation while retaining human control over purchasing and operational decisions.** 

The project team is commissioned to develop **SupplyGuard AI** , an assistant used by procurement managers, operations analysts, and incident coordinators. 

Code.Hub × PwC  ·  Agentic AI Bootcamp  ·  October 2026 **2** 

**SUPPLYGUARD AI  ·  PROJECT ASSIGNMENT** 



# **02  The incident that drives the project** 

The final demonstration begins with this message: 

**I N C O M I N G M E S S A G E · P R O C U R E M E N T M A N A G E R** 

_“Supplier Atlas Components has announced a 12-day delay for component MC-17. Determine which customer commitments are at risk, investigate alternative sources, and recommend a recovery plan. Additional spending must not exceed €75,000. Do not create a purchase order without approval.”_ 

The available evidence and runtime conditions contain complications: 

|**COMPLICATION**|**WHY IT MATTERS**|
|---|---|
|**Inventory exists in several locations**|A transfer could be preferable to a new purchase.|
|**MC-17 appears in several product bills of**<br>**materials**|The system must trace indirect business impact.|
|**Some inventory is reserved or quarantined**|Physical stock is not necessarily usable stock.|
|**Alternative suppliers have different lead times**<br>**and capacities**|The cheapest supplier might not prevent disruption.|
|**Two suppliers share an upstream manufacturer**|Apparent diversification may not reduce risk.|
|**A supplier certification has expired**|A feasible commercial option may be operationally<br>unacceptable.|
|**Contracts and emails contain conflicting**<br>**information**|The system must identify uncertainty and source precedence.|
|**One document contains malicious instructions**|Retrieved content must not gain authority over the agent.|
|**The application restarts while approval is pending**|The investigation must resume without duplicating actions.|



The system must produce a recommendation that survives all these conditions. 

# **03  What the business user should experience** 

A procurement manager opens the graphical user interface and describes the disruption. The application should: 

**Create an incident case** , extract structured facts, and request clarification where essential **01** information is missing. 

**Investigate operational impact** , including stock availability, affected products, production **02** commitments, and customer orders. 

**Collect documentary evidence** , from contracts, qualification records, procedures, supplier notices, **03** e-mails, and previous incidents. 

Code.Hub × PwC  ·  Agentic AI Bootcamp  ·  October 2026 **3** 

**SUPPLYGUARD AI  ·  PROJECT ASSIGNMENT** 



**04 Investigate dependencies** , across suppliers, components, factories, and customers. 

|**05**|**Develop recovery options**, such as inventory transfers, expedited delivery, alternate sourcing,<br>reallocation across customer orders, or revised production schedules.|
|---|---|
|**06**|**Calculate trade-offs**, using deterministic business tools.|
|**07**|**Challenge the proposed recommendation**, for missing evidence, policy violations, and weak<br>assumptions.|
|**08**|**Present an approval request**, containing the exact proposed action, quantities, costs, and<br>supporting evidence.|
|**09**|**Execute an approved action in a simulated procurement system**, and record its outcome.|
|**10**|**Produce an incident report**, and retain an approved resolution summary for future cases.|



The user must also be able to ask follow-up questions: 

**“** _What changes if we increase the spending limit_ **“** _Why did you reject Supplier Helios? to €90,000?_ **“** _Can we protect our highest-priority customers_ **“** _Resume the case I was reviewing yesterday. using existing stock?_ 

# **04  How the end user will use the final application** 

The finished application is used entirely through a chat window; the user needs no knowledge of the technology behind it. A typical session with the provided data runs as follows: 

|**WHAT THE USER DOES**|**WHAT THE APPLICATION DOES AND SHOWS**|
|---|---|
|**1 · Signs in and opens a case**|The Chainlit chat opens. The user’s role decides which documents can be retrieved: a<br>procurement manager sees procurement documents, a finance controller also sees<br>finance-confidential data, a read-only guest sees public documents only.|
||The app creates an incident case and shows its progress. It extracts supplier S001|
|**2 · Types the incident**<br>**message**|(Atlas Components), component MC-17 and the 12-day delay. If the message is<br>ambiguous, for example only “Atlas”, it asks which supplier is meant instead of<br>guessing.|
|**3 · Follows the investigation**|Findings appear with their sources: 3,200 of 5,200 MC-17 units are usable (1,400<br>reserved, 600 quarantined); six products and 77 open customer orders are affected;<br>Katowice and Lyon run out first; 5,350 units of demand would go uncovered.<br>Conflicts between contracts, notices and e-mails are flagged, and the malicious<br>document is reported and ignored.|



Code.Hub × PwC  ·  Agentic AI Bootcamp  ·  October 2026 **4** 

**SUPPLYGUARD AI  ·  PROJECT ASSIGNMENT** 



|**WHAT THE USER DOES**|**WHAT THE APPLICATION DOES AND SHOWS**|
|---|---|
|**4 · Reads the options**|A comparison of the recovery strategies with costs and reasons: Helios is too slow,<br>Borealis is blocked by an expired certificate, Delta shares its upstream manufacturer<br>with Atlas. Revenue at risk is shown separately from recovery cost.|
|**5 · Reviews and decides**|An approval request shows the exact supplier, quantities, prices, total cost (about<br>€30,000 for the reference plan, under the €75,000 limit) and the supporting<br>evidence. The user can approve, reject or change it; any change triggers revalidation<br>and a new approval. No purchase order exists before approval.|
|**6 · Receives the outcome**|After approval the actions run in the simulated procurement system and the<br>outcome is recorded. The app produces an incident report and stores an approved<br>summary for future cases.|
|**7 · Asks follow-up questions**|Answers come from the saved case: why options were rejected, what changes with a<br>€90,000 limit, whether top-priority customers can be protected with existing stock. A<br>case can be closed and resumed the next day, even after an application restart,<br>without repeating any action.|



**U S E R C O N T R O L** The application recommends and explains; **people approve** . Every number can be traced to a source, and every action can be audited. 

# **05  Required architecture** 

Each technology must have a defined responsibility. 

|**COMPONENT**|**RESPONSIBILITY**|
|---|---|
|**Chainlit**|Conversational interface, progress updates, evidence display, and approval<br>interactions.|
|**Application service layer**|User identity, case access, business operations, and integration boundaries.|
|**LangGraph**|Main incident lifecycle, routing, persistent execution, interrupts, and recovery.|
|**LangChain Core**|Prompts, messages, model interfaces, tools, structured output, and reusable<br>chains.|
|**Language model access**|A hosted or locally served LLM, accessed only through LangChain model interfaces.<br>The model is configurable, and every call is traced.|
|**create_agent**|A bounded specialist agent, such as contract analysis.|
|**Deep Agents**|Extended investigation involving planning, files, skills, sandboxed analysis, and<br>delegated subtasks.|
|**PostgreSQL**|Operational records, approval records, audit events, checkpoints, and persistent<br>stores.|
|**pgvector**|Baseline document retrieval and semantic search over approved incident<br>memories, in separate collections or tables.|



Code.Hub × PwC  ·  Agentic AI Bootcamp  ·  October 2026 **5** 

**SUPPLYGUARD AI  ·  PROJECT ASSIGNMENT** 



|**COMPONENT**|**RESPONSIBILITY**|
|---|---|
|**ChromaDB**|An alternative document vector index used in retrieval experiments and the hybrid<br>retrieval path.|
|**Neo4j**|Supplier, component, product, factory, and customer dependency graph.|
|**MCP integrations**|Access to procurement operations and an independently deployed external<br>information service.|
|**LangSmith**|Tracing, run inspection, evaluation datasets, and experiment comparison.|



# **06  Provided data package** 

All data is synthetic and is provided in the support-data folder. Teams do not generate or modify it: they load, 

index and reason over it. 

|**DATASET**|**PROVIDED IN SUPPORT -DATA**|
|---|---|
|Suppliers, including qualification status and capacity|**60 suppliers**|
|Components and product bills of materials|**300 components · 80 products · 616 BOM lines**|
|Purchase orders and delivery records|**2,000 purchase orders**|
|Shipment updates and supplier messages|**1,100+ updates · 190+ messages**|
|Inventory records across factories and warehouses|**1,000 records, with reservations and quarantine**<br>**lots**|
|Production schedules|**12 weeks · all products**|
|Customer orders and priorities|**1,500 orders · 25 customers**|
|Contracts, procedures, certifications, supplier notices, e-mails,<br>and incident reports|**212 documents with provenance (documents/)**|
|Historical disruption cases and approved incident memories|**300 cases · 40 memories**|
|Supplier, component, product, factory, and customer graph|**Neo4j CSV files and load script (graph/)**|
|Held-out evaluation cases and the MC-17 reference scenario|**105 cases (evaluation/)**|
|Policies, users and roles, external risk feed|**config/ · external_service/**|



The data already contains deliberate data-quality problems: ambiguous supplier names, missing identifiers, duplicate messages, stale documents, conflicting dates, and disconnected graph entities. Teams must detect and handle them; a manifest of the planted problems is provided for testing. 

**P R O V E N A N C E** 

Every document carries a **source identifier** , **version or effective date** , and **access scope** . Graph relationships carry a source and an effective date. Generated claims must preserve provenance. 

Code.Hub × PwC  ·  Agentic AI Bootcamp  ·  October 2026 **6** 

**SUPPLYGUARD AI  ·  PROJECT ASSIGNMENT** 



# **07  Decision requirements** 

The system must compare at least three of the following recovery strategies, where feasible: 

|**A**|**B**|**C**|**D**|**E**|
|---|---|---|---|---|
|**Transfer available**|**Expedite an existing**|**Purchase from an**|**Reallocate limited**|**Reschedule**|
|**inventory**|**order**|**approved alternative**|**components across**|**production**|
||||**customer orders**||



Report projected **revenue at risk** separately from **recovery cost** . Revenue exposure is not automatically an expected loss, and penalties must not be counted twice. 

**A P P R O V A L R U L E** 

Human approval must bind to the **specific payload** . If supplier, quantity, price, or relevant conditions change, the system must revalidate and obtain approval again. 

Code.Hub × PwC  ·  Agentic AI Bootcamp  ·  October 2026 **7** 

**SUPPLYGUARD AI  ·  PROJECT ASSIGNMENT** 



# **08  Deliverables and assessment** 

### The team submits: 

- A reproducible repository, configuration template, Docker-based services, and startup instructions. 

- The working Chainlit application and simulated procurement integration. 

- Ingestion, indexing, and graph-loading scripts for the provided data package. 

- Automated tests, results on the provided evaluation cases, retrieval benchmark results (pgvector, ChromaDB, and hybrid), and red-team findings. 

- An architecture explanation, sample incident report, and business-value assessment. 

- A live demonstration and a short discussion of limitations. 

#### **S U G G E S T E D G R A D I N G** 

|**AREA**|**WEIGHT**|
|---|---|
|Business reasoning and numerical correctness|**25%**|
|Agent orchestration, memory, and recovery|**25%**|
|Retrieval, knowledge graph, and evidence quality|**20%**|
|Guardrails, authorization, and adversarial resilience|**15%**|
|Engineering quality, evaluation, and reproducibility|**10%**|
|Final demonstration and communication|**5%**|
|**Total**|**100%**|



Code.Hub × PwC  ·  Agentic AI Bootcamp  ·  October 2026 **8** 

