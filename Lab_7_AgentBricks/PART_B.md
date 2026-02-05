# Part B: Multi-Agent Supervisor for Aircraft Intelligence

In this part, you'll create a multi-agent supervisor that intelligently routes questions to either the **Genie space** (for sensor analytics) or the **Neo4j MCP agent** (for graph relationships). This enables natural language queries that span both data sources.

**Estimated Time:** 45 minutes

---

## Prerequisites

Before starting, ensure you have:
- Completed **Part A** (Genie space for sensor analytics)
- Neo4j MCP connection configured in Unity Catalog
- Neo4j database populated with aircraft graph (from Lab 5)

---

## Step 1: Verify Neo4j MCP Connection

### 1.1 Check Unity Catalog Connections

1. Navigate to **Catalog** > **External connections**
2. Locate the Neo4j MCP connection (typically named `neo4j_mcp`)
3. Verify the connection status is **Active**

### 1.2 Test MCP Tools (Optional)

If you have access to test the MCP connection, verify these tools are available:
- `get-schema`: Retrieves the Neo4j graph schema (labels, relationships, properties)
- `read-cypher`: Executes read-only Cypher queries

---

## Step 2: Create the Multi-Agent Supervisor

### 2.1 Navigate to Agent Builder

1. In your Databricks workspace, click **New** > **Agent**
2. Or navigate to **Machine Learning** > **Agents** and click **Create agent**

### 2.2 Select Multi-Agent Template

1. Choose **Multi-Agent Supervisor** as the agent type
2. This template enables routing between multiple sub-agents

### 2.3 Configure Basic Settings

1. **Name:** `Aircraft Intelligence Hub [YOUR_INITIALS]`
   - Example: `Aircraft Intelligence Hub RK`
2. **Description:** "Intelligent coordinator for aircraft analytics combining sensor telemetry data with knowledge graph relationships"
3. Click **Create**

---

## Step 3: Add the Neo4j Graph Agent

### 3.1 Add External MCP Server

1. In the agent configuration, click **Add agent**
2. Select **External MCP Server**
3. Choose the Unity Catalog connection: `neo4j_mcp`

### 3.2 Configure Agent Settings

1. **Agent Name:** `neo4j_graph_agent`
   - Use lowercase with underscores
2. **Select Tools:**
   - [x] `get-schema` - For discovering graph structure
   - [x] `read-cypher` - For executing Cypher queries

### 3.3 Add Agent Description

Enter a detailed description to help the supervisor route correctly:

```
Queries the Neo4j knowledge graph to explore aircraft relationships, topology, and operational data.

BEST FOR:
- Aircraft topology: "What systems does aircraft AC1001 have?"
- Component hierarchy: "Show all components in the hydraulics system"
- Maintenance events: "Which aircraft had critical maintenance events?"
- Flight operations: "Find flights delayed due to maintenance"
- Relationship patterns: "Which airports does ExampleAir fly to?"
- Graph traversals: "Show the path from aircraft to sensor"

DATA AVAILABLE:
- Aircraft (20): Fleet inventory with tail numbers, models, operators
- Systems (~80): Engines, Avionics, Hydraulics per aircraft
- Components (~200): Turbines, Compressors, Pumps, etc.
- Sensors (160): Monitoring equipment metadata
- MaintenanceEvents (300): Faults, severity, corrective actions
- Flights (800): Operations with departure/arrival
- Delays (~300): Delay causes and durations
- Airports (12): Route network locations

RELATIONSHIP TYPES:
- HAS_SYSTEM: Aircraft -> System
- HAS_COMPONENT: System -> Component
- HAS_SENSOR: System -> Sensor
- HAS_EVENT: Component -> MaintenanceEvent
- OPERATES_FLIGHT: Aircraft -> Flight
- DEPARTS_FROM / ARRIVES_AT: Flight -> Airport
- HAS_DELAY: Flight -> Delay

DO NOT USE FOR:
- Time-series sensor readings (use sensor_data_agent instead)
- Statistical aggregations over readings
- Trend analysis or rolling averages
```

---

## Step 4: Add the Genie Space Agent

### 4.1 Add Genie Space

1. Click **Add agent**
2. Select **Genie Space**
3. Choose your Genie space from Part A: `Aircraft Sensor Analyst [YOUR_INITIALS]`

### 4.2 Configure Agent Settings

1. **Agent Name:** `sensor_data_agent`
   - Use lowercase with underscores

### 4.3 Add Agent Description

