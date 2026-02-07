# Adding Tools

## Step 3: Add Cypher Template Tools

**Tool 1: get_aircraft_overview**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
RETURN a.tail_number, a.model, a.operator,
       collect(DISTINCT s.name) AS systems,
       collect(DISTINCT {fault: m.fault, severity: m.severity})[0..10] AS events
```

**Tool 2: find_shared_faults**
```cypher
MATCH (a1:Aircraft {tail_number: $tail1})-[:HAS_SYSTEM]->()-[:HAS_COMPONENT]->()
      -[:HAS_EVENT]->(m1:MaintenanceEvent),
      (a2:Aircraft {tail_number: $tail2})-[:HAS_SYSTEM]->()-[:HAS_COMPONENT]->()
      -[:HAS_EVENT]->(m2:MaintenanceEvent)
WHERE m1.fault = m2.fault
RETURN collect(DISTINCT m1.fault) AS shared_faults
```

## Step 4: Add Text2Cypher

For flexible, ad-hoc queries about aircraft, flights, delays, and more.

---

[← Previous](08-lab-steps.md) | [Next: Testing Your Agent →](10-testing.md)
