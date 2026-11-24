# Role: Workflow – SupplyGuard AI

**Ευθύνη:** Ορχήστρωση μέσω Deep Agents (`deepagents`), dynamic planning middleware, context scratchpad, 6 εξειδικευμένοι subagents, deterministic business calculation tools, human approval gate, idempotent procurement execution (`pending → approved → executed`) και container restart persistence.  
**Παραδοτέο:** Πλήρης, αξιόπιστος Deep Agent μηχανισμός έρευνας περιστατικών διακοπής εφοδιασμού με αυστηρό ανθρώπινο έλεγχο.  
**Scopes commit:** `agent`, `approval`, `tools`.  
**Branches:** `feature/deepagents-skeleton`, `feature/subagents-delegation`, `feature/deterministic-calculators`, `feature/approval-gate-idempotency`, κλπ.

## Αρχή
Ο ρόλος Workflow αντικαθιστά την άκαμπτη καλωδίωση του LangGraph StateGraph με το **Deep Agents harness** (`create_deep_agent`). Αντί για απλούς κόμβους, ο Root Deep Agent χρησιμοποιεί dynamic planner για να αποδομεί το πρόβλημα, κρατάει σημειώσεις σε εξωτερικό scratchpad memory (αποτρέποντας το context drift), αναθέτει εξειδικευμένες έρευνες σε subagents, χρησιμοποιεί ντετερμινιστικά εργαλεία για αριθμητικούς υπολογισμούς (αποτρέποντας hallucinations σε κόστη), και διακόπτει τη ροή για αυστηρή ανθρώπινη έγκριση πριν εκτελέσει οποιαδήποτε ενέργεια προμήθειας.

## Βήματα

### Φάση 1 – Kick-off & Contracts (Εβδ. 1, Ημ. 1–2)
1. Συμμετοχή στα contracts (`docs/ARCHITECTURE_CONTRACTS.md`): Pydantic schemas (`IncidentCase`, `OperationalImpact`, `RecoveryOption`, `ApprovalPayload`), tool signatures, lifecycle states (`pending`, `approved`, `executed`, `rejected`). ✋ με όλους.
2. Ορισμός υπογραφών tools με Knowledge (`query_inventory`, `query_bom`, `query_supplier_graph`, `retrieve_documents`, `retrieve_incident_memories`). ✋ με Knowledge.

### Φάση 2 – Deep Agents Harness & Subagents Skeleton (Ημ. 2–4)
3. Αρχικοποίηση του Root Deep Agent (`create_deep_agent`) με:
   - Dynamic Planning Middleware (δημιουργία, ενημέρωση και εκτέλεση πλάνου βήμα-προς-βήμα).
   - Context Scratchpad (εικονικό σύστημα αρχείων/μνήμης για διατήρηση ενδιάμεσων αναλύσεων BOM και αποθεμάτων).
   - PostgreSQL Checkpointer integration για persistence κατάστασης και threads. ✋ με Platform.
4. Υλοποίηση των 6 εξειδικευμένων Subagents:
   - **Triage Subagent:** Εξάγει S001 (Atlas Components), MC-17, 12-day delay, spending cap €75k. Αν το όνομα είναι ασαφές (π.χ. "Atlas"), ενεργοποιεί διευκρίνιση χωρίς να μαντεύει.
   - **Operational Impact Subagent:** Ελέγχει φυσικά αποθέματα, απομονώνει δεσμευμένα και σε καραντίνα lots, υπολογίζει αντίκτυπο σε Katowice & Lyon και ακάλυπτη ζήτηση (5,350 units).
   - **Contract & Provenance Subagent:** Αναλύει συμβόλαια, ρήτρες καθυστέρησης, πιστοποιήσεις ποιότητας (εντοπίζει ληγμένη πιστοποίηση Borealis).
   - **Supply Graph Subagent:** Εκτελεί Cypher ερωτήματα στο Neo4j και ανακαλύπτει ότι ο εναλλακτικός προμηθευτής Delta μοιράζεται tier-2 upstream κατασκευαστή με την Atlas.
   - **Strategy Optimizer Subagent:** Διαμορφώνει εναλλακτικές (Transfer, Expedite, Alternate supplier, Reallocate, Reschedule).
   - **Adversarial Challenger Subagent:** Ελέγχει την πρόταση για παραβιάσεις πολιτικής, αδύναμες παραδοχές και εξουδετερώνει τυχόν prompt injections από ανακτηθέντα έγγραφα.
