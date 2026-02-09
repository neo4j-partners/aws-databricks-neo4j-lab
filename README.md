# Hands-On Lab: Neo4j, AWS, and Databricks

Build AI Agents and Knowledge Graphs with Neo4j, AWS Bedrock, and Databricks.

This hands-on workshop teaches you how to build production-ready AI agents that combine the power of graph databases with modern cloud platforms. You'll work with a comprehensive Aircraft Digital Twin dataset, learning to load data into Neo4j, query it with natural language, and build multi-agent systems that intelligently route questions to the right data source.

## Overview

**Total Duration:** ~4 hours

Participants start with a guided overview of AWS Bedrock and AgentCore, then work through lab exercises in Databricks and Neo4j Aura for graph exploration. AWS Bedrock and AgentCore provide pre-deployed infrastructure, while Databricks provides the notebook environment and multi-agent orchestration.

### Dataset

The workshop uses a comprehensive **Aircraft Digital Twin** dataset that models a complete aviation fleet over 90 operational days. The data is split across two platforms, each chosen for the workload it handles best:

- **Databricks Lakehouse** stores the **time-series sensor telemetry** — 345,600+ hourly readings across 90 days. Columnar storage and SQL make the Lakehouse ideal for aggregations, trend analysis, and statistical comparisons over large volumes of timestamped data.
- **Neo4j Aura** stores the **richly connected relational data** — aircraft topology, component hierarchies, maintenance events, flights, delays, and airport routes. A graph database handles multi-hop relationship traversals natively, avoiding the expensive JOINs a tabular database would require for queries like "Which components caused flight delays?"

Together the dataset includes:

- **20 Aircraft** with tail numbers, models, and operators
- **80 Systems** (Engines, Avionics, Hydraulics) per aircraft
- **320 Components** (Turbines, Compressors, Pumps, etc.)
- **160 Sensors** with monitoring metadata
- **345,600+ Sensor Readings** (hourly telemetry over 90 days)
- **800 Flights** with departure/arrival information
- **300 Maintenance Events** with fault severity and corrective actions
- **12 Airports** in the route network

### Key Technologies

| Technology | Purpose |
|------------|---------|
| **Neo4j Aura** | Graph database for storing aircraft relationships |
| **AWS Bedrock + AgentCore** | Pre-deployed Neo4j MCP Server and Agent infrastructure |
| **Databricks** | Notebooks, Unity Catalog, AI/BI Genie, AgentBricks |
| **Neo4j Spark Connector** | ETL from Databricks to Neo4j |
| **Model Context Protocol (MCP)** | Standard for connecting AI models to data sources |

---

## Setup Notes

If you are **attending a workshop**, the Databricks environment (cluster, libraries, data, and tables) has already been configured for you — skip straight to the labs.

If you are **running this on your own** or are a **lab administrator** preparing the environment for participants, see the [Lab Admin Setup Guide](lab_setup/README.md) for instructions on creating the cluster, installing libraries, uploading data, and configuring Databricks Genie.

### Neo4j Instances

Each participant receives their own **personal Neo4j Aura instance** for hands-on work — loading data via the Spark Connector (Lab 5), building vector indexes (Lab 6), and exploring the graph in the Aura console (Lab 8). Depending on how far you get in Lab 5, your personal instance may contain a subset of the full dataset.

In addition, the workshop administrators have set up a **shared Neo4j Aura instance** that contains the **complete Aircraft Digital Twin dataset** (all nodes, relationships, and indexes). A Neo4j MCP server has been pre-configured against this shared instance. Labs that use the MCP server — such as the AgentBricks multi-agent supervisor (Lab 7) and the AWS AgentCore agent (Lab 4) — connect to the shared instance so that every participant works with the full graph regardless of their personal instance's state.

---

## Lab Structure

### Phase 1: Foundation Setup (45 min)

*Get connected to all workshop resources.*

#### Part A: AWS Console Tour
- Read-only access to view the Neo4j MCP Server deployment in AgentCore
- Understand the architecture: `AgentCore Agent → AgentCore Gateway → Neo4j MCP Server → Neo4j Aura`

