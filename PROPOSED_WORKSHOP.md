# Neo4j + AWS + Databricks Lab

This document outlines the plan for a Neo4j + AWS + Databricks Lab, a five-phase hands-on workshop.

## Overview

Participants start by having a guided overview of the AWS Bedrock and AgentCore Console, then work through lab exercises in Databricks and Neo4j Aura for graph exploration. In these workshops AWS Bedrock and AgentCore provide pre-deployed infrastructure.

- **Total Duration:** ~4.5 hours
- **Dataset:** Aircraft Digital Twin Dataset (synthetic aviation fleet data)
- **Key Technologies:**
  - Neo4j Aura (Graph Database)
  - AWS Bedrock + AgentCore + AgentCore Gateway (Pre-deployed Neo4j MCP Server and AgentCore Agent infrastructure)
  - Databricks (Notebooks, Unity Catalog, AgentBricks)
  - Neo4j Spark Connector

---

## The Scenario: Zenith Horizon Airlines

### Your Role

Participants are **consultants** brought in to build a unified agent platform for Zenith Horizon Airlines.

### The Client

**Zenith Horizon Airlines** operates a fleet of 20 aircraft across 12 airports. Their data currently lives in three separate systems:

| System | Data | Current Access |
|--------|------|----------------|
| Neo4j Aura | Aircraft topology, maintenance events, components | 2 graph specialists |
| Databricks | 345K+ sensor readings, time-series analytics | 3 data engineers |
| AWS | Flight operations, delays, routes | Operations team only |

### The Problem

> "Our data is everywhere. Only three people in the company can write Cypher queries, and they're backlogged for weeks. Engineers need answers NOW."
> — **Jordan Chen**, VP of Maintenance

**Pain Points:**
- **Data silos** — No unified view across maintenance, sensors, and operations
- **Expert bottleneck** — Only a handful of people can query each system
- **Slow decisions** — Takes days to correlate sensor anomalies with maintenance events

### Your Mission

Build a **unified agent platform** that lets anyone ask questions in natural language:
- "Which aircraft have critical maintenance issues?"
- "What routes have the highest delay rates?"
- "How do sensor readings correlate with failures?"

### Today's Deliverable

By end of day, deliver a working prototype demonstrating:
1. Natural language queries across all data sources
2. Multi-agent routing for different domains (maintenance vs. operations)
3. No-code agent building for self-service dashboards

---

## Dataset Overview

The workshop uses a comprehensive Aircraft Digital Twin dataset that models a complete aviation fleet over 90 operational days (July 1 – September 29, 2024).

### Fleet Composition

| Aircraft Type | Percentage |
|--------------|------------|
| Boeing 737-800 | 40% |
| Airbus A320-200 | 30% |
| Airbus A321neo | 20% |
| Embraer E190 | 10% |

### Data Scale

| Entity | Count |
|--------|-------|
| Aircraft | 20 |
| Systems (Engine, Avionics, Hydraulics) | ~80 |
| Components (turbines, compressors, pumps) | ~200 |
| Sensors (EGT, Vibration, N1Speed, FuelFlow) | 160 |
| Flights | 800 |
| Airports | 12 |
| Delays | ~300 |
| Sensor Readings | 345,600+ |
| Maintenance Events | 300 |

### Graph Data Model

**Node Types (9):**
- `Aircraft` - Fleet metadata: tail numbers, models, operators, manufacturer
- `System` - Major systems per aircraft (Engine, Avionics, Hydraulics)
- `Component` - System subcomponents (turbines, compressors, pumps)
- `Sensor` - Monitoring devices (EGT, Vibration, N1Speed, FuelFlow)
- `Flight` - Flight operations with scheduling and routing
- `Airport` - Locations with IATA/ICAO codes and coordinates
- `Delay` - Delay records (Weather, Maintenance, NAS, Carrier)
- `Reading` - Hourly sensor telemetry measurements
- `MaintenanceEvent` - Fault records with severity levels

**Relationship Types (11):**

