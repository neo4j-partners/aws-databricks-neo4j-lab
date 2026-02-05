# Part B: Multi-Agent Supervisor for Aircraft Intelligence

In this part, you'll create a multi-agent supervisor that intelligently routes questions to either the **Genie space** (for sensor analytics) or the **Neo4j MCP agent** (for graph relationships). This enables natural language queries that span both data sources.

**Estimated Time:** 45 minutes

---

## Prerequisites

Before starting, ensure you have:
- Completed **Part A** (Genie space for sensor analytics)
- Neo4j MCP connection configured in Unity Catalog
- Neo4j database populated with aircraft graph (from Lab 5)
- Access to the Unity Catalog: `aws-databricks-neo4j-lab.lab-schema`

---

## Step 1: Verify Neo4j MCP Connection

### 1.1 Check Unity Catalog Connections

1. In the left navigation pane, click **Catalog**
2. Click **External connections** (or navigate to the **Connections** tab)
3. Locate the Neo4j MCP connection (typically named `neo4j_mcp`)
4. Verify the connection status shows as configured

> **Note:** The MCP connection uses Unity Catalog HTTP connections for secure authentication. Users need `USE CONNECTION` permission to access the MCP server tools.

### 1.2 Verify MCP Tools Are Available

The Neo4j MCP server provides these tools:
- `get-schema`: Retrieves the Neo4j graph schema (labels, relationships, properties)
- `read-cypher`: Executes read-only Cypher queries

You can test these in AI Playground before creating the supervisor:
1. Navigate to **Playground** in the left navigation
2. Select a model with **Tools enabled**
3. Click **Tools** > **+ Add tool** > **MCP Servers**
4. Select your Neo4j connection

---

## Step 2: Create the Multi-Agent Supervisor

### 2.1 Navigate to Agent Bricks

1. In the left navigation pane, click **Agents**
2. Find the **Multi-Agent Supervisor** tile
3. Click **Build**

### 2.2 Configure Basic Settings

1. **Name:** `Aircraft Intelligence Hub [YOUR_INITIALS]`
   - Example: `Aircraft Intelligence Hub RK`
2. **Description:**
   ```
   Intelligent coordinator for aircraft analytics combining sensor telemetry
   data from Unity Catalog with knowledge graph relationships from Neo4j.
   ```

---

## Step 3: Prepare Sub-agents and Permissions

Before adding agents to the supervisor, ensure proper access is configured.

### 3.1 Genie Space Permissions

For the Genie space created in Part A:
1. Navigate to your Genie space
2. Share the space with end users who will query the supervisor
3. Ensure users have access to the underlying data tables in:
   - Catalog: `aws-databricks-neo4j-lab`
   - Schema: `lab-schema`
   - Tables: `sensor_readings`, `sensors`, `systems`, `aircraft`

### 3.2 MCP Server Permissions

For the Neo4j MCP connection:
1. Navigate to **Catalog** > **Connections**
2. Select the Neo4j connection
3. Click **Permissions**
4. Grant `USE CONNECTION` permission to relevant users/groups

---

## Step 4: Add the Neo4j Graph Agent

### 4.1 Add External MCP Server

1. In the supervisor configuration under **Configure Agents**, click **+ Add**
2. From the **Type** dropdown, select **External MCP Server**
3. From the connection dropdown, select your Neo4j connection (e.g., `neo4j_mcp`)

### 4.2 Configure Agent Settings

1. **Agent Name:** `neo4j_graph_agent`
   - The name auto-populates but can be edited
2. **Description** (critical for routing accuracy):

```
Queries the Neo4j knowledge graph to explore aircraft relationships, topology, and operational data.

BEST FOR:
- Aircraft topology: "What systems does aircraft AC1001 have?"
- Component hierarchy: "Show all components in the hydraulics system"
- Maintenance events: "Which aircraft had critical maintenance events?"
- Flight operations: "Find flights delayed due to maintenance"
- Relationship patterns: "Which airports does ExampleAir fly to?"
- Graph traversals: "Show the path from aircraft to sensor"

DATA AVAILABLE (loaded from /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/):
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

## Step 5: Add the Genie Space Agent

### 5.1 Add Genie Space

1. Click **+ Add** to add another agent
2. From the **Type** dropdown, select **Genie Space**
3. Select your Genie space from Part A: `Aircraft Sensor Analyst [YOUR_INITIALS]`

### 5.2 Configure Agent Settings

1. **Agent Name:** `sensor_data_agent`
   - Edit the auto-populated name if needed
2. **Description:**

```
Analyzes aircraft sensor telemetry data using SQL queries over Unity Catalog tables.

DATA LOCATION:
- Catalog: aws-databricks-neo4j-lab
- Schema: lab-schema
- Tables: sensor_readings, sensors, systems, aircraft

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

## Step 6: Configure Supervisor Instructions

### 6.1 Set Supervisor Instructions

In the **Instructions** field (optional but recommended), enter:

