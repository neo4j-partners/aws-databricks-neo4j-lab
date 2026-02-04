# Lab 4: AWS AgentCore Overview

In this lab, you will explore AWS Bedrock and AgentCore through a guided console tour, then interact with a pre-deployed AI agent that queries the Aircraft Digital Twin graph in Neo4j.

## Prerequisites

- Completed **Lab 0** (Sign In)
- Completed **Lab 1** (Neo4j Aura setup)

## Overview

This lab provides hands-on experience with AWS AgentCore's managed infrastructure for AI agents. The environment has been pre-configured with:

- **Neo4j MCP Server** deployed to AgentCore (provides Cypher query tools)
- **AgentCore Agent** that calls the MCP server to answer questions about aircraft data

**Architecture:**
```
AgentCore Agent → AgentCore Gateway → Neo4j MCP Server → Neo4j Aura
```

---

## Part A: Read-Only Console Tour

In this section, you will explore the AWS Console to understand how the Neo4j MCP Server and AgentCore Agent have been deployed.

### Step 1: Navigate to AWS Bedrock

1. Sign in to the AWS Console
2. Search for **Bedrock** in the services search bar
3. Click on **Amazon Bedrock** to open the service

### Step 2: Explore AgentCore

1. In the Bedrock console, navigate to **AgentCore** in the left sidebar
2. Review the available sections:
   - **MCP Servers** - View the deployed Neo4j MCP server
   - **Agents** - View the deployed AgentCore agent
   - **Gateway** - Understand how agents connect to MCP servers

### Step 3: View the Neo4j MCP Server

1. Click on **MCP Servers**
2. Find the pre-deployed `neo4j-mcp-server`
3. Review the server configuration:
   - Connection to Neo4j Aura
   - Available Cypher query tools
   - Server status and health

### Step 4: View the AgentCore Agent

1. Click on **Agents**
2. Find the pre-deployed agent that queries the aircraft data
3. Review the agent configuration:
   - System prompt and instructions
   - Connected MCP servers (the Neo4j MCP server)
   - Model configuration

---

## Part B: AgentCore Agent Sandbox Testing

In this section, you will use the AgentCore Agent Sandbox to interactively test the deployed agent without writing any code.

### Step 1: Open the Agent Sandbox

1. Navigate to the agent in the AgentCore console
2. Click on **Test** or **Sandbox** to open the interactive testing interface

### Step 2: Test Aircraft Queries

Send natural language questions about the aircraft digital twin data. Try these example queries:

**Basic Aircraft Information:**
- "List all aircraft in the fleet"
- "What is the status of aircraft N12345?"
- "Show me aircraft by model type"

**Maintenance and Operations:**
- "Which aircraft have pending maintenance?"
- "What sensors are installed on aircraft N12345?"
- "Show me the component hierarchy for a Boeing 737"

**Relationship Queries:**
- "Which operator manages the most aircraft?"
- "Find aircraft with similar maintenance issues"
- "What systems are shared across multiple aircraft models?"

### Step 3: Observe Agent Reasoning

As you test queries, observe:

1. **Tool Selection** - Which MCP tools the agent chooses
2. **Cypher Generation** - The graph queries generated to answer your question
3. **Response Synthesis** - How the agent formats the graph data into natural language

---

## Summary

In this lab, you explored:

| Component | Purpose |
|-----------|---------|
| **AgentCore MCP Server** | Hosts the Neo4j MCP server with Cypher query tools |
| **AgentCore Gateway** | Routes agent requests to MCP servers |
| **AgentCore Agent** | AI agent that uses natural language to query the graph |

The architecture demonstrates how AWS AgentCore provides managed infrastructure for AI agents that can query Neo4j Aura through the Model Context Protocol (MCP).

## Reference Projects

| Project | Link | Purpose |
|---------|------|---------|
| MCP Server | [neo4j-agentcore-mcp-server](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server) | AgentCore MCP server deployment |
| AgentCore Agent | [agentcore-neo4j-mcp-agent](https://github.com/neo4j-partners/aws-starter/tree/main/agentcore-neo4j-mcp-agent) | AI agent deployment |

## Next Steps

Continue to **Lab 5** to work with Databricks and learn how to load data into Neo4j using the Spark Connector.