```
Analyzes aircraft sensor telemetry data using SQL queries over the Unity Catalog lakehouse.

BEST FOR:
- Time-series analytics: "What is the average EGT over the last 30 days?"
- Statistical analysis: "Show sensors above the 95th percentile"
- Trend detection: "Show daily vibration trends for Engine 1"
- Fleet comparisons: "Compare fuel flow between Boeing and Airbus"
- Anomaly detection: "Find EGT readings above 690 degrees"
- Aggregations: "What was the maximum N1 speed recorded?"

DATA AVAILABLE:
- sensor_readings (345,600+ rows): Hourly telemetry over 90 days
- sensors (160 rows): Sensor metadata (type, unit, system)
- systems (~80 rows): Aircraft system information
- aircraft (20 rows): Fleet metadata (model, operator)

SENSOR TYPES:
- EGT: Exhaust Gas Temperature (640-700 C)
- Vibration: Engine vibration (0.05-0.50 ips)
- N1Speed: Fan speed (4,300-5,200 rpm)
- FuelFlow: Fuel consumption (0.85-1.95 kg/s)

DO NOT USE FOR:
- Relationship queries (use neo4j_graph_agent)
- Maintenance event details
- Flight operations or delays
- Component-level fault tracking
```

---

## Step 5: Configure the Supervisor

### 5.1 Set Supervisor Instructions

Click **Edit supervisor instructions** and enter:

```
# Aircraft Intelligence Hub - Routing Instructions

You are an intelligent coordinator for aircraft analytics. Your role is to understand user questions and route them to the appropriate specialized agent.

## Available Agents

### sensor_data_agent (Genie Space)
Use for questions about:
- Sensor readings and telemetry data
- Time-series analytics (averages, trends, rolling windows)
- Statistical analysis (percentiles, standard deviation)
- Fleet-wide comparisons of sensor metrics
- Anomaly detection based on readings
- Questions containing: EGT, vibration, N1, fuel flow, temperature, readings, averages, trends

### neo4j_graph_agent (Knowledge Graph)
Use for questions about:
- Aircraft structure and topology
- Component relationships and hierarchy
- Maintenance events and fault history
- Flight operations, routes, delays
- "Which", "what systems", "connected to", "related to" questions
- Questions about maintenance, flights, delays, airports

## Routing Rules

1. **Sensor values/readings** -> sensor_data_agent
   - "What is the EGT for..."
   - "Show vibration readings..."
   - "Average fuel flow..."

2. **Relationships/structure** -> neo4j_graph_agent
   - "What systems does aircraft X have?"
   - "Which components..."
   - "Show maintenance events..."

3. **Flights/operations** -> neo4j_graph_agent
   - "Which flights were delayed?"
   - "What airports does..."
   - "Show flight routes..."

4. **Maintenance history** -> neo4j_graph_agent
   - "What maintenance events..."
   - "Which components had faults?"
   - "Critical maintenance..."

5. **Statistical aggregations on readings** -> sensor_data_agent
   - "Average", "maximum", "minimum", "percentile"
   - "Trend", "over time", "daily", "monthly"
   - "Compare", "between", "by model"

## Complex Queries (Multi-Agent)

For questions that need BOTH sources, process sequentially:

1. **"Find aircraft with high vibration AND recent maintenance"**
   - First: sensor_data_agent -> Get aircraft with high vibration
   - Then: neo4j_graph_agent -> Get maintenance events for those aircraft

2. **"Which engines have abnormal EGT and what components were serviced?"**
   - First: sensor_data_agent -> Find abnormal EGT readings
   - Then: neo4j_graph_agent -> Find maintenance events for those engines

3. **"Compare sensor trends for aircraft that had delays"**
   - First: neo4j_graph_agent -> Get aircraft with delays
   - Then: sensor_data_agent -> Get sensor trends for those aircraft

## Response Guidelines

1. For single-agent queries: Return the agent's response directly
2. For multi-agent queries: Synthesize a combined response that integrates both perspectives
3. Always cite which data source provided each piece of information
4. If a query cannot be answered by either agent, explain what data would be needed
```

---

## Step 6: Test the Multi-Agent System

### 6.1 Start a Conversation

Click **Start conversation** or navigate to the chat interface.

### 6.2 Test Single-Agent Routing

**Test 1: Sensor Analytics (should route to sensor_data_agent)**
```
What is the average EGT temperature across the fleet?
```
Verify: The query is routed to sensor_data_agent and returns a numerical average

**Test 2: Graph Relationships (should route to neo4j_graph_agent)**
```
What systems does aircraft AC1001 have?
```
Verify: The query is routed to neo4j_graph_agent and returns engine, avionics, hydraulics systems

**Test 3: Maintenance Events (should route to neo4j_graph_agent)**
```
Show me all critical maintenance events in the last month
```
Verify: Returns maintenance events with severity=CRITICAL

**Test 4: Fleet Comparison (should route to sensor_data_agent)**
```
Compare average vibration readings between Boeing and Airbus aircraft
```
Verify: Returns grouped statistics by manufacturer

