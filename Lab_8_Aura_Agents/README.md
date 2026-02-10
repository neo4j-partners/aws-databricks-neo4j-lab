# Lab 8: Neo4j Aura Exploration & Aura Agents

In this lab, you'll explore the Aircraft Digital Twin knowledge graph directly in Neo4j Aura, then build an AI-powered agent using Aura Agents — all without writing any code.

> **Infrastructure:** This lab uses the **shared Reference Aura Instance**, which contains the complete dataset with all entities, relationships, maintenance manual chunks, embeddings, and extracted operating limits.

## Prerequisites

- Neo4j Aura instance with data loaded via the `populate-aircraft-db` CLI tool:
  - `load` command — 20 aircraft, 80 systems, 320 components, 320 sensors, 10 airports, 200 flights, delays, maintenance events, and removals
  - `enrich` command — 3 maintenance manuals chunked with OpenAI embeddings, OperatingLimit entities extracted, and cross-links created
- Neo4j Aura credentials (URI, username, password)

---

## Part A: Data Exploration in Aura

Before building the agent, explore the graph to understand what's available. See **[EXPLORE.md](EXPLORE.md)** for guided Cypher queries covering:

- **Operational graph** — fleet overview, system-component hierarchy, sensors, flights, delays, maintenance events, removals
- **Enrichment data** — document-chunk structure, OperatingLimit entities, cross-links (Document→Aircraft, Sensor→OperatingLimit, provenance chains)

---

## Part B: Build an Aura Agent (No-Code)

## Step 1: Create the Aircraft Agent

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Select **Agents** in the left-hand menu
3. Click on **Create Agent**

![Aura Agents](images/aura_agents.png)

## Step 2: Configure Agent Details

Configure your new agent with the following settings. Give your agent a unique name so it doesn't conflict with other users' agents. If you get an error, try another unique name by adding your initials or a number.

**Unique Agent Name:** `aircraft-analyst` (add your initials if needed)

**Description:** An AI-powered aircraft analyst that helps users explore the Aircraft Digital Twin knowledge graph, analyze maintenance events, investigate component failures, look up sensor operating limits, and discover relationships across aircraft topology, flight operations, and maintenance documentation.

**Prompt Instructions:**
```
You are an expert aircraft maintenance and operations analyst.
You help users understand:
- Aircraft topology: systems, components, and sensors per aircraft
- Maintenance events: faults, severity levels, and corrective actions
- Flight operations: routes, delays, and operator performance
- Component removals: reasons, time-since-new, and cycles-since-new data
- Sensor operating limits: parameter limits extracted from maintenance manuals
- Maintenance documentation: chunked manuals with provenance tracking
- Cross-entity patterns: shared faults across aircraft, delay-prone airports,
  sensor-to-limit mappings

Always provide specific data from the knowledge graph when answering questions.
Include tail numbers, system names, sensor IDs, and fault details when relevant.
When discussing operating limits, reference the source maintenance manual.
```

**Target Instance:** Select your Neo4j Aura instance.

**External Available from an Endpoint:** Enabled

## Step 3: Add Cypher Template Tools

Click **Add Tool** and select **Cypher Template** for each of the following tools:

### Tool 1: Get Aircraft Overview

**Tool Name:** `get_aircraft_overview`

**Description:** Get comprehensive overview of an aircraft including its systems, components, sensors, recent maintenance events, and flight count.

**Parameters:** `tail_number` (string) - The aircraft tail number (e.g., "N95040A", "N30268B", "N54980C")

**Cypher Query:**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
OPTIONAL MATCH (c)-[:HAS_EVENT]->(m:MaintenanceEvent)
OPTIONAL MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)
WITH a,
     collect(DISTINCT s.name) AS systems,
     collect(DISTINCT {fault: m.fault, severity: m.severity, component: c.name})[0..10] AS recent_events,
     count(DISTINCT f) AS flight_count
RETURN
    a.tail_number AS tail_number,
    a.model AS model,
    a.manufacturer AS manufacturer,
    a.operator AS operator,
    systems,
    flight_count,
    recent_events AS maintenance_events
```

### Tool 2: Get Maintenance Summary

**Tool Name:** `get_maintenance_summary`

**Description:** Get a summary of maintenance events for a specific aircraft, grouped by severity. Shows event counts and sample faults for each severity level.

**Parameters:** `tail_number` (string) - The aircraft tail number (e.g., "N95040A")

**Cypher Query:**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})-[:HAS_SYSTEM]->(s:System)
      -[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
RETURN
    m.severity AS severity,
    count(m) AS event_count,
    collect(DISTINCT m.fault)[0..5] AS sample_faults,
    collect(DISTINCT c.name)[0..5] AS affected_components
ORDER BY event_count DESC
```

### Tool 3: Get Sensor Operating Limits

**Tool Name:** `get_sensor_limits`

**Description:** Get the operating limits for sensors on a specific aircraft, including parameter ranges extracted from maintenance manuals. Shows what the safe operating ranges are for each sensor type.

**Parameters:** `tail_number` (string) - The aircraft tail number (e.g., "N95040A")