```
Aircraft Hierarchy:
  (Aircraft)-[:HAS_SYSTEM]->(System)
  (System)-[:HAS_COMPONENT]->(Component)
  (System)-[:HAS_SENSOR]->(Sensor)

Operational Flow:
  (Aircraft)-[:OPERATES_FLIGHT]->(Flight)
  (Flight)-[:DEPARTS_FROM]->(Airport)
  (Flight)-[:ARRIVES_AT]->(Airport)
  (Flight)-[:HAS_DELAY]->(Delay)

Maintenance Tracking:
  (Component)-[:HAS_EVENT]->(MaintenanceEvent)
  (MaintenanceEvent)-[:AFFECTS_SYSTEM]->(System)
  (MaintenanceEvent)-[:AFFECTS_AIRCRAFT]->(Aircraft)

Time-Series:
  (Sensor)-[:GENERATES]->(Reading)
```

### Maintenance Event Distribution

- 50% Minor severity
- 35% Major severity
- 15% Critical severity

---

## Lab Structure

### Phase 1: Foundation Setup (45 min)

> **Business Context:** You've arrived at Zenith Horizon's headquarters. IT has provisioned your access to their three core platforms. Before you can build anything, you need credentials and connectivity.

| Lab | Description |
|-----|-------------|
| Lab 0: AWS Console Tour | Read-only access to view the deployment of the Neo4j MCP Server to AgentCore along with a deployment of an Agent that shows how to call the MCP Server |
| Lab 1: Databricks Workspace Access | Workspace credentials and cluster access |
| Lab 2: Neo4j Aura Credentials | Save connection credentials (exploration happens in Phase 5) |

---

### Phase 2: AWS - AgentCore Overview + Notebook (60 min)

> **Business Context:** The maintenance team wants to ask questions about aircraft health without learning Cypher. AWS has pre-deployed an agent infrastructure that connects to Zenith Horizon's Neo4j database. You'll explore how it works and test it.

#### Part A: Read-Only Console Tour

Walk participants through the AWS Bedrock and AgentCore console to understand the pre-deployed architecture:

**Architecture Flow:**
```
AI Agent → Cognito (OAuth2) → AgentCore Gateway → AgentCore Runtime → Neo4j Aura
```

**Key Components to View:**

1. **AgentCore Gateway Configuration**
   - OAuth2 credential provider setup
   - JWT authorizer configuration
   - Gateway Target routing rules

2. **Neo4j MCP Server in AgentCore Runtime**
   - Container deployment (ARM64 image from ECR)
   - Environment configuration (NEO4J_URI, credentials)
   - Exposes two read-only tools:
     - `neo4j-mcp-server-target___get-schema` - Retrieves database schema
     - `neo4j-mcp-server-target___read-cypher` - Executes read-only Cypher queries

3. **Cognito User Pool**
   - M2M (machine-to-machine) OAuth2 authentication
   - Client credentials flow for agents
   - Resource server with custom scopes

4. **AgentCore Agent Deployment**
   - Choice of Basic Agent or Orchestrator Agent architecture
   - Claude Sonnet 4 integration via Bedrock Converse API
   - LangGraph for multi-agent orchestration

#### Part B: AgentCore Agent Sandbox Testing (No-Code)

- Use the AgentCore Agent Sandbox in the AWS Console
- Interactively test the deployed agent without writing code
- Send natural language questions about the aircraft data
- See agent reasoning and Cypher query generation in real-time

**Example Questions to Test:**
- "What aircraft have had the most maintenance events?"
- "Show me all critical severity faults in the last 30 days"
- "Which routes have the highest delay rates?"
- "What sensors are installed on aircraft N12345?"
- "Find flights that were delayed due to maintenance issues"

#### Part C: Databricks Notebook - Call the Agent

> Setting up Sagemaker takes a long time so we are only going to have participants run notebooks in Databricks

- Simple Databricks notebook that calls the agent via HTTP
- Uses pre-shared API key (no OAuth complexity for participants)
- Demonstrates querying Neo4j through natural language
- Participants see the agent reasoning and Cypher generation

**Notebook Flow:**
```python
# 1. Configure API endpoint and key
AGENT_ENDPOINT = "https://<api-gateway-url>/invoke"
API_KEY = dbutils.secrets.get(scope="workshop", key="agent-api-key")

# 2. Send natural language query
response = requests.post(
    AGENT_ENDPOINT,
    headers={"x-api-key": API_KEY},
    json={"query": "What are the most common failure patterns?"}
)

# 3. Display agent reasoning and results
print(response.json()["reasoning"])
print(response.json()["cypher_query"])
print(response.json()["results"])
```

