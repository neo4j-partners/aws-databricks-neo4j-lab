# Neo4j + AWS + Databricks Hands-On Lab, 2026

## Program Name

Build AI Agents with Neo4j, AWS AgentCore, and Databricks AgentBricks

## Workshop Overview

This workshop equips participants with practical skills to combine Neo4j's graph database platform with AWS Bedrock/AgentCore and Databricks AgentBricks to build multi-agent AI applications using pre-deployed infrastructure and no-code tools.

Participants will work with a real-world dataset—an Aircraft Digital Twin that models a complete aviation fleet over 90 operational days—to experience how knowledge graphs power AI agents for maintenance analysis, pattern detection, and operational insights.

Through a series of guided exercises, attendees will:

- Explore AWS Bedrock and AgentCore Console with pre-deployed Neo4j MCP infrastructure
- Test AI agents interactively using the AgentCore Agent Sandbox
- Understand graph data models and the Aircraft → Systems → Components → Sensors hierarchy
- Load data from Databricks to Neo4j using the Spark Connector
- Build a Databricks AI/BI Genie space for natural language SQL queries
- Build multi-agent systems with AgentBricks Multi-Agent Supervisor coordinating Genie and AWS AgentCore
- Create no-code AI agents with Neo4j Aura Agents

**Total Duration:** ~4 hours

---

## Key Technologies

- **Neo4j Aura** – Fully managed cloud graph database
- **AWS Bedrock + AgentCore + AgentCore Gateway** – Pre-deployed Neo4j MCP Server and AgentCore Agent infrastructure
- **Databricks AI/BI Genie** – Natural language to SQL interface for Unity Catalog data
- **Databricks AgentBricks** – No-code Multi-Agent Supervisor for coordinating specialized agents
- **Neo4j Spark Connector** – ETL bridge between Databricks and Neo4j

---

## Lab Agenda

### Phase 1 – Foundation Setup (45 min)

#### Overview

Get oriented with the workshop environment by touring the AWS Console to understand the pre-deployed infrastructure, then save your Neo4j Aura credentials for use in later phases.

#### Labs

- **Lab 1A – AWS Console Tour**: Read-only access to view the deployment of the Neo4j MCP Server to AgentCore along with a deployment of an AgentCore Agent that shows how to call the MCP Server
- **Lab 1B – Neo4j Aura Credentials**: Save connection credentials for graph exploration in Phase 5

---

### Phase 2 – AWS AgentCore Overview + Testing (60 min)

#### Overview

Take a guided walk-through of AWS Bedrock and AgentCore, examining the pre-deployed Neo4j MCP server and AgentCore agent. Then use the AgentCore Agent Sandbox to interactively test the agent without writing any code.

#### Lecture — AWS AgentCore Architecture

- AWS Bedrock and AgentCore: Managed infrastructure for AI agents
- AgentCore Gateway: Secure routing to MCP servers
- Neo4j MCP Server: Providing Cypher query tools to agents
- Architecture Flow: `AgentCore Agent → AgentCore Gateway → Neo4j MCP Server → Neo4j Aura`

#### Labs

- **Lab 2A – Console Tour**: View the pre-deployed Neo4j MCP server showcasing AgentCore Gateway + AgentCore MCP Server Hosting; view the AgentCore agent deployment that calls the Neo4j MCP server
- **Lab 2B – Agent Sandbox Testing (No-Code)**: Use the AgentCore Agent Sandbox in the AWS Console to interactively test the deployed agent, send natural language questions about the aircraft data, and observe agent reasoning and Cypher query generation in real-time

---

### Phase 3 – Databricks ETL to Neo4j (45 min)

#### Overview

Learn the fundamentals of loading data from Databricks to Neo4j using the Spark Connector. This section covers how graph data pipelines work and prepares data for the multi-agent system in Phase 4.

#### Lecture — Graph Data Modeling

