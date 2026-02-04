# Lab 4 Admin Setup: AgentCore Agent Deployment

This directory contains the AgentCore agent that lab participants will interact with in Lab 4. Lab admins should deploy this agent before the workshop.

## Prerequisites

- AWS account with AgentCore access
- Neo4j MCP Server already deployed to AgentCore (separate project)
- MCP credentials from the MCP server deployment
- [uv](https://docs.astral.sh/uv/) package manager installed

## Setup Steps

### 1. Install Dependencies

```bash
./agent.sh setup
```

### 2. Configure MCP Credentials

Copy your MCP credentials from the MCP server deployment:

```bash
cp /path/to/mcp-server/.mcp-credentials.json .mcp-credentials.json
```

The credentials file should contain:
- `gateway_url` - AgentCore Gateway endpoint for the MCP server
- `token_url` - Cognito OAuth2 token endpoint
- `client_id` / `client_secret` - OAuth2 credentials
- `scope` - MCP server scope
- `region` - AWS region

See `mcp-credentials.json.example` for the expected format.

### 3. Test Locally (Optional)

```bash
# Start the agent locally
./agent.sh start

# In another terminal, test routing
./agent.sh test-maintenance   # Should route to Maintenance Agent
./agent.sh test-operations    # Should route to Operations Agent
```

### 4. Deploy to AgentCore

```bash
# Configure AWS deployment
./agent.sh configure

# Deploy (takes several minutes)
./agent.sh deploy

# Check status
./agent.sh status
```

### 5. Verify Deployment

```bash
# Test with a maintenance query
./agent.sh invoke-cloud "What are the most common maintenance faults?"

# Test with an operations query
./agent.sh invoke-cloud "Which routes have the most delays?"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentCore Agent                          │
│  ┌─────────┐    ┌───────────────┐    ┌─────────────────┐   │
│  │ Router  │───>│  Maintenance  │    │   Operations    │   │
│  │  Node   │    │    Agent      │    │     Agent       │   │
│  └─────────┘    └───────────────┘    └─────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ (OAuth2 + HTTP)
                           ▼
              ┌────────────────────────┐
              │   AgentCore Gateway    │
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Neo4j MCP Server     │
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │      Neo4j Aura        │
              └────────────────────────┘
```

## Query Routing

The orchestrator routes queries to specialist agents based on keywords:

| Keywords | Routes To |
|----------|-----------|
| maintenance, fault, component, sensor, reliability, engine, hydraulic | Maintenance Agent |
| flight, delay, route, airport, operator, schedule, on-time | Operations Agent |

## Troubleshooting

**Agent won't start locally:**
- Ensure `.mcp-credentials.json` exists
- Check that the MCP server is deployed and accessible

**Deployment fails:**
- Verify AWS credentials are configured
- Check that AgentCore is available in your region

**Agent returns errors:**
- Verify the MCP server is healthy
- Check that OAuth2 tokens can be refreshed (credentials are valid)

## Reference

- [neo4j-agentcore-mcp-server](https://github.com/neo4j-partners/aws-starter/tree/main/neo4j-agentcore-mcp-server) - MCP Server deployment
- [agentcore-neo4j-mcp-agent](https://github.com/neo4j-partners/aws-starter/tree/main/agentcore-neo4j-mcp-agent) - Original agent source
