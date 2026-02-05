# Lab 4: AWS Bedrock AgentCore Overview

In this lab, you will explore Amazon Bedrock and AgentCore through a guided console tour, then interact with a pre-deployed multi-agent orchestrator that queries the Aircraft Digital Twin graph in Neo4j.

## Prerequisites

- Completed **Lab 0** (Sign In)
- Completed **Lab 1** (Neo4j Aura setup)

## Overview

### What is Amazon Bedrock?

[Amazon Bedrock](https://aws.amazon.com/bedrock/) is a fully managed service that provides access to high-performing foundation models (FMs) from leading AI companies through a single API. Bedrock enables you to build generative AI applications with security, privacy, and responsible AI built in.

### What is Amazon Bedrock AgentCore?

[Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) is an agentic platform for building, deploying, and operating AI agents securely at scale -- without managing infrastructure. AgentCore provides the building blocks for production-grade agents:

| Service | Description |
|---------|-------------|
| **Runtime** | Secure, serverless runtime for deploying and scaling AI agents and tools. Supports low-latency conversations up to 8-hour asynchronous workloads with complete session isolation. Deployable with code upload or containers. |
| **Gateway** | Convert APIs, Lambda functions, and existing services into MCP-compatible tools. Connect to pre-existing MCP servers and enable intelligent tool discovery through semantic search. |
| **Memory** | Controls how agents remember and learn. Maintains context across interactions with short-term (multi-turn) and long-term (cross-session) memory that improves performance over time. |
| **Identity** | Secure agent identity and access management compatible with existing identity providers. Enables agents to access AWS resources and third-party services on behalf of users. |
| **Observability** | Powered by Amazon CloudWatch and OpenTelemetry, provides tracing, debugging, and monitoring of agent performance with detailed visualizations of each workflow step. |
| **Code Interpreter** | Isolated sandbox environments for agents to write and execute code (Python, JavaScript, TypeScript) for complex end-to-end tasks. |
| **Browser** | Secure cloud-based browser runtime enabling AI agents to interact with web applications, fill forms, navigate websites, and extract information. Auto-scales from zero to hundreds of sessions. |
| **Evaluations** *(Preview)* | Automated, consistent agent assessment measuring task execution, edge case handling, and output reliability across diverse inputs and contexts. |
| **Policy** *(Preview)* | Deterministic control ensuring agents operate within defined boundaries and business rules. Author fine-grained rules using natural language or Cedar policy language. |

### What is the Model Context Protocol (MCP)?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open standard that provides a universal way for AI agents to connect to tools and data sources. Instead of building custom integrations for every tool, agents use MCP to discover and invoke tools through a consistent interface.

AgentCore Runtime supports hosting MCP servers as stateless streamable-HTTP endpoints, making them available to any MCP-compatible agent or client.

---

## Pre-Deployed Architecture

This lab environment has been pre-configured with two components deployed to AgentCore:

1. **Neo4j MCP Server** -- exposes the Aircraft Digital Twin graph as MCP tools
2. **Multi-Agent Orchestrator** -- routes natural language questions to specialist agents that call those tools

```
                    ┌─────────────────────────────────────────────┐
                    │          AgentCore Agent (Orchestrator)      │
                    │                                             │
                    │  ┌──────────┐                               │
User Question ────> │  │  Router  │                               │
                    │  │  Node    │                               │
                    │  └────┬─────┘                               │
                    │       │                                     │
                    │  ┌────▼──────────┐    ┌──────────────────┐  │
                    │  │  Maintenance  │    │   Operations     │  │
                    │  │  Agent        │    │   Agent          │  │
                    │  └───────────────┘    └──────────────────┘  │
                    └──────────────┬───────────────────────────────┘
                                  │ OAuth2 + Streamable HTTP
                                  ▼
                    ┌──────────────────────────┐
                    │    AgentCore Gateway      │
                    └─────────────┬────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │    Neo4j MCP Server       │
                    │  (Cypher query tools)     │
                    └─────────────┬────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │      Neo4j Aura           │
                    │  (Aircraft Digital Twin)  │
                    └──────────────────────────┘
```

---

## Part A: Neo4j MCP Server Console Tour

In this section, you will explore the Neo4j MCP Server -- the foundational component that makes the graph database accessible to AI agents via the Model Context Protocol.

### Step 1: Navigate to Amazon Bedrock

1. Sign in to the AWS Console
2. Search for **Bedrock** in the services search bar
3. Click on **Amazon Bedrock** to open the service
4. In the Bedrock console, navigate to **AgentCore** in the left sidebar

### Step 2: View the Neo4j MCP Server Runtime

The Neo4j MCP Server is deployed to AgentCore Runtime as a stateless streamable-HTTP container. It wraps a Neo4j database with the Model Context Protocol, exposing read-only Cypher query tools.

1. Click on **Runtime**
2. Find the pre-deployed `neo4j-mcp-server`
3. Review the runtime configuration:
   - **Container**: ARM64 Docker image running the Neo4j MCP server on port 8000
   - **Transport**: Stateless streamable-HTTP at the `/mcp` endpoint
   - **Mode**: Read-only (`NEO4J_READ_ONLY=true`)
   - **Status and health**: Server health and invocation metrics

### Step 3: Understand the MCP Tools

The MCP server exposes two read-only tools that any MCP-compatible agent can discover and invoke:

| Tool | Description |
|------|-------------|
| `get-schema` | Returns the Neo4j database schema (node labels, relationship types, properties) |
| `read-cypher` | Executes a read-only Cypher query and returns the results |

When accessed through the AgentCore Gateway, tool names are prefixed with the target name (e.g., `neo4j-mcp-server-target___read-cypher`).

### Step 4: View the AgentCore Gateway

The Gateway connects agents to the MCP server and handles authentication, routing, and tool discovery.

1. Click on **Gateway**
2. Review how the Gateway is configured:
   - **Target**: The Neo4j MCP Server runtime
   - **Authentication**: JWT Authorizer validating Cognito tokens
   - **Tool discovery**: Agents discover available Cypher tools via the MCP `list_tools` operation

### Step 5: Understand the Authentication Setup

The MCP server uses M2M (machine-to-machine) OAuth2 via Amazon Cognito -- no user accounts are needed.

1. The CDK stack created a **Cognito User Pool** with a resource server and machine client
2. Agents request an access token using the **client credentials** grant
3. The Gateway validates the **JWT bearer token** before forwarding requests to the Runtime
4. The Gateway uses an **OAuth Credential Provider** to exchange credentials for Runtime access

### Step 6: Review the MCP Server Deployment

The MCP server was deployed as an AWS CDK stack that provisioned the full infrastructure in a single command:

```
┌─────────────────────────────────────────────────────────────┐
│                     CDK Stack Creates:                       │
│                                                             │
│  Amazon Cognito          AgentCore Runtime    AgentCore     │
│  ┌────────────────┐      ┌────────────────┐  Gateway       │
│  │ User Pool       │      │ Neo4j MCP      │  ┌───────────┐│
│  │ Resource Server │      │ Server         │  │ JWT Auth   ││
│  │ Machine Client  │      │ (ARM64 Docker) │  │ Tool Route ││
│  └────────────────┘      └────────────────┘  └───────────┘│
│                                                             │
│  Custom Resource Lambdas:                                   │
│  - OAuth Credential Provider (Gateway ↔ Runtime auth)      │
│  - Runtime Health Check (waits for container ready)         │
└─────────────────────────────────────────────────────────────┘
```

**Key characteristics:**
- **Read-only mode** -- only `get-schema` and `read-cypher` tools are exposed (no writes)
- **M2M OAuth2 authentication** -- machine-to-machine only, no user accounts needed
- **Automated deployment** -- single `./deploy.sh` command handles Docker build, ECR push, and CDK deploy
- **Credential generation** -- produces the `.mcp-credentials.json` file used by the orchestrator agent

The MCP server source code lives in a [separate repository](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server). For admin deployment details, see the [setup/README.md](setup/README.md#neo4j-mcp-server-prerequisite).

---

## Part B: AgentCore Agent Console Tour and Sandbox Testing

In this section, you will explore the multi-agent orchestrator and then test it interactively.

### Step 1: View the AgentCore Agent

The orchestrator agent is deployed to AgentCore Runtime as a containerized Python application. It uses LangGraph for multi-agent orchestration and LangChain for LLM interaction.

1. In the AgentCore console, click on **Runtime**
2. Find the pre-deployed multi-agent orchestrator
3. Review the agent configuration:
   - **Model**: Claude Sonnet 4 via Amazon Bedrock Converse API
   - **Framework**: LangGraph StateGraph with conditional routing
   - **Connected MCP servers**: The Neo4j MCP server (via Gateway)
   - **Authentication**: OAuth2 client credentials flow with automatic token refresh
   - **Observability**: AWS OpenTelemetry integration for tracing to CloudWatch

**How the orchestrator works:**

1. The **Router Node** uses Claude to classify each question as either a "maintenance" or "operations" query
2. The query is routed to the appropriate **specialist agent** (Maintenance or Operations)
3. The specialist agent uses **MCP tools** (via the AgentCore Gateway) to generate and execute Cypher queries against Neo4j
4. The agent synthesizes the graph results into a natural language response

| Agent | Domain | Example Topics |
|-------|--------|----------------|
| **Maintenance Agent** | Aircraft health and reliability | Fault codes, component failures, sensor readings, hydraulic/engine systems, severity levels |
| **Operations Agent** | Flight operations and performance | Flight delays, route analysis, airport traffic, airline performance, on-time metrics |

> For full details on how this agent is built, configured, and deployed to AgentCore, see the [setup/README.md](setup/README.md).

### Step 2: Open the Agent Sandbox

1. Navigate to the orchestrator agent in the AgentCore console
2. Click on **Test** or **Sandbox** to open the interactive testing interface

### Step 3: Test Maintenance Queries

The Maintenance Agent handles questions about aircraft health, component reliability, and system diagnostics. Try these queries:

- "What are the most common maintenance faults in the fleet?"
- "Show me critical severity maintenance events"
- "Which components have the highest failure rates?"
- "What are the recent hydraulic system issues?"
- "Show me sensor readings for engine temperature"
- "What is the reliability history for avionics components?"

### Step 4: Test Operations Queries

The Operations Agent handles questions about flights, delays, routes, and airline performance. Try these queries:

- "What are the top causes of flight delays?"
- "Which routes have the most delays?"
- "Show me airline on-time performance rankings"
- "What are the busiest airports by traffic volume?"
- "Which carriers operate the most flights?"
- "Show me average scheduled duration for routes from JFK"

### Step 5: Observe Agent Reasoning

As you test queries, observe how the multi-agent system works:

1. **Query Classification** - The Router Node analyzes your question and classifies it as "maintenance" or "operations"
2. **Agent Selection** - The query is routed to the appropriate specialist agent
3. **Tool Selection** - The specialist agent selects the right MCP tools (Cypher read/write)
4. **Cypher Generation** - The agent generates a graph query based on the domain schema
5. **Response Synthesis** - Graph results are formatted into a natural language answer

### Step 6: Test Edge Cases

Try queries that span both domains or are ambiguous to see how the router handles them:

- "How many aircraft are in the fleet?" (general -- routes to Operations)
- "What is the graph schema?" (general -- routes to Operations)
- "Show me aircraft with both maintenance issues and flight delays" (ambiguous)

---

## Summary

In this lab, you explored:

| Component | Purpose |
|-----------|---------|
| **Amazon Bedrock** | Managed service for foundation models, providing the Claude Sonnet 4 LLM |
| **AgentCore Runtime** | Serverless deployment for both the MCP server and the multi-agent orchestrator |
| **AgentCore Gateway** | Secure routing layer connecting the agent to the Neo4j MCP server with OAuth2 |
| **Neo4j MCP Server** | Stateless HTTP server exposing Cypher query tools via the Model Context Protocol |
| **Multi-Agent Orchestrator** | LangGraph-based router that delegates to Maintenance and Operations specialist agents |

This architecture demonstrates how Amazon Bedrock AgentCore provides managed infrastructure for deploying production AI agents that query Neo4j Aura through MCP -- with built-in authentication, observability, and session management.

## Reference Projects

| Project | Link | Purpose |
|---------|------|---------|
| MCP Server | [neo4j-agentcore-mcp-server](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server) | AgentCore MCP server deployment |
| AgentCore Agent | [agentcore-neo4j-mcp-agent](https://github.com/neo4j-partners/aws-starter/tree/main/agentcore-neo4j-mcp-agent) | Multi-agent orchestrator source |
| Setup Code | [setup/](setup/) | Pre-deployment code and scripts (see [setup/README.md](setup/README.md)) |
| AWS AgentCore Docs | [AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/) | Official AWS documentation |
| AgentCore Samples | [amazon-bedrock-agentcore-samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) | Official AWS AgentCore examples |

## Next Steps

Continue to **Lab 5** to work with Databricks and learn how to load data into Neo4j using the Spark Connector.
