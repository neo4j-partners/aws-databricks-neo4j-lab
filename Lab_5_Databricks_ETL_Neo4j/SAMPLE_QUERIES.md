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
| `count()`, `avg()`, `sum()`, `min()`, `max()` | Aggregate functions — work like their SQL equivalents |
| `collect()` | Aggregate values into a list (one row per group) |
| `DISTINCT` | De-duplicate values, usable inside `collect(DISTINCT x)` |
| `ORDER BY ... DESC` | Sort results (ascending by default) |
| `LIMIT n` | Cap the number of returned rows |
| `WITH` | Pipe results from one query part to the next — like a SQL CTE |
| `CASE WHEN ... THEN ... ELSE ... END` | Conditional expression for computed columns |
| `size(list)` | Returns the number of elements in a list |
| `CALL db.schema.visualization()` | Built-in procedure that returns the graph's node labels, relationship types, and properties |
| Multi-hop patterns | Chain relationships in a single `MATCH` to traverse several hops at once, e.g. `(a)-[:R1]->(b)-[:R2]->(c)` |

---

## Schema

### View the complete graph schema

```sql
CALL db.schema.visualization()
```

> **Concepts**: `CALL` invokes a built-in procedure. This one introspects the database and returns every node label, relationship type, and how they connect — useful for orienting yourself in an unfamiliar graph.

### Count all nodes and relationships

```sql
MATCH (n)
RETURN labels(n)[0] AS Label, count(n) AS Count
ORDER BY Count DESC
```

> **Concepts**: `labels(n)` returns a list of labels on a node. `[0]` takes the first one. This gives a quick census of your entire graph.

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

### Aircraft detail card

```sql
MATCH (a:Aircraft {tail_number: 'N95040A'})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)
OPTIONAL MATCH (a)-[:HAS_REMOVAL]->(r:Removal)
RETURN a.tail_number AS TailNumber,
       a.model AS Model,
       a.manufacturer AS Manufacturer,
       a.operator AS Operator,
       count(DISTINCT s) AS Systems,
       count(DISTINCT f) AS Flights,
       count(DISTINCT r) AS Removals
```

> **Concepts**: multiple `OPTIONAL MATCH` clauses gather counts from different relationship types. `count(DISTINCT ...)` prevents double-counting caused by the cross-product of multiple patterns.

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

### System types and their component types

```sql
MATCH (s:System)-[:HAS_COMPONENT]->(c:Component)
RETURN s.type AS SystemType,
       collect(DISTINCT c.type) AS ComponentTypes,
       count(c) AS TotalComponents
ORDER BY TotalComponents DESC
```

> **Concepts**: groups by system type and collects the distinct component types found in each — a quick way to understand what parts belong where.

### Systems with the most components

```sql
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)
RETURN a.tail_number AS Aircraft,
       s.name AS System,
       s.type AS SystemType,
       count(c) AS ComponentCount
ORDER BY ComponentCount DESC
LIMIT 10
```

> **Concepts**: three-hop traversal with aggregation. Shows which specific system instances have the most parts.

---

## Sensors

### Sensor types and measurement units

```sql
MATCH (sn:Sensor)
RETURN sn.type AS SensorType,
       sn.unit AS Unit,
       count(sn) AS Count
ORDER BY Count DESC
```

> **Concepts**: basic aggregation over Sensor nodes — gives an overview of what's being measured across the fleet.

### Sensors on a specific aircraft

```sql
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)-[:HAS_SENSOR]->(sn:Sensor)
RETURN s.name AS System,
       s.type AS SystemType,
       sn.name AS Sensor,
       sn.type AS SensorType,
       sn.unit AS Unit
ORDER BY s.type, sn.type
```

> **Concepts**: three-hop pattern from aircraft through system to sensor. The tabular output shows every sensor installed on one aircraft, grouped by system.

### Systems by sensor density

```sql
MATCH (s:System)-[:HAS_SENSOR]->(sn:Sensor)
WITH s.type AS SystemType, count(sn) AS SensorCount
RETURN SystemType, SensorCount
ORDER BY SensorCount DESC
```