#### Part B: Neo4j Aura Credentials
- [Lab 0 - Sign In](Lab_0_Sign_In) - Access workshop resources
- [Lab 1 - Neo4j Aura Setup](Lab_1_Aura_Setup) - Save connection credentials

---

### Phase 2: AWS AgentCore Overview (60 min)

*Explore pre-deployed AI agent infrastructure.*

#### Part A: Read-Only Console Tour
- Walk-through of Bedrock and AgentCore
- View the pre-deployed Neo4j MCP server (AgentCore Gateway + MCP Server Hosting)
- View the AgentCore agent deployment that calls the Neo4j MCP server

#### Part B: AgentCore Agent Sandbox Testing (No-Code)
- [Lab 4 - AWS AgentCore](Lab_4_AWS_Agent_Core/README.md) - Use the AgentCore Agent Sandbox
- Interactively test the deployed agent without writing code
- Send natural language questions about the aircraft data
- See agent reasoning and Cypher query generation in real-time

---

### Phase 3: Building a GraphRAG Pipeline with Databricks and Neo4j (90 min)

*Build a complete GraphRAG pipeline — from raw CSV data and maintenance documentation to a knowledge graph with semantic search capabilities.*

In this phase you'll construct a knowledge graph in Neo4j and layer semantic search on top of it. First, you'll use the Neo4j Spark Connector and Python driver to load structured aircraft data (fleet inventory, systems, flights, maintenance events) into a graph. Then you'll add unstructured data by chunking the A320-200 Maintenance Manual, generating vector embeddings with Databricks Foundation Model APIs, and creating a vector index in Neo4j. Finally, you'll query this combined graph using GraphRAG retrievers that blend vector similarity search with graph traversal — connecting maintenance procedures back to the aircraft topology.

**Participant Experience:** Pre-configured environment with CSV files and maintenance documentation in Unity Catalog Volume and ready-to-run notebooks.

#### Part A: Databricks Workspace Access
- Workspace credentials and cluster access
- Import notebooks to your workspace

#### Part B: Load Data with Spark Connector
- [Lab 5 - Databricks ETL to Neo4j](Lab_5_Databricks_ETL_Neo4j/README.md)
- Load core aircraft topology (Aircraft, System, Component) via Spark Connector
- Load full dataset (Sensors, Airports, Flights, Delays, Maintenance Events, Removals) via Python driver
- Validate with Cypher queries and explore in Neo4j Aura

#### Part C: Semantic Search & GraphRAG
- [Lab 6 - Semantic Search](Lab_6_Semantic_Search/README.md)
- Load the A320-200 Maintenance Manual into Neo4j as Document/Chunk nodes
- Generate embeddings using Databricks Foundation Model APIs
- Create a vector index for similarity search
- Build GraphRAG retrievers combining vector search with graph traversal
- Compare standard vector retrieval vs. graph-enhanced retrieval results

**Data Location:** `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/`

---

### Phase 4: Multi-Agent Aircraft Analytics with AgentBricks (75 min)

*Create an AI/BI Genie space for sensor analytics and build a multi-agent supervisor that combines the Databricks Lakehouse with the Neo4j knowledge graph — two purpose-built systems for two fundamentally different types of data.*

- [Lab 7 - AgentBricks](Lab_7_AgentBricks/README.md) - No-code multi-agent system using Databricks AgentBricks

**Why two data sources?** Aircraft intelligence requires both **time-series telemetry** and **rich relational data**, and each is best served by a purpose-built platform:

- **Genie + Lakehouse** excels at time-series sensor data — 345,600+ hourly readings stored in Delta Lake columnar format, optimized for aggregations, trend analysis, percentile calculations, and fleet-wide statistical comparisons over time. SQL is the natural language for these analytical workloads, and Genie translates natural language into SQL automatically.
- **Neo4j** excels at richly connected relational data — aircraft topology, component hierarchies, maintenance event chains, flight-to-airport routes, and delay root causes. These queries traverse multiple relationships (e.g., "Which components in the hydraulics system had maintenance events that caused flight delays?") and would require expensive multi-table JOINs in a relational database, but Neo4j handles them natively.

