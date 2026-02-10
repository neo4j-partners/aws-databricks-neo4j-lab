# Part A: Data Exploration in Aura

Open [console.neo4j.io](https://console.neo4j.io), sign in, select your instance, and click **Query** to open the query interface. Use the queries below to explore the aircraft digital twin graph.

### Aircraft Fleet Overview

List every aircraft with its model, manufacturer, and system/component counts:

```cypher
MATCH (a:Aircraft)
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
WITH a, count(DISTINCT s) AS systems, count(DISTINCT c) AS components
RETURN a.tail_number AS tail, a.model AS model,
       a.manufacturer AS mfr, systems, components
ORDER BY a.tail_number
```

The fleet contains 20 aircraft across four models: A320-200 (Airbus), A321neo (Airbus), B737-800 (Boeing), and E190 (Embraer). Each aircraft has 4 systems and 16 components.

### System-Component Hierarchy

Expand a single aircraft to see its full system and component tree:

```cypher
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)
WITH a, s, c ORDER BY s.name, c.name
WITH a, s, collect(c.name) AS comps ORDER BY s.name
WITH a, collect({system: s.name, components: comps}) AS systems
RETURN a.tail_number AS tail, a.model AS model, systems
LIMIT 1
```

For a B737-800 (e.g. N95040A) this shows:
- **CFM56-7B #1** / **CFM56-7B #2** — Compressor Stage, Fan Module, High-Pressure Turbine, Main Fuel Pump, Thrust Bearing
- **Generic Avionics Suite** — Air Data Computer, Flight Management System, Navigation Receiver
- **Main Hydraulic System** — Flap Actuator, Hydraulic Reservoir, Main Pump

A320-200 aircraft have V2500 engines, A321neo aircraft have LEAP-1A engines, and E190 aircraft have GE CF34-10E engines.

### Sensors

View the sensors attached to each aircraft's systems. Every engine system has four sensor types:

```cypher
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(sys:System)-[:HAS_SENSOR]->(s:Sensor)
RETURN a.tail_number AS aircraft, sys.name AS system,
       s.sensor_id AS sensor, s.type AS type, s.unit AS unit
ORDER BY a.tail_number, sys.name
LIMIT 10
```

Sensor types: **EGT** (°C), **Vibration** (ips), **N1Speed** (rpm), **FuelFlow** (kg/s).

### Flight Operations — Top Routes

Find the most frequent routes across the fleet:

```cypher
MATCH (f:Flight)-[:DEPARTS_FROM]->(dep:Airport),
      (f)-[:ARRIVES_AT]->(arr:Airport)
WITH dep.iata AS origin, arr.iata AS dest, count(f) AS flights
RETURN origin, dest, flights
ORDER BY flights DESC
LIMIT 10
```

### Flight Delays

Trace delays for a specific aircraft, including the cause and airport:

```cypher
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:OPERATES_FLIGHT]->(f:Flight)
OPTIONAL MATCH (f)-[:HAS_DELAY]->(d:Delay)
OPTIONAL MATCH (f)-[:DEPARTS_FROM]->(dep:Airport)
OPTIONAL MATCH (f)-[:ARRIVES_AT]->(arr:Airport)
RETURN a.tail_number, f.flight_number, dep.iata AS origin, arr.iata AS dest,
       d.cause, d.minutes
ORDER BY d.minutes DESC
LIMIT 10
```

### Maintenance Events

Recent maintenance events with fault codes, severity, and affected systems:

```cypher
MATCH (me:MaintenanceEvent)-[:AFFECTS_AIRCRAFT]->(a:Aircraft)
OPTIONAL MATCH (me)-[:AFFECTS_SYSTEM]->(s:System)
RETURN a.tail_number AS aircraft, me.event_id AS event,
       me.reported_at AS date, me.severity AS severity, me.fault AS fault,
       s.name AS system
ORDER BY me.reported_at DESC
LIMIT 10
```

Common fault types include: vibration exceedance, overheat, sensor drift, contamination, bearing wear, fuel starvation, leak, and electrical fault.

### Maintenance Event Traversal

Trace the full path from aircraft through system and component to a critical maintenance event:

```cypher
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)
      -[:HAS_EVENT]->(m:MaintenanceEvent {severity: 'CRITICAL'})
RETURN a.tail_number, s.name AS system, c.name AS component, m.fault, m.reported_at
ORDER BY m.reported_at DESC
LIMIT 10
```

### Component Removals

Investigate removal records with time-since-new (TSN) and cycles-since-new (CSN) data:

```cypher
MATCH (a:Aircraft)-[:HAS_REMOVAL]->(r:Removal)
OPTIONAL MATCH (r)-[:REMOVED_COMPONENT]->(c:Component)
RETURN a.tail_number, c.name AS component, r.reason,
       r.tsn AS time_since_new, r.csn AS cycles_since_new
ORDER BY r.tsn DESC
LIMIT 10
```

### Document-Chunk Structure

The `enrich` command loaded three maintenance manuals as Document nodes, split them into Chunks with OpenAI embeddings, and linked them with NEXT_CHUNK chains:

```cypher
MATCH (d:Document)
OPTIONAL MATCH (d)<-[:FROM_DOCUMENT]-(c:Chunk)
WITH d, count(c) AS chunks,
     sum(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded
RETURN d.documentId AS doc_id, d.aircraftType AS aircraft,
       d.title AS title, chunks, embedded
ORDER BY d.documentId
```

Three manuals: AMM-A320-2024-001 (~43 chunks), AMM-A321neo-2024-001 (~58 chunks), AMM-B737-2024-001 (~53 chunks).

Preview the chunk chain for a document:

```cypher
MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document {documentId: 'AMM-A320-2024-001'})
WITH c ORDER BY c.index
OPTIONAL MATCH (c)-[:NEXT_CHUNK]->(next:Chunk)
RETURN c.index AS idx, substring(c.text, 0, 80) AS preview, next.index AS next_idx
LIMIT 10
```

### Extracted Entities — OperatingLimits

The `enrich` command used LLM entity extraction to create OperatingLimit nodes from the maintenance manuals. Each limit is qualified by aircraft type:

```cypher
MATCH (ol:OperatingLimit)
RETURN ol.name AS name, ol.parameterName AS param,
       ol.aircraftType AS aircraft, ol.unit AS unit,
       ol.regime AS regime, ol.minValue AS min, ol.maxValue AS max
ORDER BY ol.aircraftType, ol.parameterName
```

Examples: "EGT - A320-200", "Vibration - B737-800", "N1Speed - A321neo", "FuelFlow - B737-800".

### Cross-Links: Knowledge Graph to Operational Graph

The enrichment pipeline created cross-links between the extracted knowledge and the operational graph:

**Document → Aircraft** — Each maintenance manual is linked to the fleet aircraft of that model:

```cypher
MATCH (d:Document)-[:APPLIES_TO]->(a:Aircraft)
RETURN d.title AS manual, a.tail_number AS aircraft, a.model
ORDER BY d.title, a.tail_number
```

**Sensor → OperatingLimit** — Sensors are matched to extracted operating limits by parameter name and aircraft type:

```cypher
MATCH (s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit)
RETURN s.sensor_id AS sensor, s.type AS sensor_type, ol.name AS operating_limit
LIMIT 10
```

**Provenance chain** — Trace an OperatingLimit back through its source chunk and document to the fleet aircraft it applies to:

```cypher
MATCH (ol:OperatingLimit)-[:FROM_CHUNK]->(c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
      -[:APPLIES_TO]->(a:Aircraft)
RETURN ol.name AS limit, substring(c.text, 0, 60) AS source_chunk,
       d.title AS manual, a.tail_number AS aircraft
LIMIT 10
```

### Graph Statistics

```cypher
MATCH (n)
WITH labels(n)[0] AS label
RETURN label, count(*) AS nodeCount
ORDER BY nodeCount DESC
```