```
# Aircraft Intelligence Hub - Routing Instructions

You are an intelligent coordinator for aircraft analytics. Your role is to understand user questions and route them to the appropriate specialized agent.

## Available Agents

### sensor_data_agent (Genie Space - Unity Catalog SQL)
Use for questions about:
- Sensor readings and telemetry data
- Time-series analytics (averages, trends, rolling windows)
- Statistical analysis (percentiles, standard deviation)
- Fleet-wide comparisons of sensor metrics
- Anomaly detection based on readings
- Questions containing: EGT, vibration, N1, fuel flow, temperature, readings, averages, trends

### neo4j_graph_agent (Neo4j Knowledge Graph - Cypher)
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

### 6.2 Create the Agent

Click **Create Agent** to deploy the supervisor.

> **Note:** Deployment may take several minutes to complete. The status will update when ready.

---

## Step 7: Test the Multi-Agent System

### 7.1 Start Testing

Once deployment completes:
1. Use the **Test your Agent** panel on the right side of the Build tab
2. Or click **Open in Playground** for expanded testing with AI Judge features

### 7.2 Test Single-Agent Routing

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

### 7.3 Test Multi-Agent Queries

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

---

## Step 8: Improve Through Feedback

### 8.1 Add Example Questions

1. Navigate to the **Examples** tab
2. Click **+ Add** to introduce test questions
3. Enter questions that represent common user queries

### 8.2 Share with Subject Matter Experts

1. Share the configuration page link with domain experts
2. Grant experts `CAN_MANAGE` permission on the supervisor
3. Ensure experts have appropriate access to each subagent

### 8.3 Add Guidelines

1. Select each example question
2. Add **Guidelines** labels that refine routing behavior
3. Test again to validate improvements
4. Click **Update Agent** to save changes

---

## Step 9: Manage Permissions and Deploy

### 9.1 Configure Permissions

1. Click the kebab menu (three dots) at the top of the agent page
2. Select **Manage permissions**
3. Add users, groups, or service principals
4. Assign permission levels:
   - **Can Manage:** Full editing and permission control
   - **Can Query:** Endpoint access only via Playground or API
5. Click **Add**, then **Save**

### 9.2 Query the Endpoint Programmatically

1. Click **See Agent status** or **Open in Playground**
2. Select **Get code** to retrieve API examples
3. Choose between **Curl API** or **Python API**

Example Python usage:
```python
import requests

# Get your endpoint URL from the agent status page
ENDPOINT_URL = "https://<workspace>.databricks.com/serving-endpoints/<agent-name>/invocations"

headers = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(
    ENDPOINT_URL,
    headers=headers,
    json={"messages": [{"role": "user", "content": "What systems does AC1001 have?"}]}
)
print(response.json())
```

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
     |                                              aws-databricks-neo4j-lab.lab-schema
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

### Data Sources

| Source | Location | Query Language |
|--------|----------|----------------|
| Sensor Telemetry | `aws-databricks-neo4j-lab.lab-schema.sensor_readings` | SQL |
| Aircraft Metadata | `aws-databricks-neo4j-lab.lab-schema.aircraft` | SQL |
| Knowledge Graph | Neo4j Aura (via MCP) | Cypher |
| Graph Data Origin | `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/` | - |

---

## Troubleshooting

### "Agent not responding"
- Check MCP connection status in **Catalog** > **Connections**
- Verify Neo4j instance is running
- Test Genie space independently in AI Playground
- Ensure user has `USE CONNECTION` permission on the MCP connection

### "Wrong agent selected"
- Review and enhance agent descriptions with more specific keywords
- Add explicit routing patterns in supervisor instructions
- Use the Examples tab to add labeled training questions

### "Cypher query failed"
- Check that Neo4j data was loaded correctly (Lab 5)
- Verify node labels and relationship types match documentation
- Review Cypher syntax for errors
- Test queries directly in Neo4j Aura console first

### "SQL query failed"
- Verify table names in Unity Catalog: `aws-databricks-neo4j-lab.lab-schema`
- Check column names match documentation
- Ensure Genie space has access to all required tables
- Test queries directly in SQL Editor first

### "Permission denied"
- For Genie space: User needs access to the space AND underlying data tables
- For MCP server: User needs `USE CONNECTION` permission on the Unity Catalog connection
- For supervisor: User needs `CAN QUERY` permission on the agent endpoint

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

1. **Add Documentation Agent**: Integrate semantic search as a third agent for maintenance procedures

2. **Create Unity Catalog Functions**: Build custom Python functions as additional tools

3. **Production Deployment**: Deploy as a REST API for integration with other systems

4. **Add Guardrails**: Configure output validation and safety filters

5. **Enable Feedback**: Set up user feedback collection for continuous improvement

---

## References

- [Multi-Agent Supervisor Documentation](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [External MCP Servers](https://docs.databricks.com/aws/en/generative-ai/mcp/external-mcp)
- [Agent Bricks Overview](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/)
- [Unity Catalog Connections](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