The **multi-agent supervisor** routes each question to the right system and, for complex questions spanning both, queries each sequentially and synthesizes a combined answer.

#### Part A: Genie Space for Sensor Analytics (~30 min)
- Create an AI/BI Genie space over sensor telemetry tables in Unity Catalog
- Connect data sources: `sensor_readings`, `sensors`, `systems`, `aircraft`
- Add sample questions and domain-specific instructions (sensor types, normal ranges, fleet info)
- Test natural language to SQL queries for time-series aggregations and anomaly detection

#### Part B: Multi-Agent Supervisor (~45 min)
- Build a supervisor agent that coordinates two specialized sub-agents
- Add the **Neo4j MCP agent** for graph relationship queries (topology, maintenance, flights)
- Add the **Genie space agent** for time-series sensor analytics (readings, trends, fleet comparisons)
- Configure routing rules so the supervisor directs questions to the right agent
- Test single-agent routing and combined multi-agent queries
- Deploy as a serving endpoint for programmatic access

**Agent Architecture:**

```
User Question
     |
     v
Multi-Agent Supervisor
     |
     +---> "sensor readings?" ---> Genie Space ---> Unity Catalog (Lakehouse)
     |        time-series              SQL           aws-databricks-neo4j-lab.lakehouse
     |        aggregations                           345,600+ sensor readings
     |        trend analysis
     |
     +---> "relationships?" ---> Neo4j MCP ---> Knowledge Graph (Aura)
     |        topology               Cypher       8 node types, 13 relationship types
     |        maintenance                         pre-configured admin instance
     |        flights/delays
     |
     +---> "both needed?" ---> Sequential calls to both agents
                               |
                               v
                         Synthesized Response
```

**Routing Examples:**
- **Genie Agent:** Time-series aggregations, sensor anomaly detection, fleet comparisons, trend analysis
- **Neo4j Agent:** Aircraft topology, component hierarchy, maintenance events, flight operations, delays

---

### Phase 5: Neo4j Aura Exploration (60 min)

*Visualize and query the knowledge graph you built in previous labs, then create a no-code AI agent on top of it.*