5. End-to-end ροή του reference incident με mock tools. ✋ με Interface και Quality.

### Φάση 3 – Ντετερμινιστικά Εργαλεία Υπολογισμών (Ημ. 4–6)
6. Υλοποίηση **Deterministic Business Calculators** ως Python tools:
   - Υπολογισμός Revenue at Risk (ρήτρες παράδοσης, αξία παραγγελιών πελατών ανά βαθμίδα προτεραιότητας).
   - Υπολογισμός Recovery Cost (κόστος αερομεταφοράς/expedite, πρόσθετες χρεώσεις νέου προμηθευτή, κόστος μεταφοράς αποθέματος).
   - Απόλυτη απαγόρευση εκτέλεσης αριθμητικών πράξεων από το LLM (zero LLM math hallucinations).
7. Αντικατάσταση των mock tools με πραγματικά tools από το ρόλο Knowledge. ✋ με Knowledge.

### Φάση 4 – Human-in-the-Loop Approval & Idempotency (Ημ. 6–8)
8. **Human Approval Gate & Payload Binding:**
   - Αναστολή εκτέλεσης πριν από τη δημιουργία Purchase Order ή ενέργεια στο σύστημα προμηθειών.
   - Δημιουργία μοναδικού `action_id` και αποθήκευση στο PostgreSQL `audit_log` με status `pending`.
   - Το payload (προμηθευτής, ποσότητα, τιμή, όριο €75k) είναι κλειδωμένο. Αν ο χρήστης επιλέξει τροποποίηση, το state ακυρώνεται και επανυπολογίζεται νέο payload.
9. **Simulated Procurement Integration:**
   - Μετά από έγκριση (`approved`), κλήση του Simulated Procurement MCP tool.
   - Ενημέρωση κατάστασης σε `executed` με row-level locking (`SELECT ... FOR UPDATE`).
   - Αυστηρός pre-execution έλεγχος: καμία ενέργεια δεν εκτελείται δύο φορές (zero duplicate execution). ✋ με Platform.
10. **Container Restart Test:**
    - Προσομοίωση crash/restart του app container κατά την αναμονή έγκρισης.
    - Επιβεβαίωση απρόσκοπτης συνέχισης και διατήρησης της κατάστασης έγκρισης. ✋ με Platform και Quality.

### Φάση 5 – Incident Report, Memories & Follow-Up Tuning (Ημ. 8–10)
11. Δημιουργία δομημένου Incident Report (τεκμηρίωση, ευρήματα, λόγοι επιλογής, κόστος) και αποθήκευση της εγκεκριμένης περίληψης στις vector incident memories.
12. Υποστήριξη διαλόγου συνέχειας (follow-up Q&A) από τη μνήμη της υπόθεσης (π.χ. αύξηση budget σε €90k).
13. Διορθώσεις από τα evaluation runs και συμμετοχή στις πρόβες του live demo.

## Role checklist

- [ ] State schemas, action types και contracts συμφωνημένα
- [ ] Root Deep Agent (`create_deep_agent`) με dynamic planning middleware και scratchpad
- [ ] PostgreSQL checkpointer συνδεδεμένο για persistence
- [ ] 6 Subagents πλήρως υλοποιημένοι και διασυνδεδεμένοι
- [ ] Ντετερμινιστικά εργαλεία υπολογισμού Recovery Cost & Revenue at Risk
- [ ] Mocks αντικαταστάθηκαν με πραγματικά tools
- [ ] Απόρριψη Borealis (ληγμένη πιστοποίηση) & Delta (κοινός upstream κατασκευαστής)
- [ ] Human Approval interrupt με αυστηρό payload binding (spend cap ≤ €75k)
- [ ] Idempotent εκτέλεση στο Simulated Procurement MCP (zero duplicates)
- [ ] Restart test: ανθεκτικότητα σε container crashes χωρίς απώλεια κατάστασης
- [ ] Αποθήκευση approved incident memory και εξαγωγή Incident Report
- [ ] Multi-turn follow-up συνομιλία πλήρως λειτουργική
- [ ] Συμμετοχή στις πρόβες του live demo (≥2)
- [ ] Έχω commits και τουλάχιστον ένα review σε PR άλλου ρόλου
- [ ] Μπορώ να εξηγήσω ολόκληρη την αρχιτεκτονική των Deep Agents στο demo

## Backup
Ορίζεται στο `CONTRIBUTING_LOG.md`. Προτείνεται: Knowledge.
