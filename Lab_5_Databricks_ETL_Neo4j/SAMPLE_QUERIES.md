# Lab 5: Sample Cypher Queries

Copy and paste these queries into the [Neo4j Aura Query interface](https://console.neo4j.io) to explore the Aircraft Digital Twin graph.

---

## Aircraft Topology

### See one aircraft's complete hierarchy

```sql
MATCH (a:Aircraft {tail_number: 'N95040A'})-[r1:HAS_SYSTEM]->(s:System)-[r2:HAS_COMPONENT]->(c:Component)
RETURN a, r1, s, r2, c
```

### Aircraft hierarchy (tabular view)

```sql
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)
WHERE s.type IS NOT NULL AND s.name IS NOT NULL
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
RETURN a.tail_number AS Aircraft,
       a.model AS Model,
       s.name AS System,
       s.type AS SystemType,
       collect(c.name) AS Components
ORDER BY s.type, s.name
```

### Compare aircraft by operator

```sql
MATCH (a:Aircraft)
RETURN a.operator AS Operator, count(a) AS Count
```

### Fleet by manufacturer

```sql
MATCH (a:Aircraft)
RETURN a.manufacturer AS Manufacturer,
       count(a) AS AircraftCount,
       collect(DISTINCT a.model) AS Models
ORDER BY AircraftCount DESC
```

---

## Components and Systems

### Component distribution

```sql
MATCH (c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC
```

### Find all engine components

```sql
MATCH (s:System {type: 'Engine'})-[:HAS_COMPONENT]->(c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC
```

---

## Schema

### View the complete graph schema

```sql
CALL db.schema.visualization()
```

---

## Maintenance

### Find aircraft with critical maintenance issues

```sql
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
WHERE m.severity = 'CRITICAL' AND m.reported_at IS NOT NULL
RETURN a.tail_number, s.name, c.name, m.fault, m.reported_at
ORDER BY m.reported_at DESC
LIMIT 10
```

---

## Flights and Delays

### Analyze flight delays by cause

```sql
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN d.cause, count(*) AS count, avg(d.minutes) AS avg_minutes
ORDER BY count DESC
```

---

## Component Removals

### Find component removal history

```sql
MATCH (a:Aircraft)-[:HAS_REMOVAL]->(r:Removal)-[:REMOVED_COMPONENT]->(c:Component)
WHERE r.removal_date IS NOT NULL
RETURN a.tail_number, c.name, r.reason, r.removal_date, r.tsn, r.csn
ORDER BY r.removal_date DESC
LIMIT 20
```
