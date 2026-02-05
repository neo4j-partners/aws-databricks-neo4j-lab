# Lab 7 - Multi-Agent Aircraft Analytics with AgentBricks

In this lab, you'll build a multi-agent system using Databricks AgentBricks that combines **Genie** (for sensor time-series analytics) with **Neo4j MCP** (for graph relationship queries). This enables natural language questions that span both structured telemetry data and complex relationship traversals.

## Prerequisites

Before starting, make sure you have:
- Completed **Lab 5** (Databricks ETL) to load aircraft topology into Neo4j
- Sensor readings data loaded in your Databricks lakehouse (Unity Catalog)
- Running in a **Databricks workspace** with AgentBricks access
- Neo4j MCP server connection configured in Unity Catalog

## Lab Overview

This lab is documentation-driven and focuses on **configuration over code**. You'll use the Databricks UI to create intelligent agents that automatically route questions to the right data source.

### Part A: Genie Space for Sensor Analytics
Create an AI/BI Genie space that enables natural language queries over sensor telemetry:
- Configure data sources (sensor_readings, sensors, systems, aircraft tables)
- Add sample questions to train the Genie
- Set up domain-specific instructions
- Test time-series aggregations and anomaly detection

### Part B: Multi-Agent Supervisor
Build a supervisor agent that intelligently routes questions:
- Connect to Neo4j MCP for graph queries
- Integrate the Genie space as a sub-agent
- Configure routing rules for different question types
- Test cross-system queries that combine both data sources

## Architecture

```
                    Multi-Agent Supervisor
                  "Aircraft Intelligence Hub"
                            |
            +---------------+---------------+
            |                               |
            v                               v
    Genie Space Agent               Neo4j MCP Agent
    (Sensor Analytics)              (Graph Relationships)
            |                               |
            v                               v
    Unity Catalog                    Neo4j Aura
    Delta Tables                     Knowledge Graph

    - sensor_readings                - Aircraft topology
    - sensors                        - Maintenance events
    - systems                        - Flights & delays
    - aircraft                       - Component hierarchy
```

## Data Model

### Databricks Lakehouse (Time-Series Analytics)

These tables should already be loaded from Lab 5 setup:

| Table | Rows | Description |
|-------|------|-------------|
| `sensor_readings` | 345,600+ | Hourly sensor telemetry (90 days) |
| `sensors` | 160 | Sensor metadata (type, unit, system) |
| `systems` | ~80 | Aircraft systems (engines, avionics, hydraulics) |
| `aircraft` | 20 | Fleet metadata (tail number, model, operator) |

**Sensor Types:**
- **EGT** (Exhaust Gas Temperature): 640-700 C
- **Vibration**: 0.05-0.50 ips
- **N1Speed** (Fan Speed): 4,300-5,200 rpm
- **FuelFlow**: 0.85-1.95 kg/s

### Neo4j Knowledge Graph (Relationships)

From Lab 5 and Lab 6, your graph contains:

| Node Type | Count | Purpose |
|-----------|-------|---------|
| Aircraft | 20 | Fleet inventory |
| System | ~80 | Component hierarchy |
| Component | ~200 | Parts and assemblies |
| Sensor | 160 | Monitoring equipment |
| MaintenanceEvent | 300 | Fault tracking |
| Flight | 800 | Operations |
| Delay | ~300 | Delay causes |
| Airport | 12 | Route network |

## Query Routing Strategy

The supervisor routes questions based on intent:

| Question Type | Route To | Example |
|---------------|----------|---------|
| Time-series aggregations | Genie | "What's the average EGT over the last 30 days?" |
| Statistical analysis | Genie | "Show sensors with readings above 95th percentile" |
| Trend analysis | Genie | "Compare fuel flow rates between 737 and A320" |
| Relationship traversals | Neo4j | "Which components are connected to Engine 1?" |
| Pattern matching | Neo4j | "Find all aircraft with maintenance delays" |
| Topology exploration | Neo4j | "Show the system hierarchy for N95040A" |
| Combined analytics | Both | "Find aircraft with high vibration AND recent maintenance events" |

## Sample Questions

### Genie Agent (Sensor Analytics)
- "What is the average EGT temperature for aircraft N95040A?"
- "Show daily vibration trends for Engine 1 over the last month"
- "Which sensors have readings above their 95th percentile?"
- "Compare fuel flow rates between Boeing and Airbus aircraft"
- "Find the maximum N1 speed recorded across the fleet"

### Neo4j Agent (Graph Relationships)
- "Which systems does aircraft AC1001 have?"
- "Show all maintenance events affecting Engine 1"
- "Find flights that were delayed due to maintenance"
- "What components are in the hydraulics system?"
- "Which aircraft have had critical maintenance events?"

### Multi-Agent (Combined Queries)
- "Find aircraft with high EGT readings and show their recent maintenance history"
- "Which engines have above-average vibration, and what components were recently serviced?"
- "Compare sensor trends for aircraft that had delays versus those that didn't"

## Getting Started

1. **Part A** (~30 min): Create and configure the Genie space for sensor analytics
2. **Part B** (~45 min): Build the multi-agent supervisor with Neo4j integration

## Files

| File | Description |
|------|-------------|
| `README.md` | This overview document |
| `PART_A.md` | Genie Space configuration guide |
| `PART_B.md` | Multi-Agent Supervisor setup guide |

## Key Concepts

- **Genie Space**: AI/BI interface that converts natural language to SQL
- **MCP (Model Context Protocol)**: Standardized protocol for tool integration
- **Multi-Agent Supervisor**: Orchestration layer that routes questions to specialized agents
- **AgentBricks**: Databricks platform for building and deploying AI agents
- **Unity Catalog**: Governance layer for data and connections

## Technical Notes

### Why Two Data Sources?

| System | Strength | Best For |
|--------|----------|----------|
| **Databricks (Genie)** | SQL analytics, aggregations | Time-series queries, statistics |
| **Neo4j (MCP)** | Graph traversals, pattern matching | Relationships, topology |

The multi-agent approach lets users ask questions in natural language without knowing which system to query. The supervisor intelligently routes based on the question's intent.

### Performance Considerations

- **Genie**: Optimized for large-scale aggregations (345K+ readings)
- **Neo4j**: Optimized for relationship hops and pattern matching
- **Supervisor**: Adds minimal latency for routing decisions

## Next Steps

After completing this lab, you can:
- Add more sub-agents (e.g., documentation search from Lab 6)
- Create custom tools for specific maintenance workflows
- Deploy the agent as a production service
- Integrate with external systems via additional MCP servers