Open [console.neo4j.io](https://console.neo4j.io), sign in, and select your instance to begin exploring.

#### Part A: Data Exploration in Aura
- [Exploration Guide](Lab_8_Aura_Agents/README.md#part-a-data-exploration-in-aura) — Guided Cypher queries in the Aura Query interface
- Visualize aircraft topology, flight routes, maintenance history, and component removals
- Discover cross-entity patterns like shared faults and delay-prone airports

#### Part B: Build an Aura Agent (No-Code)
- [Lab 8 - Aura Agents](Lab_8_Aura_Agents/README.md) - Create AI-powered graph assistants
- Add **Cypher Template** tools for controlled, precise lookups (e.g., company overview, shared risks)
- Add a **Similarity Search** tool over the vector index for semantic retrieval
- Add a **Text2Cypher** tool for ad-hoc natural language questions
- Test the agent across all three retrieval patterns and observe tool selection reasoning

---

## Knowledge Graph Data Model

The Aircraft Digital Twin graph models the complete operational lifecycle of an aviation fleet.

### Graph Structure

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│ Aircraft │──────>│  System  │──────>│Component │
│          │ HAS_  │          │ HAS_  │          │
│ N95040A  │SYSTEM │ Engine 1 │COMPON │ Turbine  │
└──────────┘       └──────────┘       └──────────┘
     │                  │                  │
     │ OPERATES_        │ HAS_             │ HAS_
     │ FLIGHT           │ SENSOR           │ EVENT
     v                  v                  v
┌──────────┐       ┌──────────┐       ┌──────────┐
│  Flight  │       │  Sensor  │       │Maintenan │
│          │       │          │       │ceEvent   │
│ UA1234   │       │ EGT-001  │       │ Critical │
└──────────┘       └──────────┘       └──────────┘
     │
     │ DEPARTS_FROM / ARRIVES_AT
     v
┌──────────┐
│ Airport  │
│          │
│   ORD    │
└──────────┘
```

### Node Types

| Node Label | Description | Key Properties |
|------------|-------------|----------------|
| `Aircraft` | Fleet inventory | `aircraft_id`, `tail_number`, `model`, `operator` |
| `System` | Major aircraft systems | `system_id`, `type`, `name` |
| `Component` | Parts within systems | `component_id`, `type`, `name` |
| `Sensor` | Monitoring equipment | `sensor_id`, `type`, `unit` |
| `Flight` | Flight operations | `flight_id`, `flight_number`, `origin`, `destination` |
| `Airport` | Route network locations | `airport_id`, `iata`, `icao`, `city` |
| `MaintenanceEvent` | Fault and repair records | `event_id`, `fault`, `severity`, `corrective_action` |
| `Delay` | Flight delay information | `delay_id`, `cause`, `minutes` |
| `Removal` | Component removal history | `removal_id`, `reason`, `tsn`, `csn` |

### Relationship Types

| Relationship | Direction | Description |
|--------------|-----------|-------------|
| `HAS_SYSTEM` | `(Aircraft)->(System)` | Aircraft contains this system |
| `HAS_COMPONENT` | `(System)->(Component)` | System contains this component |
| `HAS_SENSOR` | `(System)->(Sensor)` | System has this sensor |
| `HAS_EVENT` | `(Component)->(MaintenanceEvent)` | Component had this maintenance event |
| `OPERATES_FLIGHT` | `(Aircraft)->(Flight)` | Aircraft operated this flight |
| `DEPARTS_FROM` | `(Flight)->(Airport)` | Flight departs from this airport |
| `ARRIVES_AT` | `(Flight)->(Airport)` | Flight arrives at this airport |
| `HAS_DELAY` | `(Flight)->(Delay)` | Flight had this delay |
| `AFFECTS_SYSTEM` | `(MaintenanceEvent)->(System)` | Event affected this system |
| `HAS_REMOVAL` | `(Aircraft)->(Removal)` | Aircraft had this component removal |

---

## Sample Queries

### Aircraft Topology
```cypher
// What systems does aircraft N95040A have?
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)
RETURN a.tail_number, s.name, s.type
```

### Maintenance Analysis
```cypher
// Find aircraft with critical maintenance events
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)
      -[:HAS_EVENT]->(m:MaintenanceEvent {severity: 'Critical'})
RETURN a.tail_number, s.name, c.name, m.fault, m.reported_at
ORDER BY m.reported_at DESC
```

### Flight Operations
```cypher
// Find delayed flights and their causes
MATCH (a:Aircraft)-[:OPERATES_FLIGHT]->(f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN a.tail_number, f.flight_number, d.cause, d.minutes
ORDER BY d.minutes DESC
LIMIT 10
```

---

## Prerequisites

- **Laptop** with a modern web browser
- **Network Access** to AWS Console, Databricks, and Neo4j Aura
- No local software installation required

---

## Quick Start Options

| Track | Labs | Duration | Description |
|-------|------|----------|-------------|
| **Console Tour Only** | Phases 1-2 | 2 hours | Explore AWS and Neo4j consoles without coding |
| **ETL Focus** | Phases 1-3 | 2.5 hours | Learn Spark Connector and graph data modeling |
| **Multi-Agent Focus** | Phases 1, 3-4 | 3 hours | Build AI agents with Databricks AgentBricks |
| **Full Workshop** | All Phases | 4 hours | Complete hands-on experience |

---

## Resources

- [Neo4j Aura](https://neo4j.com/cloud/aura/)
- [Neo4j Spark Connector](https://neo4j.com/docs/spark/current/)
- [Neo4j MCP Server](https://github.com/neo4j/mcp)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Databricks Agent Bricks](https://docs.databricks.com/en/generative-ai/agent-bricks/)
- [Databricks Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

## Feedback

We'd appreciate your feedback! Open an issue at [github.com/neo4j-partners/aws-databricks-neo4j-lab/issues](https://github.com/neo4j-partners/aws-databricks-neo4j-lab/issues).