### 6.3 Test Multi-Agent Queries

**Test 5: Combined Query**
```
Find aircraft with EGT readings above 680 degrees and show their maintenance history
```
Expected behavior:
1. Supervisor routes to sensor_data_agent for high EGT aircraft
2. Supervisor routes to neo4j_graph_agent for maintenance history
3. Response synthesizes both data sources

**Test 6: Another Combined Query**
```
Which engines had above-average vibration, and what components were recently serviced on those engines?
```
Expected behavior:
1. Get high-vibration engines from sensor_data_agent
2. Get maintenance events from neo4j_graph_agent
3. Combine and present results

### 6.4 Monitor Agent Invocations

Click **View details** or **Monitoring** to see:
- Which agent was invoked for each query
- The actual queries/Cypher executed
- Response times and token usage

---

## Step 7: Refine Routing

### 7.1 Identify Routing Failures

Common issues to watch for:
- Sensor questions routed to Neo4j (no readings there)
- Relationship questions routed to Genie (can't traverse graphs)
- Ambiguous questions routed incorrectly

### 7.2 Update Agent Descriptions

If routing is incorrect, enhance agent descriptions with:
- More specific keywords that trigger each agent
- Additional "BEST FOR" examples
- Clearer "DO NOT USE FOR" boundaries

### 7.3 Add Routing Examples to Supervisor

If specific query patterns fail, add explicit routing rules:

```
# Additional Routing Patterns

- "EGT" -> sensor_data_agent (always about readings)
- "maintenance" -> neo4j_graph_agent (always about events)
- "between X and Y" comparisons -> sensor_data_agent (aggregations)
- "connected to" -> neo4j_graph_agent (relationships)
```

---

## Step 8: Save and Deploy

### 8.1 Save Configuration

Click **Save** to preserve your multi-agent configuration.

### 8.2 Optional: Deploy as Endpoint

For production use, you can deploy the agent as a REST endpoint:

1. Click **Deploy**
2. Select endpoint configuration (serverless or provisioned)
3. Configure authentication
4. Deploy and note the endpoint URL

---

## Summary

You've created a multi-agent system that:

- **Routes intelligently** between sensor analytics and graph queries
- **Combines data sources** for complex questions
- **Uses natural language** without requiring SQL or Cypher knowledge
- **Leverages strengths** of each underlying system

### Architecture Recap

```
User Question
     |
     v
Multi-Agent Supervisor
     |
     +---> "sensor readings?" ---> Genie Space ---> Unity Catalog
     |                                              (SQL Analytics)
     |
     +---> "relationships?" ---> Neo4j MCP ---> Knowledge Graph
     |                                          (Cypher Queries)
     |
     +---> "both needed?" ---> Sequential calls to both agents
                               |
                               v
                         Synthesized Response
```

---

## Troubleshooting

### "Agent not responding"
- Check MCP connection status in Unity Catalog
- Verify Neo4j instance is running
- Test Genie space independently

### "Wrong agent selected"
- Review and enhance agent descriptions
- Add more specific routing keywords
- Use explicit routing patterns in supervisor instructions

### "Cypher query failed"
- Check that Neo4j data was loaded correctly (Lab 5)
- Verify node labels and relationship types match documentation
- Review Cypher syntax for errors

### "SQL query failed"
- Verify table names in Unity Catalog
- Check column names match documentation
- Ensure Genie has access to all required tables

---

## Sample Queries Reference

### Sensor Analytics (sensor_data_agent)
```
What is the average EGT temperature for aircraft N95040A?
Show daily vibration trends for Engine 1 in August 2024
Find all sensors with readings above the 95th percentile
Compare fuel flow rates by aircraft model
What was the maximum N1 speed recorded?
```

### Graph Queries (neo4j_graph_agent)
```
What systems does aircraft AC1001 have?
Show all components in the hydraulics system
Which aircraft had critical maintenance events?
Find flights that were delayed due to maintenance
What airports are in the route network?
```

### Combined Queries (both agents)
```
Find aircraft with high EGT and show their recent maintenance
Which engines have abnormal vibration and what was serviced?
Compare sensor trends for aircraft that had delays vs. those that didn't
Show maintenance events for aircraft with the lowest fuel efficiency
```

---

## Next Steps

Congratulations! You've built a complete multi-agent system for aircraft intelligence. Consider these extensions:

1. **Add Documentation Agent**: Integrate the semantic search from Lab 6 as a third agent for maintenance procedures

2. **Create Custom Tools**: Build specialized tools for common workflows (e.g., "Generate Maintenance Report")

3. **Production Deployment**: Deploy as a REST API for integration with other systems

4. **Add Guardrails**: Configure output validation and safety filters

5. **Enable Feedback**: Set up user feedback collection for continuous improvement
