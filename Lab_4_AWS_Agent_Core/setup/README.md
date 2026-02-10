# Lab 4 Setup: AgentCore Multi-Agent Orchestrator

This directory contains the complete source code and deployment tooling for the multi-agent orchestrator that lab participants interact with in Lab 4. Lab admins should deploy this agent before the workshop.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Neo4j MCP Server (Prerequisite)](#neo4j-mcp-server-prerequisite)
- [Architecture Deep Dive](#architecture-deep-dive)
- [File Reference](#file-reference)
- [Agent Design](#agent-design)
- [Neo4j Graph Schema](#neo4j-graph-schema)
- [Deployment to AgentCore](#deployment-to-agentcore)
- [Testing and Verification](#testing-and-verification)
- [Troubleshooting](#troubleshooting)
- [References](#references)

---

## Prerequisites

- AWS account with Amazon Bedrock and AgentCore access enabled
- Neo4j MCP Server already deployed to AgentCore Runtime (separate project: [neo4j-agentcore-mcp-server](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server))
- MCP credentials file (`.mcp-credentials.json`) from the MCP server deployment
- [uv](https://docs.astral.sh/uv/) package manager installed
- AWS CLI configured with appropriate credentials
- `bedrock-agentcore-starter-toolkit` CLI installed (`pip install bedrock-agentcore-starter-toolkit`)

---

## Neo4j MCP Server (Prerequisite)

The orchestrator agent depends on the **Neo4j MCP Server** being deployed first. This is a separate project ([neo4j-agentcore-mcp-server](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server)) that wraps a Neo4j database with the Model Context Protocol and deploys it to AgentCore Runtime.

### What the MCP Server Provides

The Neo4j MCP server exposes two read-only tools via MCP:

| Tool | Description |
|------|-------------|
| `get-schema` | Returns the database schema (node labels, relationship types, properties) |
| `read-cypher` | Executes a read-only Cypher query and returns results |

The server runs in **read-only mode** (`NEO4J_READ_ONLY=true`) -- no write, update, or delete operations are allowed.

When accessed through the AgentCore Gateway, tool names are prefixed with the target name (e.g., `neo4j-mcp-server-target___read-cypher`). The `langchain-mcp-adapters` library handles this automatically.

### MCP Server Project Structure

```
neo4j-agentcore-mcp-server/
├── cdk/                        # AWS CDK stack (Cognito, Runtime, Gateway)
│   ├── neo4j_mcp_stack.py     # Complete infrastructure definition
│   └── resources/             # Custom Resource Lambdas
│       ├── oauth_provider/    # Creates OAuth2 credential provider
│       ├── runtime_health_check/  # Polls Runtime until ready
│       └── password_setter/   # Sets Cognito user passwords
├── client/                    # Python MCP client for testing
│   ├── gateway_client.py     # Test via Gateway
│   ├── mcp_local_client.py   # Test via local Docker
│   └── mcp_operations.py     # Shared MCP operations (schema, query)
├── deploy.sh                  # Main deployment script
├── cloud.sh                   # Gateway testing wrapper
├── local.sh                   # Local Docker testing
└── .env.sample                # Configuration template
```

---

## Architecture Deep Dive

### High-Level Flow

```
                    ┌─────────────────────────────────────────────┐
                    │          AgentCore Agent (Orchestrator)      │
                    │                                             │
                    │  ┌──────────┐                               │
User Question ────> │  │  Router  │──── "maintenance" ────┐      │
                    │  │  Node    │                        │      │
                    │  └────┬─────┘                        ▼      │
                    │       │              ┌───────────────────┐   │
                    │       │              │  Maintenance      │   │
                    │       │              │  Agent (ReAct)    │   │
                    │       │              └───────────────────┘   │
                    │       │                                     │
                    │       └─── "operations" ────┐               │
                    │                             ▼               │
                    │              ┌───────────────────┐          │
                    │              │  Operations       │          │
                    │              │  Agent (ReAct)    │          │
                    │              └───────────────────┘          │
                    └──────────────┬───────────────────────────────┘
                                  │ OAuth2 Bearer Token
                                  │ Streamable HTTP Transport
                                  ▼
                    ┌──────────────────────────┐
                    │    AgentCore Gateway      │
                    │  (Auth + Tool Discovery)  │
                    └─────────────┬────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │    Neo4j MCP Server       │
                    │  (Cypher Read/Write)      │
                    └─────────────┬────────────┘
                                  │ Bolt Protocol
                                  ▼
                    ┌──────────────────────────┐
                    │      Neo4j Aura           │
                    │  (Aircraft Digital Twin)  │
                    └──────────────────────────┘
```

### Key Technologies

| Technology | Role | Version |
|-----------|------|---------|
| **Amazon Bedrock** | Foundation model hosting (Claude Sonnet 4) | Converse API |
| **AgentCore Runtime** | Serverless container hosting for the agent | ARM64 containers |
| **AgentCore Gateway** | MCP server routing with OAuth2 authentication | Streamable HTTP |
| **LangGraph** | Multi-agent orchestration via StateGraph | >= 0.2.0 |
| **LangChain** | LLM abstraction via `ChatBedrockConverse` | >= 0.3.0 |
| **langchain-mcp-adapters** | MCP tool loading for LangChain agents | >= 0.2.0 |
| **Model Context Protocol (MCP)** | Standard protocol for tool discovery and invocation | 2025-03-26 / 2025-06-18 |
| **AWS OpenTelemetry** | Automatic tracing to CloudWatch | >= 0.10.0 |

### How AgentCore Runtime Works

[AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html) deploys your agent as a containerized application with these characteristics:

- **Serverless**: No infrastructure to manage. Deployable with code upload or containers.
- **Session Isolation**: Each invocation runs in an isolated session. AgentCore automatically manages `Mcp-Session-Id` headers.
- **Protocol-specific ports**: Agents (HTTP protocol) use port 8080, MCP servers use port 8000, A2A agents use port 9000.
- **ARM64 Architecture**: Containers must target the ARM64 (aarch64) platform (AWS Graviton).
- **Stateless**: The Runtime expects stateless servers. Session state is managed externally.

### How AgentCore Gateway Works

[AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html) sits between your agent and MCP servers:

- **Tool Discovery**: Agents call `tools/list` through the Gateway to discover available MCP tools. Supports both implicit (automatic on create/update) and explicit (`SynchronizeGatewayTargets` API) synchronization.
- **Authentication**: Supports OAuth2 and NoAuth ingress strategies. Handles secure credential exchange for egress to tools.
- **Routing**: Maps agent requests to the correct MCP server target. Combines multiple APIs, functions, and tools into a single MCP endpoint.
- **Semantic Tool Selection**: Uses contextual search to help agents find appropriate tools, minimizing prompt size when thousands of tools are available.
- **Streamable HTTP**: Uses the stateless streamable-HTTP transport at the `/mcp` endpoint.

### Authentication Flow

```
Agent ──> Cognito (OAuth2 client_credentials) ──> Access Token
Agent ──> Gateway (Bearer Token) ──> MCP Server ──> Neo4j
```

1. The agent requests an OAuth2 access token from Amazon Cognito using the client credentials grant
2. Tokens are cached in memory with a 5-minute safety buffer before expiry
3. On each request, the agent checks token validity and refreshes if needed
4. The bearer token is passed in the `Authorization` header to the AgentCore Gateway

---

## File Reference

| File | Purpose |
|------|---------|
| `orchestrator_agent.py` | Main entry point. LangGraph StateGraph with Router, Maintenance, and Operations nodes. Includes credential management, MCP tool loading, and the AgentCore entrypoint handler. |
| `maintenance_agent.py` | Maintenance specialist: system prompt defining expertise in aircraft health, component reliability, sensor data, and fault analysis. Includes Neo4j schema knowledge and example Cypher patterns. |
| `operations_agent.py` | Operations specialist: system prompt defining expertise in flight scheduling, delay analysis, route management, and airline performance. Includes Neo4j schema knowledge and example Cypher patterns. |
| `invoke_agent.py` | Client tool for testing the deployed agent. Supports single queries and continuous load testing with randomized queries from `queries.txt`. |
| `queries.txt` | 20 test queries (10 maintenance, 10 operations) used for routing validation and load testing. |
| `agent.sh` | CLI tool for the full lifecycle: setup, start, test, configure, deploy, invoke, and destroy. |
| `Dockerfile` | Container definition for AgentCore Runtime deployment (Python 3.12, ARM64, port 8080). |
| `pyproject.toml` | Python project configuration with all dependencies. |
| `mcp-credentials.json.example` | Template for the required MCP credentials file. |
| `uv.lock` | Dependency lock file for reproducible builds. |

---

## Agent Design

### Router Node

The Router Node is a lightweight LLM call that classifies each incoming query into one of two domains. It uses a system prompt with keyword lists:

**Maintenance keywords**: maintenance, fault, failure, component, system, reliability, sensor, reading, repair, hydraulic, engine, avionics, critical, severity

**Operations keywords**: flight, delay, route, airport, operator, schedule, departure, arrival, on-time, airline, carrier

The router responds with a single word ("maintenance" or "operations"), and the LangGraph conditional edge routes to the corresponding specialist. Ambiguous or general queries default to the Operations Agent.

### Specialist Agents (ReAct Pattern)

Both specialist agents use the [ReAct (Reasoning + Acting)](https://arxiv.org/abs/2210.03629) pattern via LangGraph's `create_react_agent`:

1. **Reason**: The agent analyzes the question and decides which MCP tool to call
2. **Act**: The agent invokes the tool (e.g., a Cypher read query against Neo4j)
3. **Observe**: The agent receives the tool result
4. **Repeat**: If more information is needed, the agent reasons and acts again
5. **Respond**: The agent synthesizes a final natural language response

Each agent has a detailed system prompt that includes:
- Domain expertise description
- Neo4j graph schema for its domain (entities, relationships, properties)
- Query guidelines (always use LIMIT, focus on patterns and aggregations)
- Example Cypher query patterns

### LangGraph StateGraph

The orchestrator is built as a [LangGraph StateGraph](https://langchain-ai.github.io/langgraph/):

```python
graph = StateGraph(OrchestratorState)

# Nodes
graph.add_node("router", create_router_node(llm))
graph.add_node("maintenance", create_maintenance_node(llm, tools))
graph.add_node("operations", create_operations_node(llm, tools))

# Edges
graph.add_edge(START, "router")
graph.add_conditional_edges(
    "router",
    route_to_agent,
    {"maintenance": "maintenance", "operations": "operations"}
)
graph.add_edge("maintenance", END)
graph.add_edge("operations", END)
```

The graph is compiled with a `MemorySaver` checkpointer for in-session conversation memory.

### MCP Tool Loading

Tools are loaded dynamically at invocation time from the Neo4j MCP Server via the AgentCore Gateway:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_client = MultiServerMCPClient({
    "neo4j": {
        "transport": "streamable_http",
        "url": gateway_url,
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
})
tools = await mcp_client.get_tools()
```

This means the agent always discovers the latest tools available on the MCP server -- no hardcoded tool definitions.

---

## Neo4j Graph Schema

The Aircraft Digital Twin graph has two main domains:

### Maintenance Domain

```
(:Aircraft) -[:HAS_SYSTEM]-> (:System) -[:HAS_COMPONENT]-> (:Component)
(:Component) -[:HAS_SENSOR]-> (:Sensor) -[:HAS_READING]-> (:Reading)
(:MaintenanceEvent) -[:AFFECTED]-> (:Component)
(:MaintenanceEvent) -[:PERFORMED_ON]-> (:Aircraft)
```

**Entities**: Aircraft, System (Engine, Hydraulic, Electrical, Avionics), Component, Sensor, Reading, MaintenanceEvent

### Operations Domain

```
(:Flight) -[:DEPARTED_FROM]-> (:Airport)
(:Flight) -[:ARRIVED_AT]-> (:Airport)
(:Flight) -[:OPERATED_BY]-> (:Operator)
(:Flight) -[:ASSIGNED_TO]-> (:Aircraft)
(:Delay) -[:DELAYED]-> (:Flight)
```

**Entities**: Flight, Airport, Route, Operator, Delay, Aircraft

---

## Deployment to AgentCore

### Step 1: Install Dependencies

```bash
./agent.sh setup
```

This runs `uv sync` to install all Python dependencies from `pyproject.toml`.

### Step 2: Configure MCP Credentials

Copy the `.mcp-credentials.json` file from your Neo4j MCP Server deployment:

```bash
cp /path/to/mcp-server/.mcp-credentials.json .mcp-credentials.json
```

The file must contain these fields (see `mcp-credentials.json.example`):

```json
{
  "gateway_url": "https://YOUR_GATEWAY_ID.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
  "token_url": "https://YOUR_COGNITO_DOMAIN.auth.us-west-2.amazoncognito.com/oauth2/token",
  "client_id": "YOUR_COGNITO_CLIENT_ID",
  "client_secret": "YOUR_COGNITO_CLIENT_SECRET",
  "scope": "neo4j-mcp-server/mcp",
  "region": "us-west-2"
}
```

| Field | Description |
|-------|-------------|
| `gateway_url` | The AgentCore Gateway endpoint for the Neo4j MCP server. Ends with `/mcp`. |
| `token_url` | Amazon Cognito OAuth2 token endpoint for the user pool associated with the MCP server. |
| `client_id` | Cognito app client ID with the `client_credentials` grant enabled. |
| `client_secret` | Cognito app client secret. |
| `scope` | OAuth2 scope for the MCP server resource (e.g., `neo4j-mcp-server/mcp`). |
| `region` | AWS region where the resources are deployed. |

### Step 3: Test Locally (Optional)

Start the agent locally on port 8080:

```bash
# Start the orchestrator
./agent.sh start

# In another terminal, test routing to each specialist:
./agent.sh test-maintenance   # Routes to Maintenance Agent
./agent.sh test-operations    # Routes to Operations Agent

# Or send a custom query:
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the most common maintenance faults?"}'

# Stop the local server
./agent.sh stop
```

### Step 4: Deploy to AgentCore Runtime

The deployment process builds a Docker container, pushes it to Amazon ECR, and creates an AgentCore Runtime:

```bash
# Configure the deployment (prompts for IAM role, ECR repo, OAuth settings)
./agent.sh configure
```

The `agentcore configure` command will prompt for:
- **Execution role**: IAM role with permissions for Bedrock, ECR, and AgentCore
- **ECR repository**: Press Enter to auto-create one
- **Dependency file**: Auto-detected from the directory
- **OAuth**: Type `yes` and provide the Cognito discovery URL and client ID

```bash
# Deploy to AgentCore (builds container, pushes to ECR, creates Runtime)
./agent.sh deploy
```

This takes several minutes. The output will include the agent's ARN:
```
arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/neo4j-orchestrator-agent-xyz123
```

```bash
# Check deployment status
./agent.sh status
```

### Step 5: Verify the Deployment

```bash
# Test with a maintenance query
./agent.sh invoke-cloud "What are the most common maintenance faults?"

# Test with an operations query
./agent.sh invoke-cloud "Which routes have the most delays?"
```

### Dockerfile Details

The container is built for AgentCore's requirements:

```dockerfile
FROM python:3.12-slim           # Python 3.12 base
# Architecture: ARM64 (required by AgentCore Runtime)
# Port: 8080 (required by AgentCore Runtime)
# Uses uv for dependency management
# Copies: orchestrator_agent.py, maintenance_agent.py, operations_agent.py
# Entry: uv run python orchestrator_agent.py
```

Build manually if needed:
```bash
docker build --platform linux/arm64 -t neo4j-orchestrator-agent .
docker run -p 8080:8080 neo4j-orchestrator-agent
```

---

## Testing and Verification

### Test Individual Queries

```bash
# Via agent.sh (deployed agent)
./agent.sh invoke-cloud "Show me critical severity maintenance events"

# Via invoke_agent.py (deployed agent)
python invoke_agent.py "What are the busiest airports?"
```

### Load Testing

Run continuous random queries from `queries.txt`:

```bash
# Via agent.sh
./agent.sh load-test

# Via invoke_agent.py (custom interval in seconds)
python invoke_agent.py load-test --interval 10
```

The load test picks random queries from the 20 test queries in `queries.txt` and reports statistics (Maintenance/Operations/Errors).

### Test Query Examples

The `queries.txt` file contains 20 categorized test queries:

**Maintenance (1-10):**
1. What are the most common maintenance faults across the fleet?
2. Show me all critical severity maintenance events
3. Which components have the highest failure rates?
4. What hydraulic system issues have been reported?
5. Show me recent engine-related maintenance events
6. ...

**Operations (11-20):**
11. What are the top causes of flight delays?
12. Which routes have the most problematic delay patterns?
13. Show me airline performance rankings by on-time percentage
14. What are the most common weather-related delays?
15. Find all flights departing from JFK today
16. ...

---

## Troubleshooting

### Agent won't start locally

- Verify `.mcp-credentials.json` exists and has valid values
- Check that the Neo4j MCP Server is deployed and the Gateway URL is reachable
- Ensure uv dependencies are installed: `./agent.sh setup`

### OAuth token refresh fails

- Verify the Cognito client credentials (`client_id`, `client_secret`) are correct
- Confirm the `token_url` points to the correct Cognito user pool
- Check the `scope` matches what the MCP server expects

### Deployment fails

- Verify AWS CLI credentials are configured (`aws sts get-caller-identity`)
- Check that AgentCore is available in your chosen region
- Ensure the IAM execution role has the required permissions for Bedrock, ECR, and AgentCore
- Verify Docker is installed and running (for container builds)

### Agent returns errors

- Check CloudWatch logs for the AgentCore Runtime (OpenTelemetry traces are sent automatically)
- Verify the MCP server is healthy by testing the Gateway URL directly
- Confirm Neo4j Aura is running and accessible from the MCP server
- Check that OAuth2 tokens are valid (tokens expire and are auto-refreshed with a 5-minute safety buffer)

### Agent routes to wrong specialist

- The Router Node uses keyword matching -- queries with mixed domain terms may route unexpectedly
- Ambiguous or general queries default to the Operations Agent
- Review the router classification in the logs: `[Router] Classification: maintenance|operations`

---

## References

- [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) - Product page
- [AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/) - Official documentation
- [AgentCore Runtime Service Contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html) - Protocol ports and endpoints
- [MCP Protocol Contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp-protocol-contract.html) - MCP server requirements
- [Deploy MCP Servers in AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html) - MCP deployment guide
- [AgentCore Gateway MCP Targets](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html) - Gateway configuration
- [amazon-bedrock-agentcore-samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) - Official AWS examples
- [neo4j-agentcore-mcp-server](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server) - Neo4j MCP Server deployment
- [agentcore-neo4j-mcp-agent](https://github.com/neo4j-partners/aws-starter/tree/main/agentcore-neo4j-mcp-agent) - Original agent source
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) - Multi-agent orchestration framework
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