> **Concepts**: `WITH` pipes intermediate results forward — here it computes sensor counts per system type, then passes them to `RETURN` for sorting.

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

### Maintenance events by severity

```sql
MATCH (m:MaintenanceEvent)
RETURN m.severity AS Severity, count(m) AS Count
ORDER BY Count DESC
```

> **Concepts**: simple aggregation — quickly shows the distribution of event severities across the dataset.

### Most common faults

```sql
MATCH (m:MaintenanceEvent)
WHERE m.fault IS NOT NULL
RETURN m.fault AS Fault,
       m.severity AS Severity,
       count(m) AS Occurrences
ORDER BY Occurrences DESC
LIMIT 15
```

> **Concepts**: groups by fault description and severity to surface the most frequent problems in the fleet.

### Aircraft ranked by maintenance burden

```sql
MATCH (m:MaintenanceEvent)-[:AFFECTS_AIRCRAFT]->(a:Aircraft)
RETURN a.tail_number AS Aircraft,
       a.model AS Model,
       count(m) AS TotalEvents,
       count(CASE WHEN m.severity = 'CRITICAL' THEN 1 END) AS CriticalEvents
ORDER BY TotalEvents DESC
```

> **Concepts**: `CASE WHEN ... THEN 1 END` inside `count()` acts as a conditional count — only critical events increment the counter, while `NULL` (the implicit `ELSE`) is ignored by `count()`.

### Corrective actions for critical faults

```sql
MATCH (m:MaintenanceEvent)
WHERE m.severity = 'CRITICAL' AND m.corrective_action IS NOT NULL
RETURN m.fault AS Fault,
       m.corrective_action AS CorrectiveAction,
       m.reported_at AS ReportedAt
ORDER BY m.reported_at DESC
LIMIT 10
```

> **Concepts**: filters to critical events with recorded fixes — useful for understanding what remediation looks like for the worst problems.

### Which systems have the most maintenance events?

```sql
MATCH (m:MaintenanceEvent)-[:AFFECTS_SYSTEM]->(s:System)
RETURN s.type AS SystemType,
       count(m) AS Events,
       count(CASE WHEN m.severity = 'CRITICAL' THEN 1 END) AS Critical,
       count(CASE WHEN m.severity = 'WARNING' THEN 1 END) AS Warning
ORDER BY Events DESC
```

> **Concepts**: uses `AFFECTS_SYSTEM` to link events back to the system they impacted. Multiple `CASE` expressions in a single query compute severity breakdowns without needing subqueries.

---

## Flights and Delays

### Analyze flight delays by cause

```sql
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN d.cause AS Cause,
       count(*) AS Count,
       avg(d.minutes) AS AvgMinutes,
       max(d.minutes) AS MaxMinutes,
       sum(d.minutes) AS TotalMinutes
ORDER BY Count DESC
```

> **Concepts**: `count(*)` counts matched rows, `avg()` / `max()` / `sum()` compute statistics — all are grouped by `d.cause`.

### Flights by operator

```sql
MATCH (f:Flight)
RETURN f.operator AS Operator, count(f) AS FlightCount
ORDER BY FlightCount DESC
```

> **Concepts**: simple aggregation over flight nodes — shows fleet activity by airline.

### Flights for a specific aircraft

```sql
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:OPERATES_FLIGHT]->(f:Flight)
OPTIONAL MATCH (f)-[:DEPARTS_FROM]->(dep:Airport)
OPTIONAL MATCH (f)-[:ARRIVES_AT]->(arr:Airport)
RETURN f.flight_number AS Flight,
       dep.iata AS Origin,
       arr.iata AS Destination,
       f.scheduled_departure AS Departure,
       f.scheduled_arrival AS Arrival
ORDER BY f.scheduled_departure
```

> **Concepts**: combines `MATCH` and `OPTIONAL MATCH` to pull in origin/destination airports. Uses airport IATA codes for readability.

### Most delayed flights