#### Admin Pre-Configuration

- Deploy neo4j-agentcore-mcp-server to AgentCore (provides Cypher query tools)
- Deploy agentcore-neo4j-mcp-agent to AgentCore (calls the MCP server to answer questions)
- Add API Gateway in front of the agent with API key authentication
- Pre-load full aircraft digital twin data into Neo4j
- Share API key with participants (via Databricks secrets or config)
- Generate `.mcp-credentials.json` using `./deploy.sh credentials`

---

### Phase 3 (Optional): Databricks - ETL to Neo4j (45 min)

> **Business Context:** Zenith Horizon's operations team has new aircraft and operator data sitting in Databricks. They need it loaded into Neo4j so the agents can answer questions about the full fleet. You'll build that data pipeline.

#### Participant Experience: Pre-Configured Environment

- 19 CSV files pre-uploaded to Unity Catalog Volume
- Ready-to-run notebook provided - participants clone the sample notebook to run in their workspace

**Source Notebooks from Reference Project:**
- `2_upload_test_data_to_neo4j.ipynb` - Main ETL notebook
- `2_a_neo4j_validation.ipynb` - Validation queries

#### Data Subset: Aircraft and Operators

For this phase, participants load a subset to understand the ETL process:

- Aircraft nodes (tail numbers, models, fleet info)
- Operator nodes (airlines, operators)
- System nodes (Engine, Avionics, Hydraulics per aircraft)
- Relationships connecting aircraft to operators and systems

#### Part A: Data Model Mapping

| Relational Concept | Graph Concept |
|-------------------|---------------|
| Table rows | Nodes with labels and properties |
| Foreign keys | Relationships |
| Join tables | Direct graph connections |
| Column values | Node/relationship properties |

**Mapping Example:**
```
aircraft.csv row → (:Aircraft {tail_number, model, manufacturer})
operators.csv row → (:Operator {name, code, country})
aircraft.operator_id → (:Aircraft)-[:OPERATED_BY]->(:Operator)
```

#### Part B: Load Data with Spark Connector

```python
# Read from Delta Lake
aircraft_df = spark.read.format("delta").load("/Volumes/workshop/data/aircraft")

# Transform to node structure
nodes_df = aircraft_df.select(
    col("tail_number").alias("tail_number"),
    col("model").alias("model"),
    col("manufacturer").alias("manufacturer"),
    lit("Aircraft").alias("labels")
)

# Write to Neo4j
nodes_df.write \
    .format("org.neo4j.spark.DataSource") \
    .mode("overwrite") \
    .option("url", NEO4J_URI) \
    .option("authentication.basic.username", NEO4J_USER) \
    .option("authentication.basic.password", NEO4J_PASSWORD) \
    .option("labels", ":Aircraft") \
    .option("node.keys", "tail_number") \
    .save()
```

**Validation Queries:**
```cypher
// Count nodes by label
MATCH (n) RETURN labels(n) AS label, count(*) AS count

// Verify relationships
MATCH (a:Aircraft)-[r]->(s:System)
RETURN a.tail_number, type(r), s.name LIMIT 10
```

---

### Phase 4: Databricks - Multi-Agent with AgentBricks (45 min)

> **Business Context:** Different teams at Zenith Horizon have different questions. Maintenance wants component reliability data. Operations wants delay analysis. You'll build an orchestrator that routes queries to the right specialist agent.

#### No-Code Visual Builder

Build multi-agent using AgentBricks visual interface

#### Agent Architecture

The orchestrator routes queries to specialized agents based on domain:

```
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                            │
│           (Routes based on query domain)                    │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
                  ▼                       ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│        AGENT A              │ │        AGENT B              │
│   (Maintenance Domain)      │ │   (Operations Domain)       │
│                             │ │                             │
│ - Faults & components       │ │ - Flight schedules          │
│ - Sensor anomalies          │ │ - Delay analysis            │
│ - System reliability        │ │ - Route performance         │
│                             │ │                             │
│ Calls: AWS AgentCore        │ │ Queries: Lakehouse +        │
│        (Full Neo4j)         │ │          Phase 3 Neo4j      │
└─────────────────────────────┘ └─────────────────────────────┘
```