**Cypher Query:**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})-[:HAS_SYSTEM]->(sys:System)
      -[:HAS_SENSOR]->(s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit)
RETURN
    sys.name AS system,
    s.sensor_id AS sensor,
    s.type AS sensor_type,
    s.unit AS unit,
    ol.name AS limit_name,
    ol.regime AS regime,
    ol.minValue AS min_value,
    ol.maxValue AS max_value
ORDER BY sys.name, s.type
```

### Tool 4: Find Aircraft with Shared Faults

**Tool Name:** `find_shared_faults`

**Description:** Find maintenance faults that two aircraft have in common, helping identify fleet-wide issues.

**Parameters:**
- `tail1` (string) - First aircraft tail number
- `tail2` (string) - Second aircraft tail number

**Cypher Query:**
```cypher
MATCH (a1:Aircraft {tail_number: $tail1})-[:HAS_SYSTEM]->()-[:HAS_COMPONENT]->()-[:HAS_EVENT]->(m1:MaintenanceEvent),
      (a2:Aircraft {tail_number: $tail2})-[:HAS_SYSTEM]->()-[:HAS_COMPONENT]->()-[:HAS_EVENT]->(m2:MaintenanceEvent)
WHERE m1.fault = m2.fault
WITH a1, a2, collect(DISTINCT m1.fault) AS shared_faults
RETURN
    a1.tail_number AS aircraft_1,
    a2.tail_number AS aircraft_2,
    shared_faults,
    size(shared_faults) AS num_shared_faults
```

### Tool 5: Find Maintenance Manual for Aircraft

**Tool Name:** `find_manual`

**Description:** Find the maintenance manual that applies to a specific aircraft and show its document structure including chunk count and embedding coverage.

**Parameters:** `tail_number` (string) - The aircraft tail number (e.g., "N30268B")

**Cypher Query:**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})<-[:APPLIES_TO]-(d:Document)
OPTIONAL MATCH (d)<-[:FROM_DOCUMENT]-(c:Chunk)
WITH a, d, count(c) AS chunks,
     sum(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded
RETURN
    a.tail_number AS aircraft,
    a.model AS model,
    d.documentId AS document_id,
    d.title AS title,
    chunks,
    embedded
```

## Step 4: Add Text2Cypher Tool

Click **Add Tool** and select **Text2Cypher** to enable natural language to Cypher translation:

**Tool Name:** `query_aircraft_graph`

**Description:** Query the Aircraft Digital Twin knowledge graph using natural language. This tool translates user questions into Cypher queries to retrieve data about aircraft, their systems and components, maintenance events and fault history, flight operations and delays, airports, sensor metadata, component removals, maintenance documentation (Documents and Chunks), extracted operating limits (OperatingLimit nodes), and cross-links between documentation and operational data. Use this for ad-hoc questions that require flexible data exploration beyond the pre-defined Cypher templates.

## Step 5: Add Similarity Search Tool

The graph includes OpenAI embeddings on Chunk nodes from the three maintenance manuals.

1. Click **Add Tool** and select **Similarity Search**
2. **Tool Name:** `search_maintenance_docs`
3. **Description:** Search aircraft maintenance documentation semantically to find relevant procedures, troubleshooting steps, operating limits, and inspection schedules. The documentation covers A320-200, A321neo, and B737-800 maintenance and troubleshooting manuals.
4. Configure the **OpenAI** embedding provider with the same API key used during `enrich`
5. Select the `maintenanceChunkEmbeddings` vector index
6. Set **Top K** to 5

## Step 6: Test the Agent

Test your agent with the sample questions below. After each test, observe:
1. Which tool the agent selected and why
2. The context retrieved from the knowledge graph
3. How the agent synthesized the response

### Cypher Template Questions

**"Tell me about aircraft N95040A"** — Uses `get_aircraft_overview`. You'll see it's a Boeing B737-800 with CFM56-7B engines, Generic Avionics Suite, and Main Hydraulic System.

**"What are the sensor operating limits for N30268B?"** — Uses `get_sensor_limits` to show EGT, Vibration, N1Speed, and FuelFlow limits for this A320-200, extracted from the maintenance manual.

**"Show the maintenance summary for N54980C"** — Uses `get_maintenance_summary` to show events grouped by severity (CRITICAL, MAJOR, MINOR) for this A321neo.

**"What faults do aircraft N95040A and N26760M share?"** — Uses `find_shared_faults` to compare maintenance history between two B737-800s.

**"What maintenance manual applies to N30268B?"** — Uses `find_manual` to show the A320-200 Maintenance and Troubleshooting Manual with its chunk/embedding counts.

### Text2Cypher Questions

**"Which aircraft has the most critical maintenance events?"** — Generates a Cypher query counting CRITICAL-severity events per aircraft.

**"What are the top causes of flight delays?"** — Aggregates delay causes across all flights.

**"Which airports have the most delayed arrivals?"** — Joins Flights, Delays, and Airports.

**"Show all components in the hydraulics system"** — Traverses the System-Component hierarchy.

**"Which sensors have operating limits defined?"** — Traverses the Sensor-OperatingLimit cross-link.

