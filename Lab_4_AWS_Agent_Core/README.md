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

> **Important:** Make sure your AWS Console is set to the **US West (Oregon) / `us-west-2`** region. You can verify this in the region selector at the top-right of the console. All AgentCore resources for this lab are deployed in `us-west-2`.

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
3. **Tool Selection** - The specialist agent selects the right MCP tools (`get-schema` and `read-cypher`)
4. **Cypher Generation** - The agent generates a graph query based on the domain schema
5. **Response Synthesis** - Graph results are formatted into a natural language answer

### Step 6: Test Edge Cases

Try queries that span both domains or are ambiguous to see how the router handles them:

- "How many aircraft are in the fleet?" (general -- routes to Operations)
- "What is the graph schema?" (general -- routes to Operations)
- "Show me aircraft with both maintenance issues and flight delays" (ambiguous)

---

## Part C: Deep Dive -- How the Agent Orchestration Works

This section walks through the orchestrator source code in [`setup/`](setup/) to show exactly how the multi-agent system is built.

### The LangGraph StateGraph

The orchestrator is a [LangGraph](https://langchain-ai.github.io/langgraph/) `StateGraph` -- a directed graph where each node is a function and edges define the execution flow. The state that flows through the graph carries the conversation messages and a routing decision:

```python
from langgraph.graph import StateGraph, START, END

class OrchestratorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: str  # "maintenance" or "operations"
```

The graph is assembled with three nodes and conditional routing:

```python
graph = StateGraph(OrchestratorState)

# Three nodes: one router, two specialists
graph.add_node("router", create_router_node(llm))
graph.add_node("maintenance", create_maintenance_node(llm, tools))
graph.add_node("operations", create_operations_node(llm, tools))

# Every query starts at the router
graph.add_edge(START, "router")

# Router decides which specialist handles the query
graph.add_conditional_edges(
    "router",
    route_to_agent,  # reads state["next_agent"]
    {"maintenance": "maintenance", "operations": "operations"}
)

# Both specialists go to END after responding
graph.add_edge("maintenance", END)
graph.add_edge("operations", END)
```

This produces the following execution graph:

```
            START
              │
              ▼
          ┌────────┐
          │ Router │  ← Classifies query domain
          └───┬────┘
              │
     ┌────────┴────────┐
     │ next_agent=?     │
     ▼                  ▼
┌────────────┐   ┌────────────┐
│Maintenance │   │ Operations │  ← ReAct agents with MCP tools
│   Agent    │   │   Agent    │
└─────┬──────┘   └─────┬──────┘
      │                │
      └───────┬────────┘
              ▼
             END
```

### Router Node: Query Classification

The router is a lightweight LLM call that classifies each question into one of two domains. It uses keyword hints to guide the classification:

```python
ROUTER_PROMPT = """You are a query router for an aviation fleet management system.

Analyze the user's question and determine which specialist should handle it.

MAINTENANCE keywords: maintenance, fault, failure, component, system,
    reliability, sensor, reading, repair, hydraulic, engine, avionics,
    critical, severity
OPERATIONS keywords: flight, delay, route, airport, operator, schedule,
    departure, arrival, on-time, airline, carrier

Respond with ONLY one word: either "maintenance" or "operations"

If the query is ambiguous or general (like "schema" or "count"),
respond with "operations"."""
```

The router extracts the latest user message, sends it to Claude with this system prompt, and sets `state["next_agent"]` to the single-word response. The conditional edge function then routes accordingly:

```python
def route_to_agent(state: OrchestratorState) -> Literal["maintenance", "operations"]:
    return state["next_agent"]
```

**Why keyword-based routing?** This approach is fast (a single, short LLM call with `temperature=0`), deterministic, and inexpensive. The router does not need tools or multi-step reasoning -- it only needs to read the question and pick a domain.

### Specialist Agents: The ReAct Pattern

Each specialist is a [ReAct](https://arxiv.org/abs/2210.03629) (Reasoning + Acting) agent created with LangGraph's `create_react_agent`. ReAct agents work in a loop:

```
┌──────────────────────────────────────────────────┐
│                 ReAct Agent Loop                  │
│                                                  │
│  1. REASON  ─── Think about what to do next      │
│       │                                          │
│       ▼                                          │
│  2. ACT     ─── Call an MCP tool (Cypher query)  │
│       │                                          │
│       ▼                                          │
│  3. OBSERVE ─── Read the tool results            │
│       │                                          │
│       ▼                                          │
│  4. DECIDE  ─── Need more info? Loop back to 1   │
│       │         Have enough? Generate response    │
│       ▼                                          │
│  5. RESPOND ─── Natural language answer           │
└──────────────────────────────────────────────────┘
```

The agents are created by wrapping an LLM with domain-specific system prompts and the shared MCP tools:

```python
from langgraph.prebuilt import create_react_agent

# Both agents get the SAME MCP tools but DIFFERENT system prompts
maintenance_agent = create_react_agent(llm, tools, prompt=MAINTENANCE_SYSTEM_PROMPT)
operations_agent  = create_react_agent(llm, tools, prompt=OPERATIONS_SYSTEM_PROMPT)
```

Each system prompt gives the agent:
1. **Domain expertise** -- what it specializes in
2. **Graph schema** -- the node types, relationships, and properties it should query
3. **Query guidelines** -- how to formulate good Cypher queries
4. **Example Cypher patterns** -- templates for common query shapes
5. **LIMIT enforcement** -- always bound result sets to avoid overwhelming responses

### Graph Schemas by Domain

Each specialist agent is given knowledge of the graph schema relevant to its domain.

**Maintenance Agent -- Aircraft Health Schema:**

```
(:Aircraft) -[:HAS_SYSTEM]-> (:System) -[:HAS_COMPONENT]-> (:Component)
                                                                │
                                                    [:HAS_SENSOR]
                                                                │
                                                                ▼
                                                          (:Sensor)
                                                                │
                                                    [:HAS_READING]
                                                                │
                                                                ▼
                                                          (:Reading)

(:MaintenanceEvent) -[:AFFECTED]-> (:Component)
(:MaintenanceEvent) -[:PERFORMED_ON]-> (:Aircraft)
```

| Node | Key Properties |
|------|---------------|
| `Aircraft` | tailNumber, model |
| `System` | name (Engine, Hydraulic, Electrical, Avionics) |
| `Component` | name, type |
| `Sensor` | name, type |
| `Reading` | value, timestamp, unit |
| `MaintenanceEvent` | faultCode, severity, description |

**Operations Agent -- Flight Operations Schema:**

```
(:Delay) -[:DELAYED]-> (:Flight) -[:DEPARTED_FROM]-> (:Airport)
                            │
                            ├── [:ARRIVED_AT] ──> (:Airport)
                            ├── [:OPERATED_BY] ──> (:Operator)
                            └── [:ASSIGNED_TO] ──> (:Aircraft)
```

| Node | Key Properties |
|------|---------------|
| `Flight` | flightNumber, scheduledDeparture, scheduledDuration |
| `Delay` | cause, duration |
| `Airport` | code (IATA), name |
| `Operator` | name |
| `Aircraft` | tailNumber, model |

### MCP Tool Discovery

Tools are **not hardcoded** in the agent. At startup, the orchestrator dynamically discovers available tools from the Neo4j MCP Server via the AgentCore Gateway:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_client = MultiServerMCPClient({
    "neo4j": {        # single MCP server connection
        "transport": "streamable_http",
        "url": gateway_url,
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
})
tools = await mcp_client.get_tools()
# Returns: [neo4j-mcp-server-target___get-schema, neo4j-mcp-server-target___read-cypher]
```

The `langchain-mcp-adapters` library converts MCP tool definitions into LangChain-compatible tools that ReAct agents can invoke. The Gateway prefixes each tool name with the target (e.g., `neo4j-mcp-server-target___read-cypher`).

> **Note:** There is only **one** MCP server in this architecture -- the Neo4j MCP Server. The class is called `MultiServerMCPClient` because the library supports connecting to multiple MCP servers, but here only one (`"neo4j"`) is configured. Both specialist agents share the same two tools (`get-schema` and `read-cypher`); what differentiates them is their system prompts, not their tools.

### Example: End-to-End Query Trace

Here is what happens when you ask: **"Which components have the highest failure rates?"**

```
Step 1 ─ ROUTER
  Input:  "Which components have the highest failure rates?"
  LLM:    Sees keywords "components", "failure" → responds "maintenance"
  Output: state["next_agent"] = "maintenance"

Step 2 ─ MAINTENANCE AGENT (ReAct loop)

  Iteration 1 — Reason + Act:
    Thought: I need to query the graph for components with the most
             maintenance events. Let me first check the schema.
    Action:  Call tool `neo4j-mcp-server-target___get-schema`
    Result:  Returns node labels, relationship types, and properties

  Iteration 2 — Reason + Act:
    Thought: Now I know the schema. I'll query for components with
             the most associated MaintenanceEvents, grouped by name.
    Action:  Call tool `neo4j-mcp-server-target___read-cypher`
    Input:   {
               "query": "MATCH (m:MaintenanceEvent)-[:AFFECTED]->(c:Component)
                         RETURN c.name, count(m) AS failures
                         ORDER BY failures DESC LIMIT 10"
             }
    Result:  [{"c.name": "Hydraulic Pump", "failures": 47},
              {"c.name": "APU Starter", "failures": 34},
              {"c.name": "Landing Gear Actuator", "failures": 28}, ...]

  Iteration 3 — Respond:
    Thought: I have the data. Let me present the findings clearly.
    Output:  "The components with the highest failure rates are:
              1. Hydraulic Pump — 47 failures
              2. APU Starter — 34 failures
              3. Landing Gear Actuator — 28 failures
              ..."

Step 3 ─ END
  The final AIMessage is returned to the user.
```

### Example: Operations Query Trace

For **"Which routes have the most delays?"**:

```
Step 1 ─ ROUTER
  Input:  "Which routes have the most delays?"
  LLM:    Sees keywords "routes", "delays" → responds "operations"
  Output: state["next_agent"] = "operations"

Step 2 ─ OPERATIONS AGENT (ReAct loop)

  Iteration 1 — Act:
    Action:  Call tool `neo4j-mcp-server-target___read-cypher`
    Input:   {
               "query": "MATCH (d:Delay)-[:DELAYED]->(f:Flight)-[:DEPARTED_FROM]->(origin:Airport)
                         MATCH (f)-[:ARRIVED_AT]->(dest:Airport)
                         RETURN origin.code + ' -> ' + dest.code AS route,
                                count(d) AS delays,
                                avg(d.duration) AS avgDelayMinutes
                         ORDER BY delays DESC LIMIT 10"
             }
    Result:  [{"route": "JFK -> LAX", "delays": 23, "avgDelayMinutes": 42.5},
              {"route": "ORD -> ATL", "delays": 19, "avgDelayMinutes": 38.1}, ...]

  Iteration 2 — Respond:
    Output:  "The routes with the most delays are:
              1. JFK → LAX — 23 delays (avg 42.5 min)
              2. ORD → ATL — 19 delays (avg 38.1 min)
              ..."

Step 3 ─ END
```

### Session Memory

The orchestrator uses LangGraph's `MemorySaver` checkpointer to maintain conversation context within a session:

```python
memory = MemorySaver()
compiled = graph.compile(checkpointer=memory)

# Each invocation passes a session-scoped thread_id
config = {"configurable": {"thread_id": session_id}}
result = await graph.ainvoke(
    {"messages": [HumanMessage(content=prompt)], "next_agent": ""},
    config=config,
)
```

This means follow-up questions within the same session carry context. For example:
- **You**: "Which components have the most failures?"
- **Agent**: _(lists top 10 components)_
- **You**: "Tell me more about the hydraulic pump issues"
- **Agent**: _(understands "hydraulic pump" refers to the #1 result from the previous answer)_

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

Continue to [Lab 5 - Databricks ETL to Neo4j](../Lab_5_Databricks_ETL_Neo4j) to work with Databricks and learn how to load data into Neo4j using the Spark Connector.