**Example Query Routing:**
- "What components fail most often?" → Agent A (Maintenance)
- "Which routes have the most delays?" → Agent B (Operations)
- "How do sensor anomalies correlate with flight delays?" → Both agents

#### Deployment

Deploy as serving endpoint

> **TODO:** Research how AgentBricks handles external HTTP calls
> - Unity Catalog HTTP Connection?
> - Built-in HTTP tool?
> - Custom wrapper if needed?

---

### Phase 5: Neo4j Aura - Graph Exploration & Aura Agents (50 min)

> **Business Context:** Before the final demo to Zenith Horizon's leadership, you'll explore the graph data yourself to understand what's possible. Then you'll build a no-code Aura Agent that executives can use without any technical training.

#### Part A: Graph Exploration with Browser/Bloom (30 min)

**Tools:** Neo4j Browser or Bloom

#### Guided Explorations

**1. Aircraft Topology (5 min)**
```cypher
// Visualize aircraft → system → component → sensor hierarchy
MATCH path = (a:Aircraft {tail_number: 'N12345'})-[:HAS_SYSTEM]->(s:System)
              -[:HAS_COMPONENT]->(c:Component)
RETURN path
```

**2. Maintenance Analysis (10 min)**
```cypher
// Find aircraft with critical maintenance events
MATCH (a:Aircraft)<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent {severity: 'critical'})
RETURN a.tail_number, a.model, count(m) AS critical_events
ORDER BY critical_events DESC
```

```cypher
// Trace maintenance event impact
MATCH path = (c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
              -[:AFFECTS_SYSTEM]->(s:System)<-[:HAS_SYSTEM]-(a:Aircraft)
WHERE m.severity = 'critical'
RETURN path LIMIT 25
```

**3. Operational Patterns (10 min)**
```cypher
// Find routes with highest delay rates
MATCH (f:Flight)-[:DEPARTS_FROM]->(dep:Airport),
      (f)-[:ARRIVES_AT]->(arr:Airport),
      (f)-[:HAS_DELAY]->(d:Delay)
RETURN dep.iata_code + ' → ' + arr.iata_code AS route,
       count(d) AS delays,
       collect(DISTINCT d.category) AS delay_types
ORDER BY delays DESC
LIMIT 10
```

```cypher
// Aircraft utilization
MATCH (a:Aircraft)-[:OPERATES_FLIGHT]->(f:Flight)
RETURN a.tail_number, a.model, count(f) AS total_flights
ORDER BY total_flights DESC
```

**4. Sensor Data Exploration (5 min)**
```cypher
// Sensor types per aircraft
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_SENSOR]->(sen:Sensor)
RETURN a.tail_number, collect(DISTINCT sen.type) AS sensor_types
```

---

#### Part B: Build an Aura Agent (No-Code) (20 min)

Neo4j Aura Agents provide a no-code way to build AI-powered assistants that can query your graph database using natural language. Participants will create an agent that helps analyze the aircraft digital twin data.

**What is an Aura Agent?**

An Aura Agent combines three powerful retrieval patterns:

| Tool Type | Purpose | Best For |
|-----------|---------|----------|
| **Cypher Templates** | Controlled, precise queries with parameters | Specific lookups, comparisons |
| **Similarity Search** | Semantic retrieval using vector embeddings | Finding relevant content by meaning |
| **Text2Cypher** | Flexible natural language to Cypher translation | Ad-hoc questions about the data |

##### Step 1: Create the Aircraft Analyst Agent

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Select **Agents** in the left-hand menu
3. Click **Create Agent**

**Agent Configuration:**

- **Name:** `{your-initials}-aircraft-analyst` (unique name required)
- **Description:** An AI-powered aircraft maintenance analyst that helps users explore the digital twin graph, analyze maintenance events, investigate flight delays, and discover relationships across the fleet.
- **Target Instance:** Select your Neo4j Aura instance
- **External Available from an Endpoint:** Enabled

**Prompt Instructions:**
```
You are an expert aircraft maintenance analyst assistant specializing in fleet operations and reliability.
You help users understand:
- Aircraft maintenance events and their severity patterns
- System and component reliability across the fleet
- Flight delay patterns and their causes
- Sensor data and anomaly detection
- Relationships between aircraft, systems, components, and maintenance history

Always provide specific examples from the knowledge graph when answering questions.
Ground your responses in the actual data from the aircraft digital twin dataset.
```