```sql
MATCH (a:Aircraft)-[:OPERATES_FLIGHT]->(f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN a.tail_number AS Aircraft,
       f.flight_number AS Flight,
       d.cause AS DelayCause,
       d.minutes AS DelayMinutes
ORDER BY d.minutes DESC
LIMIT 10
```

> **Concepts**: three-hop pattern joining aircraft, flight, and delay. Sorting by delay minutes surfaces the worst disruptions.

### Aircraft with the most total delay

```sql
MATCH (a:Aircraft)-[:OPERATES_FLIGHT]->(f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN a.tail_number AS Aircraft,
       a.model AS Model,
       count(d) AS DelayCount,
       sum(d.minutes) AS TotalDelayMinutes
ORDER BY TotalDelayMinutes DESC
```

> **Concepts**: aggregates delays per aircraft using `sum()` — identifies which airframes are causing the most schedule disruption.

---

## Airports and Routes

### Airports in the dataset

```sql
MATCH (ap:Airport)
RETURN ap.iata AS IATA, ap.name AS Name, ap.city AS City, ap.country AS Country
ORDER BY ap.country, ap.city
```

> **Concepts**: simple node scan with property projection — inventory of all airports in the graph.

### Busiest airports by departures

```sql
MATCH (f:Flight)-[:DEPARTS_FROM]->(ap:Airport)
RETURN ap.iata AS Airport,
       ap.name AS Name,
       count(f) AS Departures
ORDER BY Departures DESC
LIMIT 10
```

> **Concepts**: traverses `DEPARTS_FROM` and aggregates by airport — shows the hubs with the most outbound flights.

### Airport-to-airport route frequency

```sql
MATCH (f:Flight)-[:DEPARTS_FROM]->(dep:Airport)
MATCH (f)-[:ARRIVES_AT]->(arr:Airport)
RETURN dep.iata AS Origin,
       arr.iata AS Destination,
       count(f) AS FlightCount
ORDER BY FlightCount DESC
LIMIT 15
```

> **Concepts**: two separate `MATCH` clauses share the same `f` variable — an alternative to chaining patterns that reads more clearly when the relationships go in different directions.

### Airports with the most delays

```sql
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay)
MATCH (f)-[:DEPARTS_FROM]->(ap:Airport)
RETURN ap.iata AS Airport,
       ap.name AS Name,
       count(d) AS DelayedFlights,
       sum(d.minutes) AS TotalDelayMinutes,
       avg(d.minutes) AS AvgDelayMinutes
ORDER BY TotalDelayMinutes DESC
LIMIT 10
```

> **Concepts**: joins flights to both delays and departure airports — aggregates delay statistics per airport to find the worst bottlenecks.

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

### Removals by reason

```sql
MATCH (r:Removal)
WHERE r.reason IS NOT NULL
RETURN r.reason AS Reason, count(r) AS Count
ORDER BY Count DESC
```

> **Concepts**: aggregation by removal reason — shows the most common causes of part replacement.

### Aircraft with the most removals

```sql
MATCH (a:Aircraft)-[:HAS_REMOVAL]->(r:Removal)
RETURN a.tail_number AS Aircraft,
       a.model AS Model,
       count(r) AS Removals,
       avg(r.tsn) AS AvgTimeSinceNew,
       avg(r.csn) AS AvgCyclesSinceNew
ORDER BY Removals DESC
```

> **Concepts**: aggregates removal metrics per aircraft — `avg(r.tsn)` shows whether parts are being pulled early or late in their lifecycle.

### Which components get removed most often?

```sql
MATCH (r:Removal)-[:REMOVED_COMPONENT]->(c:Component)
RETURN c.type AS ComponentType,
       c.name AS ComponentName,
       count(r) AS TimesRemoved
ORDER BY TimesRemoved DESC
LIMIT 15
```

> **Concepts**: aggregates from the removal side to find the most failure-prone part types.

---

## Cross-Domain Analysis

These queries traverse multiple domains of the graph to answer questions that span topology, operations, and maintenance.

### Aircraft with both critical maintenance and delays

