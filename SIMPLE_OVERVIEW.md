# Neo4j + AWS + Databricks Lab

This document outlines the plan for a Neo4j + AWS + Databricks Lab, a five-phase hands-on workshop.

## Overview

Participants start by having a guided overview of the AWS Bedrock and AgentCore Console, then work through lab exercises in Databricks and Neo4j Aura for graph exploration. In these workshops AWS Bedrock and AgentCore provide pre-deployed infrastructure.

**Total Duration:** ~4 hours

### Dataset

The workshop uses a comprehensive Aircraft Digital Twin dataset that models a complete aviation fleet over 90 operational days (Aircraft Maintenance Dataset).

### Key Technologies

- Neo4j Aura (Graph Database)
- AWS Bedrock + AgentCore + AgentCore Gateway (Pre-deployed Neo4j MCP Server and AgentCore Agent infrastructure)
- Databricks (Notebooks, Unity Catalog, AI/BI Genie, AgentBricks Multi-Agent Supervisor)
- Neo4j Spark Connector

---

## Lab Structure

### Phase 1: Foundation Setup (45 min)

#### Part A: AWS Console Tour
- Read-only access to view the deployment of the Neo4j MCP Server to AgentCore along with a deployment of an AgentCore Agent that shows how to call the MCP Server

#### Part B: Neo4j Aura Credentials
- Save connection credentials (exploration happens in Phase 5)

---

### Phase 2: AWS - AgentCore Overview + Notebook (60 min)

#### Part A: Read-Only Console Tour
- Walk-through of Bedrock and AgentCore
- View the pre-deployed Neo4j MCP server in AgentCore which showcases AgentCore Gateway + AgentCore MCP Server Hosting
- View the AgentCore agent deployment (which calls the Neo4j MCP server)
- Understand the architecture: `AgentCore Agent → AgentCore Gateway → Neo4j MCP Server in AgentCore → Neo4j Aura`

#### Part B: AgentCore Agent Sandbox Testing (No-Code)
- Use the AgentCore Agent Sandbox in the AWS Console
- Interactively test the deployed agent without writing code
- Send natural language questions about the aircraft data
- See agent reasoning and Cypher query generation in real-time

**Admin Pre-Configuration:**
- Deploy neo4j-agentcore-mcp-server to AgentCore (provides Cypher query tools)
- Deploy agentcore-neo4j-mcp-agent to AgentCore (calls the MCP server to answer questions)

---

### Phase 3: Databricks - ETL to Neo4j (45 min)

**Participant Experience: Pre-Configured Environment**
- CSV files pre-uploaded to Unity Catalog Volume
- Ready-to-run notebook provided - participants clone the sample notebook to run in their workspace

**Data Subset: Aircraft and Operators**
- Aircraft nodes (tail numbers, models, fleet info)
- Operator nodes (airlines, operators)
- Relationships connecting aircraft to their operators

#### Part A: Databricks Workspace Access
- Workspace credentials and cluster access

#### Part B: Data Model Mapping
- Table rows → nodes with labels and properties
- Foreign keys → relationships
- Join tables → direct graph connections

#### Part C: Load Data with Spark Connector
- Read aircraft/operator data from Delta Lake
- Transform to graph structure (nodes + relationships)
- Write to Neo4j via Spark Connector
- Validate with simple Cypher queries

---

### Phase 4: Databricks - Multi-Agent with AgentBricks (60 min)

#### Part A: Databricks Workspace Access
- Workspace credentials and cluster access (if not done in previous section)

#### Part B: Create a Genie Space
- **AI/BI Genie**: Natural language interface for querying structured data in Unity Catalog
- Configure a Genie space with aircraft data tables
- Add sample questions and business context to improve query accuracy
- Genie converts natural language questions into SQL queries automatically

#### Part C: AgentBricks Multi-Agent Supervisor
- **Multi-Agent Supervisor**: No-code framework for building coordinated multi-agent systems
- Supports up to 10 subagents per supervisor
- Question routing based on intent analysis

**Agent Architecture:**
- **Genie Agent:** Queries aircraft data via natural language to SQL (lakehouse data)
- **AWS AgentCore Agent:** Calls Phase 2 AgentCore agent for graph queries (full Neo4j dataset)
- **Supervisor:** Routes questions based on intent—SQL aggregations to Genie, relationship queries to Neo4j

#### Part D: Deployment
- Deploy as serving endpoint

---

### Phase 5: Neo4j Aura - Graph Exploration & Aura Agents (60 min)

**Tools:** Neo4j Aura

#### Part A: Data Explorations in Aura
- Visualize the aircraft digital twin graph
- Aircraft → Systems → Components → Sensors hierarchy
- Operator relationships (loaded in Phase 3)
- Flight patterns and maintenance events
- Understand graph structure that powers Phases 2 and 4

#### Part B: Build an Aura Agent (No-Code)
Neo4j Aura Agents provide a no-code way to build AI-powered assistants that can query your graph database using natural language. Participants will create an agent that helps analyze the aircraft digital twin data.

- Create the Aircraft Analyst Aura Agent
- Add Semantic Search and Cypher Template Tools
- Find Aircraft with Shared Issues

---

## Workshop Automation Options: Per-User Notebook Copies

Since participants share a workspace, each user needs their own copy of notebooks.

| Option | Description |
|--------|-------------|
| **Option 1: Manual Clone** | Participants right-click template notebook → "Clone" |
| **Option 2: Automated Distribution Script** | Review if possible to use Databricks SDK for Python |

---

## Admin Pre-Configuration Checklist

### AWS Setup
- [ ] Deploy neo4j-agentcore-mcp-server to AgentCore (provides Cypher tools)
- [ ] Deploy agentcore-neo4j-mcp-agent to AgentCore (calls the MCP server)
- [ ] Add API Gateway in front of agent with API key authentication
- [ ] Test agent invocation via API Gateway

### Neo4j Setup
- [ ] Provision Neo4j Aura instance
- [ ] Load full aircraft digital twin dataset
- [ ] Verify data with sample queries

### Databricks Setup
- [ ] Upload CSV files to Unity Catalog Volume
- [ ] Create Phase 3 notebook (Spark Connector ETL)
- [ ] Configure cluster with Neo4j Spark Connector library
- [ ] Pre-configure Genie space with aircraft data tables and sample questions
- [ ] Set up AgentBricks Multi-Agent Supervisor template
- [ ] Run notebook distribution script for participants

---

## Reference Projects

| Project | Link | Purpose |
|---------|------|---------|
| MCP Server | [neo4j-agentcore-mcp-server](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server) | AgentCore MCP server deployment |
| AgentCore Agent | [agentcore-neo4j-mcp-agent](https://github.com/neo4j-partners/aws-starter/tree/main/agentcore-neo4j-mcp-agent) | AI agent deployment |
| Databricks Samples | [dbx-aircraft-analyst](https://github.com/neo4j-partners/dbx-aircraft-analyst/tree/main) | Databricks Sample Projects and HTTP connection patterns |
| Aircraft Data | [ARCHITECTURE.md](https://github.com/neo4j-partners/dbx-aircraft-analyst/blob/main/aircraft_digital_twin_data/ARCHITECTURE.md) | Source data and ETL examples |




