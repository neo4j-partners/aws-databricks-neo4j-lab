# Lab 5: Sample Cypher Queries

Copy and paste these queries into the [Neo4j Aura Query interface](https://console.neo4j.io) to explore the Aircraft Digital Twin graph.

## Cypher Concepts Used

| Concept | What It Does |
|---|---|
| `MATCH (n:Label)` | Find nodes by label — the starting point for most queries |
| `(a)-[:REL]->(b)` | Traverse a relationship between two nodes (direction matters) |
| `{key: 'value'}` | Inline property filter — shorthand for `WHERE n.key = 'value'` |
| `WHERE` | Filter results by condition after a `MATCH` |
| `OPTIONAL MATCH` | Like a SQL LEFT JOIN — keeps the row even if the pattern has no match |
| `RETURN ... AS alias` | Project properties and rename columns |
| `count()`, `avg()` | Aggregate functions — work like their SQL equivalents |
| `collect()` | Aggregate values into a list (one row per group) |
| `DISTINCT` | De-duplicate values, usable inside `collect(DISTINCT x)` |
| `ORDER BY ... DESC` | Sort results (ascending by default) |
| `LIMIT n` | Cap the number of returned rows |
| `CALL db.schema.visualization()` | Built-in procedure that returns the graph's node labels, relationship types, and properties |
| Multi-hop patterns | Chain relationships in a single `MATCH` to traverse several hops at once, e.g. `(a)-[:R1]->(b)-[:R2]->(c)` |

---

## Aircraft Topology

### See one aircraft's complete hierarchy

```sql
MATCH (a:Aircraft {tail_number: 'N95040A'})-[r1:HAS_SYSTEM]->(s:System)-[r2:HAS_COMPONENT]->(c:Component)
RETURN a, r1, s, r2, c
```

> **Concepts**: multi-hop pattern, inline property filter, returning full nodes and relationships (renders as a graph visualization in Neo4j Browser).

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

> **Concepts**: `OPTIONAL MATCH` keeps systems that have no components, `collect()` groups component names into a list per system, `WHERE ... IS NOT NULL` filters out incomplete data.

### Compare aircraft by operator

```sql
MATCH (a:Aircraft)
RETURN a.operator AS Operator, count(a) AS Count
```

> **Concepts**: `count()` aggregation with implicit grouping — non-aggregated columns (`Operator`) become the group key, just like SQL `GROUP BY`.

### Fleet by manufacturer

```sql
MATCH (a:Aircraft)
RETURN a.manufacturer AS Manufacturer,
       count(a) AS AircraftCount,
       collect(DISTINCT a.model) AS Models
ORDER BY AircraftCount DESC
```

> **Concepts**: `collect(DISTINCT ...)` builds a de-duplicated list of models per manufacturer.

---

## Components and Systems

### Component distribution

```sql
MATCH (c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC
```

> **Concepts**: simple label scan with aggregation — counts how many components exist of each type.

### Find all engine components

```sql
MATCH (s:System {type: 'Engine'})-[:HAS_COMPONENT]->(c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC
```

> **Concepts**: inline property filter `{type: 'Engine'}` narrows the match before traversing the relationship.

---

## Schema

### View the complete graph schema

```sql
CALL db.schema.visualization()
```

> **Concepts**: `CALL` invokes a built-in procedure. This one introspects the database and returns every node label, relationship type, and how they connect — useful for orienting yourself in an unfamiliar graph.

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

> **Concepts**: four-hop pattern traverses Aircraft → System → Component → MaintenanceEvent in one query. `LIMIT 10` caps the output, and `ORDER BY ... DESC` puts the most recent events first.

---

## Flights and Delays

### Analyze flight delays by cause

```sql
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN d.cause, count(*) AS count, avg(d.minutes) AS avg_minutes
ORDER BY count DESC
```

> **Concepts**: `count(*)` counts matched rows (not a specific node), `avg()` computes the mean — both are grouped by `d.cause`.

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

> **Concepts**: three-hop pattern linking aircraft to their removed components. `r.tsn` (time since new) and `r.csn` (cycles since new) are domain properties on the Removal node.
