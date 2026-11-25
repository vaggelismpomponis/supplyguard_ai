// Copy graph/*.csv into the Neo4j import directory, then run this script.
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Supplier) REQUIRE n.supplierId IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Component) REQUIRE n.componentId IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Product) REQUIRE n.productId IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Factory) REQUIRE n.factoryId IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Customer) REQUIRE n.customerId IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Upstream) REQUIRE n.upstreamId IS UNIQUE;
LOAD CSV WITH HEADERS FROM 'file:///nodes_supplier.csv' AS r MERGE (n:Supplier {supplierId:r['supplierId:ID(Supplier)']}) SET n.name=r.name,n.country=r.country,n.erpStatus=r.erpStatus,n.certificationExpiry=date(r.certificationExpiry),n.sourceId=r.sourceId,n.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///nodes_upstream.csv' AS r MERGE (n:Upstream {upstreamId:r['upstreamId:ID(Upstream)']}) SET n.name=r.name,n.country=r.country,n.sourceId=r.sourceId,n.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///nodes_component.csv' AS r MERGE (n:Component {componentId:r['componentId:ID(Component)']}) SET n.description=r.description,n.sourceId=r.sourceId,n.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///nodes_product.csv' AS r MERGE (n:Product {productId:r['productId:ID(Product)']}) SET n.name=r.name,n.sourceId=r.sourceId,n.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///nodes_factory.csv' AS r MERGE (n:Factory {factoryId:r['factoryId:ID(Factory)']}) SET n.name=r.name,n.sourceId=r.sourceId,n.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///nodes_customer.csv' AS r MERGE (n:Customer {customerId:r['customerId:ID(Customer)']}) SET n.name=r.name,n.priorityTier=toInteger(r['priorityTier:int']),n.sourceId=r.sourceId,n.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///rel_supplies.csv' AS r MATCH (a:Supplier {supplierId:r[':START_ID(Supplier)']}),(b:Component {componentId:r[':END_ID(Component)']}) MERGE (a)-[x:SUPPLIES]->(b) SET x.leadTimeDays=toInteger(r['leadTimeDays:int']),x.unitPriceEur=toFloat(r['unitPriceEur:float']),x.sourceId=r.sourceId,x.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///rel_sources_from.csv' AS r MATCH (a:Supplier {supplierId:r[':START_ID(Supplier)']}),(b:Upstream {upstreamId:r[':END_ID(Upstream)']}) MERGE (a)-[x:SOURCES_FROM]->(b) SET x.sourceId=r.sourceId,x.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///rel_used_in.csv' AS r MATCH (a:Component {componentId:r[':START_ID(Component)']}),(b:Product {productId:r[':END_ID(Product)']}) MERGE (a)-[x:USED_IN]->(b) SET x.qtyPerUnit=toInteger(r['qtyPerUnit:int']),x.sourceId=r.sourceId,x.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///rel_produced_at.csv' AS r MATCH (a:Product {productId:r[':START_ID(Product)']}),(b:Factory {factoryId:r[':END_ID(Factory)']}) MERGE (a)-[x:PRODUCED_AT]->(b) SET x.sourceId=r.sourceId,x.effectiveDate=date(r.effectiveDate);
LOAD CSV WITH HEADERS FROM 'file:///rel_ordered_by.csv' AS r MATCH (a:Product {productId:r[':START_ID(Product)']}),(b:Customer {customerId:r[':END_ID(Customer)']}) MERGE (a)-[x:ORDERED_BY]->(b) SET x.openOrders=toInteger(r['openOrders:int']),x.sourceId=r.sourceId,x.effectiveDate=date(r.effectiveDate);
// Example - shared upstream risk for Atlas:
// MATCH (a:Supplier {supplierId:'S001'})-[:SOURCES_FROM]->(u)<-[:SOURCES_FROM]-(o:Supplier) RETURN o.name, u.name;