- Data Model Mapping: Table rows → nodes with labels and properties
- Relationship Modeling: Foreign keys → relationships, join tables → direct graph connections
- Neo4j Spark Connector: Reading from Delta Lake and writing to Neo4j

#### Participant Environment

- CSV files pre-uploaded to Unity Catalog Volume
- Ready-to-run notebook provided (participants clone the sample notebook)
- Data Subset: Aircraft nodes (tail numbers, models, fleet info), Operator nodes (airlines), and relationships

#### Labs

- **Lab 3A – Databricks Workspace Access**: Obtain workspace credentials and cluster access
- **Lab 3B – Data Model Mapping**: Understand how tabular data transforms to graph structure
- **Lab 3C – Load Data with Spark Connector**: Read aircraft/operator data from Delta Lake, transform to graph structure (nodes + relationships), write to Neo4j via Spark Connector, and validate with simple Cypher queries

---

### Phase 4 – Databricks Multi-Agent with AgentBricks (60 min)

#### Overview

Build a multi-agent system using Databricks AgentBricks and AI/BI Genie. Create a Multi-Agent Supervisor that routes queries between a Genie space (for SQL-based lakehouse queries) and the AWS AgentCore agent (for Neo4j graph queries).

#### Lecture — Databricks AI/BI Genie

- **What is Genie**: Natural language interface for querying structured data in Unity Catalog
- **Natural Language to SQL**: Converts user questions into SQL queries automatically
- **Genie Spaces**: Configured workspaces with selected tables, sample questions, and business context
- **Stateful Conversations**: Supports follow-up questions and multi-turn dialogue

#### Lecture — AgentBricks Multi-Agent Supervisor

- **Multi-Agent Supervisor**: No-code framework for building coordinated multi-agent systems
- **Question Routing**: Analyzes intent and routes to the appropriate specialized agent
- **Supported Agent Types**: Genie Spaces, External MCP Servers, Unity Catalog Functions
- **Response Synthesis**: Combines insights from multiple data sources into coherent answers
- **Scalability**: Supports up to 10 subagents per supervisor

#### Labs

- **Lab 4A – Databricks Workspace Access**: Obtain workspace credentials and cluster access (if not done in Phase 3)
- **Lab 4B – Create a Genie Space**: Configure a Genie space for natural language SQL queries against aircraft data in Unity Catalog; add sample questions and business context to improve query accuracy
- **Lab 4C – AgentBricks Multi-Agent Supervisor**: Build a multi-agent system using the AgentBricks visual interface:
  - **Genie Agent:** Queries aircraft data via natural language to SQL (lakehouse data)
  - **AWS AgentCore Agent:** Calls Phase 2 AgentCore agent for graph queries (full Neo4j dataset)
  - **Supervisor:** Routes questions based on intent—SQL aggregations to Genie, relationship queries to Neo4j
- **Lab 4D – Deployment**: Deploy the multi-agent system as a serving endpoint

---

### Phase 5 – Neo4j Aura Graph Exploration & Aura Agents (60 min)

#### Overview

Explore the aircraft digital twin graph visually in Neo4j Aura, understanding the data structure that powers the AI agents from earlier phases. Then build your own no-code Aura Agent to analyze the aircraft data.

#### Lecture — Neo4j Aura and Aura Agents

- Neo4j Aura: Fully managed, cloud-native graph database platform
- Graph Visualization: Exploring complex relationships visually
- Aura Agents: Build, test, and deploy AI agents grounded in your graph data without writing code

#### Labs

- **Lab 5A – Data Exploration in Aura**: Visualize the aircraft digital twin graph including Aircraft → Systems → Components → Sensors hierarchy, operator relationships (loaded in Phase 3), and flight patterns and maintenance events; understand the graph structure that powers Phases 2 and 4
- **Lab 5B – Build an Aura Agent (No-Code)**: Create the Aircraft Analyst Aura Agent, add Semantic Search and Cypher Template Tools, and build queries to find aircraft with shared issues
