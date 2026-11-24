# Role: Knowledge – SupplyGuard AI

**Ευθύνη:** Data engineering & ingestion του συνθετικού πακέτου `support-data/`, Neo4j multi-tier supply chain graph, pgvector & ChromaDB vector indexing, hybrid retrieval (Vector + BM25 + Graph), provenance metadata, ανίχνευση & επίλυση φυτεμένων προβλημάτων ποιότητας δεδομένων, και tool contracts.  
**Παραδοτέο:** Πλήρες σύστημα αποθήκευσης και ανάκτησης γνώσης με τεκμηριωμένη προέλευση (provenance) και εργαλεία για τους Deep Agents.  
**Scopes commit:** `db`, `neo4j`, `retrieval`, `policy`.  
**Branches:** `feature/supply-data-ingestion`, `feature/neo4j-multitier-graph`, `feature/chroma-indexing`, `feature/hybrid-retrieval-tool`, κλπ.

## Αρχή
Τα δεδομένα αποτελούν τον θεμέλιο λίθο της αξιοπιστίας του SupplyGuard AI. Ο ρόλος Knowledge φορτώνει ολόκληρο το συνθετικό επιχειρησιακό οικοσύστημα, συνδέει τα multi-tier dependencies στο Neo4j, ευρετηριάζει έγγραφα σε δύο διαφορετικά vector stores (`pgvector` και `ChromaDB`) για benchmark, και παρέχει ασφαλή εργαλεία ανάκτησης με αυστηρή διατήρηση προέλευσης (`source_id`, `version`/`effective_date`, `access_scope`).

## Βήματα

### Φάση 1 – Kick-off & Contracts (Εβδ. 1, Ημ. 1–2)
1. Συμμετοχή στα contracts (`docs/ARCHITECTURE_CONTRACTS.md`): Ορισμός schemas για επιχειρησιακές οντότητες και επιστρεφόμενα Pydantic models εργαλείων: `InventoryStatusResult`, `BOMResult`, `DocumentResult`, `SupplierGraphResult`. ✋ με Workflow.
2. Ανάλυση του συνθετικού πακέτου `support-data/` και καταγραφή των φυτεμένων προβλημάτων ποιότητας δεδομένων (conflicting dates, stale docs, duplicate messages).

### Φάση 2 – Επιχειρησιακή Βάση & Neo4j Multi-Tier Graph (Ημ. 2–4)
3. **Σχεδιασμός Σχεσιακού Σχήματος PostgreSQL:**
   - Δημιουργία πινάκων για: `suppliers` (60), `components` (300), `products` (80), `bom_lines` (616), `purchase_orders` (2,000), `shipment_updates` (1,100+), `supplier_messages` (190+), `inventory_lots` (1,000 εγγραφές με διακριτά πεδία `physical_quantity`, `reserved_quantity`, `quarantined_quantity`, `location`), `production_schedules` (12 εβδομάδες), `customer_orders` (1,500 παραγγελίες για 25 πελάτες).
4. **Neo4j Multi-Tier Supply Chain Graph Model:**
   - Κόμβοι: `Supplier`, `Component`, `Product`, `Factory`, `Customer`, `CustomerOrder`, `UpstreamManufacturer`.
   - Σχέσεις: `(:Supplier)-[:SUPPLIES {lead_time, capacity}]->(:Component)`, `(:Component)-[:PART_OF {quantity_per_unit}]->(:Product)`, `(:Product)-[:PRODUCED_AT]->(:Factory)`, `(:CustomerOrder)-[:REQUIRES]->(:Product)`, `(:Supplier)-[:DEPENDS_ON_UPSTREAM]->(:UpstreamManufacturer)`.
   - **Κρίσιμη σχέση:** Μοντελοποίηση της κοινής εξάρτησης Atlas (S001) και Delta (S004) από τον ίδιο upstream κατασκευαστή chip fab.
5. Ingestion scripts: Idempotent φόρτωση των CSV αρχείων του φακέλου `support-data/graph/` στο Neo4j.