##### Step 2: Add Cypher Template Tools

Click **Add Tool** → **Cypher Template** for each tool:

**Tool 1: Get Aircraft Overview**

| Field | Value |
|-------|-------|
| Tool Name | `get_aircraft_overview` |
| Description | Get comprehensive overview of an aircraft including systems, maintenance events, and flight history |
| Parameters | `tail_number` (string) - The aircraft tail number (e.g., "N12345") |

**Cypher Query:**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (a)<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent)
OPTIONAL MATCH (a)-[:OPERATES_FLIGHT]->(f:Flight)
WITH a,
     collect(DISTINCT s.name) AS systems,
     collect(DISTINCT {severity: m.severity, description: m.description})[0..5] AS recent_events,
     count(DISTINCT f) AS total_flights
RETURN
    a.tail_number AS aircraft,
    a.model AS model,
    a.manufacturer AS manufacturer,
    systems,
    recent_events AS recent_maintenance,
    total_flights
```

**Tool 2: Find Aircraft with Shared Issues**

| Field | Value |
|-------|-------|
| Tool Name | `find_shared_issues` |
| Description | Find maintenance issues that affect multiple aircraft of the same model |
| Parameters | `model` (string) - Aircraft model (e.g., "Boeing 737-800") |

**Cypher Query:**
```cypher
MATCH (a:Aircraft {model: $model})<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent)
WITH m.description AS issue, collect(DISTINCT a.tail_number) AS affected_aircraft, count(DISTINCT a) AS aircraft_count
WHERE aircraft_count > 1
RETURN issue, affected_aircraft, aircraft_count
ORDER BY aircraft_count DESC
LIMIT 10
```

**Tool 3: Get Route Delay Analysis**

| Field | Value |
|-------|-------|
| Tool Name | `get_route_delays` |
| Description | Analyze delays for flights between two airports |
| Parameters | `origin` (string) - Origin IATA code, `destination` (string) - Destination IATA code |

**Cypher Query:**
```cypher
MATCH (f:Flight)-[:DEPARTS_FROM]->(dep:Airport {iata_code: $origin}),
      (f)-[:ARRIVES_AT]->(arr:Airport {iata_code: $destination})
OPTIONAL MATCH (f)-[:HAS_DELAY]->(d:Delay)
WITH f, d, dep, arr
RETURN
    dep.iata_code + ' → ' + arr.iata_code AS route,
    count(f) AS total_flights,
    count(d) AS delayed_flights,
    collect(DISTINCT d.category) AS delay_categories,
    round(100.0 * count(d) / count(f), 1) AS delay_percentage
```

##### Step 3: Add Text2Cypher Tool

Click **Add Tool** → **Text2Cypher**:

| Field | Value |
|-------|-------|
| Tool Name | `query_database` |
| Description | Query the aircraft digital twin graph using natural language. Translates questions into Cypher queries to retrieve data about aircraft, systems, components, sensors, flights, delays, and maintenance events. Use for ad-hoc questions beyond pre-defined templates. |

##### Step 4: Test the Agent

Test with these sample questions and observe the agent's tool selection and reasoning:

**Cypher Template Questions:**
- "Tell me about aircraft N12345" → Uses `get_aircraft_overview`
- "What issues affect Boeing 737-800 aircraft?" → Uses `find_shared_issues`
- "How are flights from LAX to JFK performing?" → Uses `get_route_delays`

**Text2Cypher Questions:**
- "Which aircraft has the most critical maintenance events?"
- "What sensors are on the Engine systems?"
- "How many flights had weather delays last month?"

**Observe for each query:**
1. Which tool the agent selected and why
2. The Cypher query generated or executed
3. How the agent synthesized the response
4. The reasoning process shown in tool explanations

##### Step 5: (Optional) Deploy to API

1. Click **Deploy** in the Aura Agent console
2. Copy the authenticated API endpoint
3. Use the endpoint from Databricks notebooks or other applications

**Example API Call:**
```python
import requests

