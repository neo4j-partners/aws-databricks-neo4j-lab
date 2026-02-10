# Adding Tools

## Step 3: Add Cypher Template Tools

**Tool 1: get_aircraft_overview** — Aircraft info, systems, maintenance events
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
OPTIONAL MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)
RETURN a.tail_number, a.model, a.manufacturer,
       collect(DISTINCT s.name) AS systems, count(DISTINCT f) AS flights
```

**Tool 2: get_sensor_limits** — Operating limits from maintenance manuals
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})-[:HAS_SYSTEM]->(sys:System)
      -[:HAS_SENSOR]->(s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit)
RETURN sys.name AS system, s.type AS sensor_type,
       ol.name AS limit, ol.minValue AS min, ol.maxValue AS max
```

**Tool 3: find_shared_faults** — Faults two aircraft share

## Step 4: Add Text2Cypher + Similarity Search

- **Text2Cypher** for ad-hoc queries across the full graph
- **Similarity Search** over maintenance manual chunks (OpenAI embeddings)

---

[<- Previous](08-lab-steps.md) | [Next: Testing Your Agent ->](10-testing.md)