### Φάση 3 – Multi-Vector Indexing & Hybrid Retrieval Pipeline (Ημ. 4–6)
6. **Chunking & Ευρετηρίαση Εγγράφων (212 documents):**
   - Κατάτμηση συμβολαίων, πιστοποιήσεων, διαδικασιών, επιστολών προμηθευτών και ιστορικών αναφορών.
   - Εμπλουτισμός κάθε chunk με metadata: `source_id`, `version`/`effective_date`, `access_scope` (`procurement`, `finance`, `public`), `document_type`.
   - Αποθήκευση στο **PostgreSQL `pgvector`** με HNSW index.
   - Παράλληλη αποθήκευση στο **ChromaDB** για τη διεξαγωγή του retrieval benchmark.
7. **Ευρετηρίαση Approved Incident Memories:**
   - Ευρετηρίαση 300 ιστορικών disruption cases και 40 approved incident memories σε ξεχωριστό collection/table για semantic search ανακτήσεων παρόμοιων περιστατικών.
8. **Υλοποίηση Hybrid Retrieval Tool:**
   - Συνδυασμός Dense Vector Search (cosine similarity) + BM25 Lexical Search + Graph contextual filtering.
   - Εφαρμογή δυναμικού φίλτρου `access_scope` με βάση το session role του χρήστη (αποτροπή διαρροής finance-confidential δεδομένων σε guest).

### Φάση 4 – Επίλυση Προβλημάτων Ποιότητας Δεδομένων & Integration (Ημ. 6–8)
9. Υλοποίηση κανόνων επίλυσης συγκρούσεων:
   - Όταν email και συμβόλαιο διαφωνούν για lead time ή τιμή, επισήμανση της αβεβαιότητας και ιεράρχηση βάσει ημερομηνίας ισχύος / επίσημης τροποποίησης (amendment).
   - Αναγνώριση ληγμένης πιστοποίησης (Borealis ISO expired) και επιστροφή operational warning.
10. Αυτοματοποίηση του πλήρους seeding script (`scripts/seed_supply_chain.py`) για ένταξη στο Compose `seed` service. ✋ με Platform.
11. Παροχή δεδομένων και ground truth στον ρόλο Quality για τα 105 evaluation cases. ✋ με Quality.

### Φάση 5 – Retrieval Benchmark & Demo Rehearsal (Ημ. 8–10)
12. Εκτέλεση benchmarks ανάκτησης σε συνεργασία με τον Quality: σύγκριση Recall@K, Precision@K, και χρόνου απόκρισης μεταξύ `pgvector`, `ChromaDB` και `Hybrid Retrieval`.
13. Συμμετοχή στις πρόβες του demo και επεξήγηση του Knowledge Graph και της προέλευσης τεκμηρίων (provenance).

## Role checklist

- [ ] Σχεσιακό σχήμα PostgreSQL για όλα τα operational datasets του `support-data/`
- [ ] Neo4j multi-tier graph model τεκμηριωμένο με upstream supplier dependencies
- [ ] Ingestion scripts για Neo4j CSVs πλήρως idempotent
- [ ] 212 έγγραφα κατατμημένα με `source_id`, `version`/`effective_date`, `access_scope`
- [ ] Αποθήκευση σε `pgvector` και `ChromaDB`
- [ ] Ευρετηρίαση 300 ιστορικών περιπτώσεων και 40 approved memories
- [ ] Υλοποίηση Hybrid Retrieval tool (Vector + BM25 + Graph)
- [ ] Δυναμικό filtering βάσει ρόλου χρήστη (`access_scope`)
- [ ] Κανόνες επίλυσης συγκρούσεων μεταξύ συμβολαίων και emails
- [ ] Εντοπισμός ληγμένων πιστοποιήσεων προμηθευτών
- [ ] Seeding script ενταγμένο στο Compose `seed` service
- [ ] Παροχή δεδομένων στον Quality για τα 105 evaluation cases
- [ ] Έχω commits και τουλάχιστον ένα review σε PR άλλου ρόλου
- [ ] Μπορώ να εξηγήσω ολόκληρη τη δομή των δεδομένων και της ανάκτησης στο demo

## Backup
Ορίζεται στο `CONTRIBUTING_LOG.md`. Προτείνεται: Platform.
