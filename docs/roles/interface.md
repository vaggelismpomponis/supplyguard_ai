# Role: Interface – SupplyGuard AI

**Ευθύνη:** Chainlit UI: Role-Based Access Control (RBAC), Investigation Telemetry (Subagent steps), Operational Impact Dashboard, Recovery Strategy Comparison Matrix, Payload-Bound Approval Card, Post-Approval Outcome, Session Resume & Follow-Up Q&A.  
**Παραδοτέο:** Λειτουργικό, ασφαλές και πλούσιο UI βασισμένο στο Chainlit.  
**Scopes commit:** `ui`, `approval`.  
**Branches:** `feature/chainlit-rbac`, `feature/telemetry-steps`, `feature/strategy-comparison-ui`, `feature/approval-card-payload`, κλπ.

## Αρχή
Το UI καθοδηγεί τον επιχειρησιακό χρήστη (Procurement Manager, Finance Controller, Incident Coordinator). Παρουσιάζει με σαφήνεια τα ευρήματα της έρευνας, συγκρίνει τις στρατηγικές ανάκαμψης με διαχωρισμό του Recovery Cost από το Revenue at Risk, και επιβάλλει αυστηρό ανθρώπινο έλεγχο (Human Approval) πριν από οποιαδήποτε ενέργεια στο σύστημα προμηθειών.

## Βήματα

### Φάση 1 – Kick-off & Contracts (Εβδ. 1, Ημ. 1–2)
1. Συμμετοχή στα αρχιτεκτονικά συμβόλαια (`docs/ARCHITECTURE_CONTRACTS.md`): UI payloads, RBAC scopes, telemetry step events, approval card contract. ✋ με Workflow και Platform.
2. Ορισμός κανόνα σταθερής αντιστοίχισης `thread_id` ↔ Chainlit session id για απρόσκοπτο resume μετά από restart.

### Φάση 2 – RBAC & Investigation Telemetry (Ημ. 2–4)
3. Υλοποίηση **Role-Based Access Control (RBAC)** στην είσοδο του Chainlit:
   - *Procurement Manager*: Πρόσβαση σε standard έγγραφα, αναφορές προμηθευτών, S001 incident, κάρτες έγκρισης.
   - *Finance Controller*: Πρόσβαση σε όλα τα παραπάνω + εμπιστευτικά οικονομικά στοιχεία (περιθώρια κέρδους, ρήτρες, συμβατικές τιμές).
   - *Read-only Guest*: Προβολή μόνο δημόσιων ανακοινώσεων και υψηλού επιπέδου κατάστασης.
4. Telemetry Dashboard: Εμφάνιση live step indicators καθώς οι εξειδικευμένοι Deep Agent subagents εκτελούνται (Triage, Stock Check, Contract Analysis, Supply Graph Traversal, Trade-off Optimization). ✋ με Workflow.
5. Clarification interrupt: Όταν το εισερχόμενο αίτημα είναι ασαφές (π.χ. μόνο "Atlas"), το UI ζητά ευγενικά διευκρινίσεις χωρίς να μαντεύει.

### Φάση 3 – Operational Impact & Strategy Comparison (Ημ. 4–6)
6. Παρουσίαση επιχειρησιακού αντικτύπου με πηγές:
   - 3,200 από 5,200 μονάδες MC-17 είναι διαθέσιμες (1,400 δεσμευμένες, 600 σε καραντίνα).
   - 6 προϊόντα και 77 πελατειακές παραγγελίες επηρεάζονται.
   - Τα εργοστάσια Katowice και Lyon ξεμένουν πρώτα · 5,350 μονάδες ζήτησης μένουν ακάλυπτες.
   - Επισήμανση συγκρούσεων μεταξύ συμβολαίων και e-mails · αναφορά και αγνόηση του κακόβουλου εγγράφου (prompt injection).