```sql
MATCH (m:MaintenanceEvent {severity: 'CRITICAL'})-[:AFFECTS_AIRCRAFT]->(a:Aircraft)
WITH a, count(m) AS CriticalEvents
MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN a.tail_number AS Aircraft,
       a.model AS Model,
       CriticalEvents,
       count(d) AS DelayedFlights,
       sum(d.minutes) AS TotalDelayMinutes
ORDER BY CriticalEvents DESC
```

> **Concepts**: `WITH` passes intermediate results (aircraft and their critical event counts) to the next `MATCH`. This two-stage pattern is how you correlate data from different parts of the graph.

### Maintenance history for removed components

```sql
MATCH (r:Removal)-[:REMOVED_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
WHERE r.removal_date IS NOT NULL
RETURN c.name AS Component,
       c.type AS ComponentType,
       r.reason AS RemovalReason,
       r.removal_date AS RemovedOn,
       m.fault AS PriorFault,
       m.severity AS FaultSeverity,
       m.reported_at AS FaultReportedAt
ORDER BY r.removal_date DESC
LIMIT 20
```

> **Concepts**: links removals back to the maintenance events that preceded them on the same component — useful for understanding whether maintenance flagged a problem before the part was pulled.

### Full aircraft profile: systems, maintenance, flights, removals

```sql
MATCH (a:Aircraft {tail_number: 'N95040A'})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
WITH a, count(s) AS SystemCount
OPTIONAL MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)
WITH a, SystemCount, count(f) AS FlightCount
OPTIONAL MATCH (a)-[:HAS_REMOVAL]->(r:Removal)
WITH a, SystemCount, FlightCount, count(r) AS RemovalCount
OPTIONAL MATCH (m:MaintenanceEvent)-[:AFFECTS_AIRCRAFT]->(a)
RETURN a.tail_number AS TailNumber,
       a.model AS Model,
       a.operator AS Operator,
       SystemCount,
       FlightCount,
       RemovalCount,
       count(m) AS MaintenanceEvents
```

> **Concepts**: chains `WITH` clauses to collect counts from four different relationship types without cross-product inflation. Each `OPTIONAL MATCH` + `WITH` step aggregates one metric before moving on.

### Airports serving delayed aircraft with critical maintenance

```sql
MATCH (m:MaintenanceEvent {severity: 'CRITICAL'})-[:AFFECTS_AIRCRAFT]->(a:Aircraft)
WITH DISTINCT a
MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)-[:DEPARTS_FROM]->(ap:Airport)
WHERE EXISTS { (f)-[:HAS_DELAY]->(:Delay) }
RETURN ap.iata AS Airport,
       ap.name AS AirportName,
       count(DISTINCT a) AS AffectedAircraft,
       count(f) AS DelayedFlights
ORDER BY DelayedFlights DESC
```

> **Concepts**: `EXISTS { }` is an existential subquery — it checks whether a pattern exists without returning it. `DISTINCT` in the `WITH` clause de-duplicates aircraft before joining to flights.

### Route delay analysis with maintenance correlation

```sql
MATCH (f:Flight)-[:DEPARTS_FROM]->(dep:Airport)
MATCH (f)-[:ARRIVES_AT]->(arr:Airport)
OPTIONAL MATCH (f)-[:HAS_DELAY]->(d:Delay)
MATCH (a:Aircraft)-[:OPERATES_FLIGHT]->(f)
OPTIONAL MATCH (me:MaintenanceEvent)-[:AFFECTS_AIRCRAFT]->(a)
WHERE me.severity = 'CRITICAL'
WITH dep.iata AS Origin,
     arr.iata AS Destination,
     count(DISTINCT f) AS Flights,
     count(DISTINCT d) AS Delays,
     count(DISTINCT me) AS CriticalEvents
WHERE Flights > 1
RETURN Origin,
       Destination,
       Flights,
       Delays,
       CriticalEvents
ORDER BY Delays DESC
LIMIT 15
```

> **Concepts**: combines route, delay, and maintenance data in a single query. The `WITH ... WHERE` pattern filters on aggregated values (routes with more than one flight) — similar to SQL's `HAVING`.