**"Trace the provenance of the EGT operating limit for B737-800"** — Follows OperatingLimit → Chunk → Document → Aircraft.

### Similarity Search Questions

**"How do I troubleshoot engine vibration?"** — Finds relevant chunks from the maintenance manuals about vibration diagnostics.

**"What are the EGT limits during takeoff?"** — Retrieves chunks describing exhaust gas temperature limits.

**"What is the engine inspection schedule?"** — Finds chunks from Section 9 of the manuals covering scheduled maintenance tasks.

## Step 7: (Optional) Deploy to API

Deploy your agent to a production endpoint:
1. Click **Deploy** in the Aura Agent console
2. Copy the authenticated API endpoint
3. Use the endpoint in your applications

## Summary

You have built an Aura Agent that provides no-code access to the Aircraft Digital Twin knowledge graph using three retrieval patterns:

| Tool Type | Purpose | Best For |
|-----------|---------|----------|
| **Cypher Templates** | Controlled, precise queries | Aircraft overviews, maintenance summaries, sensor limits, shared faults, manual lookup |
| **Text2Cypher** | Flexible natural language | Ad-hoc questions about topology, flights, delays, removals, cross-links |
| **Similarity Search** | Semantic retrieval | Finding maintenance procedures, troubleshooting steps, and inspection schedules by meaning |

## Graph Schema Reference

**Node types (9 operational + 3 enrichment):**
Aircraft, System, Component, Sensor, Airport, Flight, Delay, MaintenanceEvent, Removal, Document, Chunk, OperatingLimit

**Relationship types (12 operational + 5 enrichment):**
HAS_SYSTEM, HAS_COMPONENT, HAS_SENSOR, HAS_EVENT, OPERATES_FLIGHT, DEPARTS_FROM, ARRIVES_AT, HAS_DELAY, AFFECTS_SYSTEM, AFFECTS_AIRCRAFT, HAS_REMOVAL, REMOVED_COMPONENT, FROM_DOCUMENT, NEXT_CHUNK, APPLIES_TO, HAS_LIMIT, FROM_CHUNK

**Indexes:**
- Vector: `maintenanceChunkEmbeddings` on Chunk.embedding
- Fulltext: `maintenanceChunkText` on Chunk.text

## Next Steps

Congratulations — you've completed the workshop! You can now:
- Extend the agent with additional Cypher template tools (see examples below)
- Deploy the agent as a production API endpoint
- Explore the [Neo4j Aura Agents documentation](https://neo4j.com/docs/aura/aurads/aura-agents/) for advanced features

## Additional Cypher Template Tools

These tools can be added to extend your agent's capabilities:

### Get Component Removal History

**Tool Name:** `get_removal_history`

**Description:** Get component removal history for an aircraft, including reasons and usage data.

**Parameters:** `tail_number` (string) - The aircraft tail number (e.g., "N95040A")

**Cypher Query:**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})-[:HAS_REMOVAL]->(r:Removal)
OPTIONAL MATCH (r)-[:REMOVED_COMPONENT]->(c:Component)
RETURN
    a.tail_number AS aircraft,
    c.name AS component,
    r.reason AS removal_reason,
    r.removal_date AS date,
    r.tsn AS time_since_new,
    r.csn AS cycles_since_new
ORDER BY r.removal_date DESC
LIMIT 20
```

### Fleet Summary

**Tool Name:** `fleet_summary`

**Description:** Get a summary of the entire fleet by manufacturer and model, including flight counts.

**Parameters:** None

**Cypher Query:**
```cypher
MATCH (a:Aircraft)
OPTIONAL MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)
WITH a.manufacturer AS manufacturer, a.model AS model,
     count(DISTINCT a) AS aircraft_count, count(f) AS total_flights
RETURN manufacturer, model, aircraft_count, total_flights
ORDER BY aircraft_count DESC
```

### Airport Delay Analysis

**Tool Name:** `airport_delays`

**Description:** Find airports with the most delayed arrivals, including average delay time.

**Parameters:** None

**Cypher Query:**
```cypher
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay), (f)-[:ARRIVES_AT]->(apt:Airport)
RETURN apt.iata AS airport, apt.city, count(d) AS delay_count,
       round(avg(d.minutes), 1) AS avg_delay_minutes
ORDER BY delay_count DESC
```

### Sensor-to-Limit Provenance

**Tool Name:** `sensor_limit_provenance`

**Description:** Trace a sensor's operating limit back to the source chunk and maintenance manual, showing the full provenance chain.

**Parameters:** `sensor_id` (string) - The sensor ID (e.g., "AC1001-S01-SN01")

**Cypher Query:**
```cypher
MATCH (s:Sensor {sensor_id: $sensor_id})-[:HAS_LIMIT]->(ol:OperatingLimit)
OPTIONAL MATCH (ol)-[:FROM_CHUNK]->(c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
RETURN
    s.sensor_id AS sensor,
    s.type AS sensor_type,
    ol.name AS limit_name,
    ol.minValue AS min_value,
    ol.maxValue AS max_value,
    ol.unit AS unit,
    substring(c.text, 0, 200) AS source_text,
    d.title AS manual
```