7. **Recovery Strategy Comparison Matrix (Κάρτα σύγκρισης στρατηγικών):**
   - Σύγκριση τουλάχιστον 3 στρατηγικών (Transfer stock, Expedite order, Alternative supplier, Reallocate, Reschedule).
   - Αυστηρός διαχωρισμός **Recovery Cost** από το **Revenue at Risk**.
   - Σαφείς λόγοι απόρριψης: Helios πολύ αργός, Borealis αποκλεισμένος λόγω ληγμένης πιστοποίησης, Delta μοιράζεται tier-2 upstream προμηθευτή με Atlas.

### Φάση 4 – Human-in-the-Loop Approval & Resume Resilience (Ημ. 6–8)
8. **Payload-Bound Approval Card:**
   - Εμφάνιση ακριβούς payload: Προμηθευτής, ποσότητα PO, τιμή μονάδας, συνολικό κόστος (έλεγχος ορίου ≤ €75,000) και υποστηρικτικά τεκμήρια (citations).
   - Κουμπιά: **[Approve]**, **[Reject]**, **[Modify Plan]**.
   - Αποτροπή διπλού κλικ (`asyncio.Lock`) και αφαίρεση κουμπιών μετά το πάτημα.
   - Οποιαδήποτε αλλαγή από τον χρήστη (Modify Plan) ακυρώνει την πρόταση, ενεργοποιεί επανεπικύρωση από το Workflow και παράγει νέο approval payload. ✋ με Workflow.
9. **Container Restart Resume:**
   - Δοκιμή επανεκκίνησης του app container κατά την αναμονή έγκρισης.
   - Μετά το restart ή reload της σελίδας, το session ανακτάται άμεσα από τη βάση και η κάρτα έγκρισης παραμένει λειτουργική. ✋ με Workflow και Platform.
10. Εμφάνιση αποτελέσματος εκτέλεσης (receipt από το simulated procurement system) και δυνατότητα εξαγωγής Incident Report σε Markdown/PDF.

### Φάση 5 – Multi-Turn Follow-Ups & Demo Rehearsals (Ημ. 8–10)
11. Υποστήριξη follow-up ερωτήσεων επί της αποθηκευμένης υπόθεσης:
    - *"Τι αλλάζει αν αυξηθεί το spending limit στα €90,000;"*
    - *"Γιατί απορρίφθηκε ο προμηθευτής Helios;"*
    - *"Μπορούμε να προστατεύσουμε τους πελάτες ύψιστης προτεραιότητας με το υπάρχον απόθεμα;"*
12. Συμμετοχή στις πρόβες του live demo (παρουσίαση του UI flow, του clarification, του approval card και του container restart).

## Role checklist

- [ ] Συμφωνημένα contracts UI ↔ Deep Agents
- [ ] Chainlit RBAC authentication με 3 ρόλους (Procurement, Finance, Guest)
- [ ] Scoped retrieval φίλτρα συνδεδεμένα με το ενεργό session
- [ ] Live progress step telemetry ανά subagent
- [ ] Clarification dialogs για ελλιπή ή ασαφή στοιχεία
- [ ] Operational impact dashboard (διαθέσιμο vs δεσμευμένο/καραντίνα, ακάλυπτη ζήτηση)
- [ ] Strategy Comparison Matrix (διαχωρισμός Recovery Cost vs Revenue at Risk)
- [ ] Strict Approval Card με ακριβές payload και προστασία διπλού κλικ
- [ ] Restart resilience: απρόσκοπτο resume της αναμονής έγκρισης μετά από restart
- [ ] Post-approval receipt και εξαγωγή Incident Report
- [ ] Multi-turn follow-up συνομιλία από την αποθηκευμένη μνήμη της υπόθεσης
- [ ] Συμμετοχή στις πρόβες του live demo (≥2)
- [ ] Έχω commits και τουλάχιστον ένα review σε PR άλλου ρόλου
- [ ] Μπορώ να εξηγήσω ολόκληρη τη ροή του UI στο demo

## Backup
Ορίζεται στο `CONTRIBUTING_LOG.md`. Προτείνεται: Quality.