response = requests.post(
    "https://your-agent-endpoint.neo4j.io/query",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"query": "What aircraft have critical maintenance issues?"}
)
print(response.json())
```

---

## Architecture Summary

### Phase 1: Setup

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  AWS Console │  │  Databricks  │  │  Neo4j Aura  │
│   (access)   │  │   (access)   │  │ (credentials)│
└──────────────┘  └──────────────┘  └──────────────┘
```

### Phase 2: AWS AgentCore (Console Tour + Sandbox + Notebook)

```
┌─────────────────────────────────────────────────────────────┐
│                           AWS                               │
│                                                             │
│  Agent Sandbox ──┐                                          │
│  (Console UI)    │         AgentCore    MCP        Neo4j    │
│                  ├───────▶ Agent ────▶ Gateway ──▶ MCP ──▶ Aura
│  Databricks      │         (Claude)    (OAuth2)   Server    │
│  Notebook ───────┘                                          │
│  (HTTP + API Key)                                           │
│                                                             │
│  The AgentCore Agent uses Claude to reason about questions  │
│  and calls the Neo4j MCP Server to execute Cypher queries   │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3 (Optional): Databricks ETL

```
┌─────────────────────────────────────────────────────────────┐
│                        DATABRICKS                           │
│  Volume (CSV) ──▶ Notebook ──▶ Spark Connector ──▶ Neo4j    │
└─────────────────────────────────────────────────────────────┘
```

### Phase 4: Databricks Multi-Agent

```
┌─────────────────────────────────────────────────────────────┐
│                        DATABRICKS                           │
│  ┌─────────────────┐                                        │
│  │   AgentBricks   │──▶ Agent A ──▶ AWS AgentCore (Phase 2) │
│  │  (Orchestrator) │                                        │
│  │                 │──▶ Agent B ──▶ Lakehouse / Neo4j       │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

### Phase 5: Neo4j Exploration

```
┌─────────────────────────────────────────────────────────────┐
│                        NEO4J AURA                           │
│  Browser/Bloom ──▶ Visualize ──▶ Cypher Queries             │
└─────────────────────────────────────────────────────────────┘
```

---

## Workshop Automation Options: Per-User Notebook Copies

Since participants share a workspace, each user needs their own copy of notebooks.

### Option 1: Manual Clone

Participants right-click template notebook → "Clone"

### Option 2: Automated Distribution Script

Review if possible to use Databricks SDK for Python:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace

w = WorkspaceClient()

for user_email in participant_emails:
    user_folder = f"/Users/{user_email}/workshop"
    w.workspace.mkdirs(user_folder)

    exported = w.workspace.export(
        path="/Shared/templates/phase2_notebook",
        format=workspace.ExportFormat.SOURCE
    )
    w.workspace.import_(
        path=f"{user_folder}/phase2_notebook",
        content=exported.content,
        format=workspace.ImportFormat.SOURCE,
        language=workspace.Language.PYTHON,
        overwrite=True
    )
```

---

## Admin Pre-Configuration Checklist

### AWS Setup

- [ ] Deploy neo4j-agentcore-mcp-server to AgentCore using `./deploy.sh`
- [ ] Deploy agentcore-neo4j-mcp-agent to AgentCore (Basic or Orchestrator variant)
- [ ] Generate credentials using `./deploy.sh credentials`
- [ ] Add API Gateway in front of agent with API key authentication
- [ ] Test agent invocation via API Gateway
- [ ] Test with `./cloud.sh` (Gateway) and `./cloud-http.sh` (direct Runtime)

### Neo4j Setup

- [ ] Provision Neo4j Aura instance
- [ ] Load full aircraft digital twin dataset (all 9 node types, 11 relationship types)
- [ ] Verify data with sample queries
- [ ] Test MCP server connectivity

### Databricks Setup

- [ ] Upload 19 CSV files to Unity Catalog Volume
- [ ] Create Phase 2 notebook (HTTP call to agent)
- [ ] Create Phase 3 notebook (Spark Connector ETL) - adapt from `2_upload_test_data_to_neo4j.ipynb`
- [ ] Create validation notebook - adapt from `2_a_neo4j_validation.ipynb`
- [ ] Configure cluster with Neo4j Spark Connector library
- [ ] Store API key in Databricks secrets
- [ ] Run notebook distribution script for participants

---

## Reference Projects

| Project | Link | Purpose |
|---------|------|---------|
| MCP Server | https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server | AgentCore MCP server deployment |
| AgentCore Agent | https://github.com/neo4j-partners/aws-starter/tree/main/agentcore-neo4j-mcp-agent | AI agent deployment (Basic + Orchestrator) |
| Databricks Samples | https://github.com/neo4j-partners/dbx-aircraft-analyst/tree/main | Databricks Sample Projects and HTTP connection patterns |
| Aircraft Data | https://github.com/neo4j-partners/dbx-aircraft-analyst/blob/main/aircraft_digital_twin_data/ARCHITECTURE.md | Source data and ETL examples |

---

## Suggested Improvements

### 1. Add Observability Section

The AgentCore agent supports OpenTelemetry for tracing. Consider adding a mini-lab where participants view agent traces:

- **Benefit:** Participants understand how the agent reasons through queries
- **Implementation:** Add CloudWatch Logs or X-Ray integration walkthrough
- **Time:** +15 min to Phase 2

### 2. Include Comparison Exercise

Add an exercise comparing direct Cypher queries vs. natural language agent queries:

```cypher
-- Direct Cypher (Phase 5)
MATCH (a:Aircraft)<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent)
WHERE m.severity = 'critical'
RETURN a.model, count(m) ORDER BY count(m) DESC

