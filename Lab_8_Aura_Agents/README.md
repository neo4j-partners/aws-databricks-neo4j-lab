# Lab 8: Neo4j Aura Exploration & Aura Agents

In this lab, you'll explore the aircraft digital twin knowledge graph directly in Neo4j Aura, then build an AI-powered agent using Aura Agents — all without writing any code.

## Prerequisites

- Completed **Lab 5** (Databricks ETL) — both notebooks to load the full aircraft graph
- Completed **Lab 6** (Semantic Search) — to add Document/Chunk nodes with embeddings
- Neo4j Aura credentials from Lab 1 (URI, username, password)

---

## Part A: Data Exploration in Aura

Open [console.neo4j.io](https://console.neo4j.io), sign in, select your instance, and click **Query** to open the query interface. Use the queries below to explore the aircraft digital twin graph you built in Labs 5 and 6.

### Aircraft Topology

Expand a single aircraft into its systems, components, and sensors to see the full hierarchy:

```cypher
// Visualize one aircraft's full hierarchy
MATCH (a:Aircraft {tail_number: 'N95040A'})-[r1:HAS_SYSTEM]->(s:System)-[r2:HAS_COMPONENT]->(c:Component)
RETURN a, r1, s, r2, c
```

```cypher
// View sensors attached to an aircraft's systems
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)-[:HAS_SENSOR]->(sen:Sensor)
RETURN a.tail_number, s.name AS system, sen.type AS sensor_type, sen.unit
```

### Flight Operations

Trace an aircraft's flight routes across the airport network, including delays and their causes:

```cypher
// Trace flights and delays for an aircraft
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:OPERATES_FLIGHT]->(f:Flight)
OPTIONAL MATCH (f)-[:HAS_DELAY]->(d:Delay)
OPTIONAL MATCH (f)-[:DEPARTS_FROM]->(dep:Airport)
OPTIONAL MATCH (f)-[:ARRIVES_AT]->(arr:Airport)
RETURN a, f, d, dep, arr
```

```cypher
// Top 10 longest delays and their causes
MATCH (a:Aircraft)-[:OPERATES_FLIGHT]->(f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN a.tail_number, f.flight_number, d.cause, d.minutes
ORDER BY d.minutes DESC
LIMIT 10
```

### Maintenance History

Find components with critical maintenance events and see which systems they affect:

```cypher
// Find components with critical maintenance events
MATCH (c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent {severity: 'Critical'})
RETURN c.name AS component, m.fault AS fault, m.corrective_action AS action
ORDER BY m.reported_at DESC LIMIT 10
```

```cypher
// Full path from aircraft to maintenance event
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)
      -[:HAS_EVENT]->(m:MaintenanceEvent {severity: 'Critical'})
RETURN a.tail_number, s.name AS system, c.name AS component, m.fault, m.reported_at
ORDER BY m.reported_at DESC
```

### Component Removals

Investigate removal records with time-since-new (TSN) and cycles-since-new (CSN) data:

```cypher
// View component removals with usage data
MATCH (a:Aircraft)-[:HAS_REMOVAL]->(r:Removal)
RETURN a.tail_number, r.reason, r.tsn AS time_since_new, r.csn AS cycles_since_new
ORDER BY r.tsn DESC LIMIT 10
```

### Cross-Entity Patterns

Discover which aircraft share the same maintenance faults, or which airports see the most delayed flights:

```cypher
// Aircraft that share the same fault type
MATCH (a1:Aircraft)-[:HAS_SYSTEM]->()-[:HAS_COMPONENT]->()-[:HAS_EVENT]->(m1:MaintenanceEvent),
      (a2:Aircraft)-[:HAS_SYSTEM]->()-[:HAS_COMPONENT]->()-[:HAS_EVENT]->(m2:MaintenanceEvent)
WHERE a1 <> a2 AND m1.fault = m2.fault
RETURN DISTINCT a1.tail_number, a2.tail_number, m1.fault
LIMIT 20
```

```cypher
// Airports with the most delayed arrivals
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay), (f)-[:ARRIVES_AT]->(apt:Airport)
RETURN apt.iata AS airport, apt.city, count(d) AS delay_count, round(avg(d.minutes), 1) AS avg_delay_minutes
ORDER BY delay_count DESC
```

### Fleet Overview

```cypher
// Fleet summary by manufacturer
MATCH (a:Aircraft)
RETURN a.manufacturer AS manufacturer, a.model AS model, count(a) AS count
ORDER BY count DESC
```

```cypher
// Graph statistics — count all node types
MATCH (n)
WITH labels(n)[0] AS label
RETURN label, count(*) AS nodeCount
ORDER BY nodeCount DESC
```

---

## Part B: Build an Aura Agent (No-Code)

## Step 1: Create the Aircraft Agent

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Select **Agents** in the left-hand menu
3. Click on **Create Agent**

![Aura Agents](images/aura_agents.png)

## Step 2: Configure Agent Details

Configure your new agent with the following settings. It is critical that you give your agent a unique name so that it does not conflict with other users' agents in the shared environment. If you have an error try another unique name by adding your initials or a number:

**Unique Agent Name:** `ryans-aircraft-analyst`

**Description:** An AI-powered aircraft analyst that helps users explore the Aircraft Digital Twin knowledge graph, analyze maintenance events, investigate component failures, and discover relationships across aircraft topology, flight operations, and maintenance history.

**Prompt Instructions:**
```
You are an expert aircraft maintenance and operations analyst.
You help users understand:
- Aircraft topology: systems, components, and sensors per aircraft
- Maintenance events: faults, severity levels, and corrective actions
- Flight operations: routes, delays, and operator performance
- Component removals: reasons, time-since-new, and cycles-since-new data
- Cross-entity patterns: shared faults across aircraft, delay-prone airports

Always provide specific data from the knowledge graph when answering questions.
Include tail numbers, system names, and fault details when relevant.
```

**Target Instance:** Select your Neo4j Aura instance created in Lab 1.

**External Available from an Endpoint:** Enabled

![Agent Configuration](images/aura_agents.png)

## Step 3: Add Cypher Template Tools

Click **Add Tool** and select **Cypher Template** for each of the following tools:

### Tool 1: Get Aircraft Overview

**Tool Name:** `get_aircraft_overview`

**Description:** Get comprehensive overview of an aircraft including its systems, recent maintenance events, and flight count.

**Parameters:** `tail_number` (string) - The aircraft tail number to look up (e.g., "N95040A", "N30268B")

**Cypher Query:**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
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

### Tool 2: Find Aircraft with Shared Faults

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

### Tool 3: Get Maintenance Summary

**Tool Name:** `get_maintenance_summary`

**Description:** Get a summary of maintenance events for a specific aircraft, grouped by severity.

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

## Step 4: Add Text2Cypher Tool

Click **Add Tool** and select **Text2Cypher** to enable natural language to Cypher translation:

**Tool Name:** `query_aircraft_graph`

**Description:** Query the Aircraft Digital Twin knowledge graph using natural language. This tool translates user questions into Cypher queries to retrieve data about aircraft, their systems and components, maintenance events and fault history, flight operations and delays, airports, sensor metadata, and component removals. Use this for ad-hoc questions that require flexible data exploration beyond the pre-defined Cypher templates.

## Step 5: Test the Agent

Test your agent with the sample questions below. After each test, observe:
1. Which tool the agent selected and why
2. The context retrieved from the knowledge graph
3. How the agent synthesized the response
4. Tool explanations showing the reasoning process

### Cypher Template Questions

Try asking: **"Tell me about aircraft N95040A"**

The agent recognizes this matches the `get_aircraft_overview` template and executes the pre-defined Cypher query with "N95040A" as the parameter. You'll see the aircraft's model, operator, systems, flight count, and recent maintenance events.

Other Cypher template questions to try:
- "What faults do aircraft N95040A and N30268B share?" — Uses `find_shared_faults` to compare maintenance history between two aircraft.
- "Show the maintenance summary for N54980C" — Uses `get_maintenance_summary` to show events grouped by severity.

### Text2Cypher Questions

Try asking: **"Which aircraft has the most critical maintenance events?"**

The agent translates this natural language question into a Cypher query that counts critical-severity maintenance events per aircraft and returns the highest.

Other Text2Cypher questions to try:
- "What are the top causes of flight delays?" — Generates a query to aggregate delay causes.
- "Which airports have the most delayed arrivals?" — Creates a query joining Flights, Delays, and Airports.
- "Show all components in the hydraulics system" — Traverses the System → Component hierarchy.
- "Find flights operated by ExampleAir" — Queries flight operations by operator.

## Step 6: (Optional) Add Similarity Search Tool

> **Note:** Similarity Search requires an embedding provider that matches the embeddings stored in your vector index. If you created embeddings in Lab 6 using Databricks Foundation Model APIs (BGE-large, 1024 dimensions), you'll need a compatible embedding provider configured in Aura. If you have an OpenAI API key available, you can re-embed the chunks with OpenAI and use the similarity search tool. Otherwise, skip this step — the Cypher Template and Text2Cypher tools provide comprehensive access to the graph.

If you have a compatible embedding provider:

1. Click **Add Tool** and select **Similarity Search**
2. **Tool Name:** `search_maintenance_docs`
3. **Description:** Search aircraft maintenance documentation semantically to find relevant procedures, troubleshooting steps, and specifications.
4. Configure the embedding provider and select the `maintenanceChunkEmbeddings` vector index
5. Set **Top K** to 5

Sample questions for similarity search:
- "How do I troubleshoot engine vibration?"
- "What are the EGT limits during takeoff?"
- "What causes hydraulic pressure loss?"

## Step 7: (Optional) Deploy to API

Deploy your agent to a production endpoint:
1. Click **Deploy** in the Aura Agent console
2. Copy the authenticated API endpoint
3. Use the endpoint in your applications

## Summary

You have built an Aura Agent that provides no-code access to the Aircraft Digital Twin knowledge graph using powerful retrieval patterns:

| Tool Type | Purpose | Best For |
|-----------|---------|----------|
| **Cypher Templates** | Controlled, precise queries | Aircraft overviews, shared faults, maintenance summaries |
| **Text2Cypher** | Flexible natural language | Ad-hoc questions about topology, flights, delays, removals |
| **Similarity Search** | Semantic retrieval (optional) | Finding maintenance procedures by meaning |

These same retrieval patterns are implemented programmatically in Lab 6 (Semantic Search / GraphRAG) using Python, and the graph is queried by AI agents in Lab 4 (AgentCore) and Lab 7 (AgentBricks).

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

**Description:** Get a summary of the entire fleet by manufacturer and model.

**Parameters:** None

**Cypher Query:**
```cypher
MATCH (a:Aircraft)
OPTIONAL MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)
WITH a, count(f) AS flights
RETURN
    a.manufacturer AS manufacturer,
    a.model AS model,
    a.operator AS operator,
    count(a) AS aircraft_count,
    sum(flights) AS total_flights
ORDER BY aircraft_count DESC
```