-- vs Natural Language (Phase 2)
"Which aircraft models have the most critical maintenance events?"
```

- **Benefit:** Shows when to use each approach
- **Time:** +10 min

### 3. Add Sensor Time-Series Lab (Optional Phase)

Leverage the 345,600+ sensor readings with Databricks SQL:

```sql
-- Detect anomalies using Delta Lake
SELECT sensor_id, timestamp, value,
       AVG(value) OVER (PARTITION BY sensor_id ORDER BY timestamp
                        ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) as rolling_avg
FROM sensor_readings
WHERE value > rolling_avg * 1.5  -- 50% deviation
```

- **Benefit:** Shows the dual-database strategy (Neo4j for topology, Databricks for time-series)
- **Time:** +30 min (optional phase)

### 4. Pre-Flight Checklist for Participants

Add a "Phase 0" self-service checklist participants complete before the workshop:

- [ ] Verify AWS Console access (read-only)
- [ ] Verify Databricks workspace login
- [ ] Save Neo4j Aura credentials locally
- [ ] Test network connectivity to all services

- **Benefit:** Reduces setup time during the workshop
- **Time:** Saves ~15 min of Phase 1

### 5. Troubleshooting Guide

Add common issues and solutions:

| Issue | Solution |
|-------|----------|
| "JWT token expired" | Re-run `./deploy.sh credentials` to refresh |
| "Neo4j connection refused" | Verify Aura instance is running; check firewall rules |
| Spark Connector fails | Confirm cluster has the neo4j-connector library installed |
| Agent returns empty results | Check if the database has data loaded |

### 6. Expand Phase 4 with Concrete AgentBricks Steps

Research and document the exact AgentBricks workflow:

- How to create a new agent in the visual builder
- How to configure HTTP connections to external APIs
- How to set up the orchestrator routing logic
- How to deploy and test the multi-agent system

### 7. Add Success Metrics

Define what "success" looks like for each phase:

| Phase | Success Criteria |
|-------|-----------------|
| Phase 1 | All participants have credentials saved |
| Phase 2 | Each participant successfully queries the agent |
| Phase 3 | Participants load ≥100 nodes into Neo4j |
| Phase 4 | Multi-agent routes queries correctly |
| Phase 5a | Participants execute 3+ Cypher queries in Browser/Bloom |
| Phase 5b | Participants create an Aura Agent with at least 2 tools |

### 8. Consider Shorter "Express" Version

For time-constrained events, offer a 2-hour version:

- **Express Phase 1:** Quick credential distribution (15 min)
- **Express Phase 2:** Agent Sandbox only, skip notebook (30 min)
- **Express Phase 3:** Pre-loaded data, participants run validation only (20 min)
- **Skip Phase 4:** (Multi-agent is advanced)
- **Express Phase 5:** Guided queries only (15 min)

### 9. Add Take-Home Resources

Provide participants with:

- Link to clone the reference repositories
- Sample `.env` template for self-deployment
- Recommended next steps for deeper learning
- Community resources (Neo4j Discord, AWS forums)
