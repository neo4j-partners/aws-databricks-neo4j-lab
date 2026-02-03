# Neo4j + AWS + Databricks Workshop Slides

This document contains all slide content for the hands-on workshop. Content is organized by phase as outlined in CONVERT.md.

---

# THE SCENARIO

---

## Welcome to Zenith Horizon Airlines

You've been brought in as **consultants** to solve a critical data challenge.

### Your Client

**Zenith Horizon Airlines** operates a fleet of 20 aircraft across 12 airports, serving millions of passengers annually.

### The Current State

Their data lives in **three separate systems**:

| System | Data | Who Can Access |
|--------|------|----------------|
| **Neo4j Aura** | Aircraft topology, maintenance events, components | 2 graph specialists |
| **Databricks** | 345K+ sensor readings, time-series analytics | 3 data engineers |
| **AWS** | Flight operations, delays, routes | Operations team only |

---

## The Problem

> "Our data is everywhere. Only three people in the company can write Cypher queries, and they're backlogged for weeks. Engineers need answers NOW."
>
> — **Jordan Chen**, VP of Maintenance

### Pain Points

- **Data silos** — No unified view across maintenance, sensors, and operations
- **Expert bottleneck** — Only a handful of people can query each system
- **Slow decisions** — Takes days to correlate sensor anomalies with maintenance events

### The Business Impact

- Delayed maintenance decisions
- Missed patterns that could prevent failures
- Frustrated engineers waiting for data access

---

## Your Mission

Build a **unified agent platform** that lets anyone ask questions in natural language.

### Target Users

| Persona | Sample Questions |
|---------|-----------------|
| **Maintenance Engineer** | "Which aircraft have critical maintenance issues?" |
| **Operations Analyst** | "What routes have the highest delay rates?" |
| **Fleet Manager** | "How do sensor readings correlate with failures?" |
| **Executive** | "Give me a fleet health summary" |

### Today's Deliverable

By end of day, you'll deliver a working prototype demonstrating:

1. **Natural language queries** across all data sources
2. **Multi-agent routing** for different domains
3. **No-code agent building** for self-service dashboards

---

# PHASE 1: Foundation Setup (45 min)

---

## Phase 1 Context

> You've arrived at Zenith Horizon's headquarters. IT has provisioned your access to their three core platforms. Before you can build anything, you need credentials and connectivity.

---

## Workshop Overview

Welcome to the **Neo4j, AWS, and Databricks** hands-on lab!

In this workshop, you'll learn to build AI-powered applications that combine:
- **Knowledge Graphs** - Structured data with relationships
- **Large Language Models** - Natural language understanding
- **GraphRAG** - Graph-enhanced retrieval for better AI responses

**Total Duration:** ~4.5 hours

**Key Technologies:**
- Neo4j Aura (Graph Database)
- AWS AgentCore + API Gateway (Pre-deployed agent infrastructure)
- Databricks (Notebooks, Unity Catalog, AgentBricks)
- Neo4j Spark Connector

---

## What You'll Build

### The Architecture

```
Phase 1: Setup
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  AWS Console │  │  Databricks  │  │  Neo4j Aura  │
│   (access)   │  │   (access)   │  │ (credentials)│
└──────────────┘  └──────────────┘  └──────────────┘

Phase 2: AWS AgentCore (Console Tour + Sandbox + Notebook)
┌─────────────────────────────────────────────────────────────┐
│                         AWS                                  │
│  Agent Sandbox ──┐                                          │
│  (Console UI)    │         AgentCore    MCP        Neo4j    │
│                  ├───────▶ Agent ────▶ Gateway ──▶ MCP ──▶ Aura
│  Databricks      │         (Claude)    (OAuth2)   Server    │
│  Notebook ───────┘                                          │
│  (HTTP + API Key)                                           │
└─────────────────────────────────────────────────────────────┘

Phase 3 (Optional): Databricks ETL
┌─────────────────────────────────────────────────────────────┐
│                      DATABRICKS                              │
│  Volume (CSV) ──▶ Notebook ──▶ Spark Connector ──▶ Neo4j   │
└─────────────────────────────────────────────────────────────┘

Phase 4: Databricks Multi-Agent
┌─────────────────────────────────────────────────────────────┐
│                      DATABRICKS                              │
│  ┌─────────────────┐                                        │
│  │   AgentBricks   │──▶ Agent A ──▶ AWS AgentCore (Phase 2) │
│  │  (Orchestrator) │                                        │
│  │                 │──▶ Agent B ──▶ Lakehouse / Neo4j       │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘

Phase 5: Neo4j Exploration & Aura Agents
┌─────────────────────────────────────────────────────────────┐
│                      NEO4J AURA                              │
│  Browser/Bloom ──▶ Visualize ──▶ Cypher Queries             │
│  Aura Agents ───▶ No-Code AI ──▶ Conversational Access      │
└─────────────────────────────────────────────────────────────┘
```

---

## Why Graph Databases?

### The Problem with Relational Databases

Traditional databases struggle with **connected data**:

| Query | Relational Approach | Graph Approach |
|-------|---------------------|----------------|
| "Friends of friends" | Multiple JOINs, slow | Single traversal |
| "What impacts what?" | Complex subqueries | Pattern matching |
| "How are these connected?" | Hard to express | Native relationships |

### Real-World Impact

Questions like:
- "Which asset managers are exposed to cybersecurity risks?"
- "What companies share risk factors with Apple?"

These require **traversing relationships** - exactly what graphs do best.

---

## What is Neo4j Aura?

### Fully Managed Cloud Graph Database

Neo4j Aura eliminates the operational overhead of running a graph database.

**Key Characteristics:**
- **Fully managed** - No infrastructure to maintain
- **Scalable** - Automatically scales with your data
- **Secure** - Enterprise-grade security and compliance
- **Cloud-native** - Deploy in AWS, GCP, or Azure

### Why "Aura"?

Aura provides the power of Neo4j without the operational burden:
- Automatic backups and updates
- High availability built-in
- Pay for what you use

---

## Aura for AI/GenAI

### GraphRAG Foundation

Neo4j Aura provides unique capabilities for AI applications:

| Feature | AI Benefit |
|---------|------------|
| **Vector indexes** | Semantic similarity search |
| **Graph traversal** | Relationship reasoning |
| **Cypher language** | Complex retrieval patterns |
| **APIs** | Integration with LLM frameworks |

### Production-Ready

- Built-in vector indexes for embeddings
- Graph algorithms (PageRank, community detection)
- Low-latency queries for real-time AI

---

## Lab 0: AWS Console Access

### Read-Only Access

- View AgentCore deployments
- Understand deployed infrastructure
- No write access required

---

## Lab 1: Databricks Workspace Access

### Setup Steps

1. Access your Databricks workspace using provided credentials
2. Verify cluster access
3. Clone workshop repository

### Pre-Configured Environment

- CSV files pre-uploaded to Unity Catalog Volume
- Ready-to-run notebooks provided
- Neo4j Spark Connector library installed on cluster

---

## Lab 2: Neo4j Aura Credentials

### Save Connection Credentials

You'll receive:
- **NEO4J_URI** - Connection endpoint
- **NEO4J_USERNAME** - Database username
- **NEO4J_PASSWORD** - Database password

**Important:** Save these credentials - you'll need them in later phases!

Exploration of the database happens in Phase 5.

---

# PHASE 2: AWS - AgentCore Overview + Notebook (60 min)

---

## Phase 2 Context

> The maintenance team at Zenith Horizon wants to ask questions about aircraft health without learning Cypher. AWS has pre-deployed an agent infrastructure that connects to their Neo4j database. You'll explore how it works and test it.

---

## The Problem Agents Solve

### Users Don't Know Cypher

Your knowledge graph is powerful, but querying it requires Cypher:

```cypher
MATCH (c:Company)-[:FACES_RISK]->(r:RiskFactor)
WHERE c.name = 'APPLE INC'
RETURN r.name
```

**Most users can't write this.**

### Users Don't Know Retriever Types

You have different retrieval patterns:
- Vector search for semantic content
- Text2Cypher for precise facts
- Graph traversal for relationships

**Users just want to ask questions.**

### The Solution

An agent that **understands questions** and **chooses the right approach** automatically.

---

## What is an AI Agent?

### Beyond Simple Chat

Regular chat is one-shot:
```
User → LLM → Response
```

Agents can **take actions** and **iterate**:
```
User → LLM → Tool → Observe → LLM → Tool → ... → Response
```

### Agent Capabilities

| Capability | Example |
|------------|---------|
| **Tool Use** | Query a database, call an API |
| **Iteration** | Try multiple approaches |
| **Memory** | Remember conversation context |
| **Reasoning** | Decide what to do next |

### Why Agents Matter

Complex tasks often require:
- Breaking the problem into steps
- Gathering information from multiple sources
- Adapting based on results

---

## The ReAct Pattern

### Reasoning + Acting

**ReAct** (Reason + Act) is a fundamental agent pattern:

```
1. Receive question
2. REASON: "I need to find the current time"
3. ACT: Call get_current_time tool
4. OBSERVE: "2024-01-15 10:30:00"
5. REASON: "Now I can answer the question"
6. RESPOND: "The current time is 10:30 AM"
```

### The Loop

```
        ┌─────────────────────────┐
        │                         │
        ▼                         │
    [Reason] ──▶ [Act] ──▶ [Observe]
        │
        ▼
    [Respond]
```

For complex questions, the agent may loop multiple times.

---

## What is MCP?

### Model Context Protocol

An **open standard** defining how AI assistants connect to external data sources and tools.

### The Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   AI Agent   │◀──MCP──▶│  MCP Server  │◀───────▶│  Data Source │
│  (Claude,    │         │  (Neo4j,     │         │  (Database,  │
│   GPT, etc)  │         │   Files)     │         │   API, etc)  │
└──────────────┘         └──────────────┘         └──────────────┘
```

### Benefits

- **Universal adapter** - One protocol for any tool
- **Discovery** - Agents learn available capabilities
- **Standardized** - Consistent interface across tools
- **Secure** - Built-in authentication patterns

---

## The Integration Problem

### Before MCP

Connecting an AI agent to external tools required:

| Challenge | Description |
|-----------|-------------|
| **Custom code** | Build integration for each tool |
| **Different auth** | Handle authentication per service |
| **Unique formats** | Parse tool-specific responses |
| **Manual lifecycle** | Manage connections yourself |

### The Scale Problem

If you have:
- 5 AI applications
- 10 data sources

You need **50 custom integrations**.

### The Dream

One protocol that any AI agent can use to connect to any data source.

That's **MCP**.

---

## MCP Interaction Pattern

### The Five-Step Dance

```
1. DISCOVERY
   Agent connects and requests available tools

2. SELECTION
   LLM decides which tool fits the question

3. INVOCATION
   Agent sends tool call with parameters

4. RESPONSE
   MCP server executes and returns results

5. SYNTHESIS
   LLM incorporates results into response
```

### Example

```python
# 1. Agent discovers tools
tools = mcp_client.list_tools()
# → [{"name": "read-cypher", ...}]

# 2-4. Agent invokes tool
result = mcp_client.call_tool("read-cypher", {
    "query": "MATCH (c:Company) RETURN count(c)"
})

# 5. LLM synthesizes
# "There are 8 companies in the database."
```

---

## Neo4j MCP Server

### Tools Provided

The Neo4j MCP Server exposes two tools:

| Tool | Purpose |
|------|---------|
| `get-schema` | Retrieves node labels, relationship types, properties |
| `read-cypher` | Executes read-only Cypher queries |

### Why Two Tools?

**Schema First:** Before generating queries, the agent needs to understand your data model.

```
1. Agent calls: get-schema
2. Learns: Company, RiskFactor, FACES_RISK, OWNS...
3. Now can generate accurate Cypher
```

**Read-Only:** The `read-cypher` tool only allows read operations - safe for exploration.

---

## Why Schema Matters

### Graph Databases Are Schema-Flexible

Unlike relational databases, graphs don't require predefined tables.

**This means:** The LLM needs to discover what exists.

### What get-schema Reveals

| Component | Examples |
|-----------|----------|
| Node labels | `Company`, `RiskFactor`, `Product` |
| Relationship types | `FACES_RISK`, `OWNS`, `MENTIONS` |
| Properties | `name`, `ticker`, `description` |

### Better Queries

With schema knowledge:

```cypher
-- LLM knows Company has 'name' property
-- LLM knows FACES_RISK connects Company to RiskFactor
MATCH (c:Company {name: 'APPLE INC'})-[:FACES_RISK]->(r:RiskFactor)
RETURN r.name
```

Without schema: The LLM guesses and often fails.

---

## Agent Flow

### What Happens When You Ask a Question

```
User: "What risk factors does Apple face?"
         │
         ▼
┌─────────────────────────────────────────┐
│  LLM: Analyzes question, decides to     │
│       first understand the schema       │
│       → Calls: get-schema               │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  MCP Server: Returns schema             │
│  - Nodes: Company, RiskFactor...        │
│  - Rels: FACES_RISK, OWNS...            │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  LLM: Formulates Cypher query           │
│       → Calls: read-cypher              │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  MCP Server: Executes, returns results  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  LLM: Synthesizes human response        │
│  "Apple faces the following risks..."   │
└─────────────────────────────────────────┘
```

---

## Part A: Read-Only Console Tour

### What You'll See

- View the pre-deployed Neo4j MCP server in AWS Console
- View the AgentCore agent deployment (which calls the Neo4j MCP server)
- Understand the architecture: Agent → MCP Gateway → Neo4j MCP Server → Neo4j Aura

### Lab Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Your Notebook  │────▶│   AgentCore     │────▶│   Neo4j MCP     │
│  (Agent Code)   │     │   Gateway       │     │    Server       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │ Bedrock API                                   │
        ▼                                               ▼
┌─────────────────┐                           ┌─────────────────┐
│   Claude LLM    │                           │   Neo4j Aura    │
│   (Reasoning)   │                           │    Database     │
└─────────────────┘                           └─────────────────┘
```

---

## Part B: Agent Sandbox Testing (No-Code)

### Use the AgentCore Agent Sandbox

- Use the AgentCore Agent Sandbox in the AWS Console
- Interactively test the deployed agent without writing code
- Send natural language questions about the aircraft data
- See agent reasoning and Cypher query generation in real-time

### Sample Questions to Try

**Explore the Data Model:**
```
"What is the database schema?"
```

**Simple Counts:**
```
"How many companies are in the database?"
"How many risk factors exist?"
```

**Relationship Traversal:**
```
"What companies does BlackRock own?"
"What risk factors does Apple face?"
```

**Comparative Analysis:**
```
"Which company has the most risk factors?"
"What risks do Apple and Microsoft share?"
```

---

## Agent Reasoning

### Understanding Tool Selection

The agent shows its reasoning process:

```
Question: "Tell me about Apple Inc"

Reasoning: This question asks for company overview information.
           The get_company_overview tool is designed for this.
           Parameter: company_name = "APPLE INC"

Action: Calling get_company_overview with company_name="APPLE INC"

Result: Company data with risks and investors

Response: "Apple Inc is a technology company that faces
          several key risk factors including..."
```

### Why Reasoning Matters

- **Transparency** - Understand why the agent chose its approach
- **Debugging** - Identify when tools are misselected
- **Trust** - Users can verify the agent's logic

---

## Part C: Notebook - Call the Agent

### Simple Databricks Notebook

- Simple Databricks notebook that calls the agent via HTTP
- Uses pre-shared API key (no OAuth complexity for participants)
- Demonstrates querying Neo4j through natural language
- Participants see the agent reasoning and Cypher generation

### API Request Flow

```
Your Application
    │
    ▼
┌─────────────────────────┐
│  Call Agent via API Key │
│  POST /agents/.../invoke│
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Parse Response         │
│  Extract text/tools     │
└─────────────────────────┘
```

---

## Response Structure

### Calling the Agent

```http
POST {agent_endpoint}
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "input": "Tell me about Apple's risk factors"
}
```

### Response Structure

```json
{
  "status": "completed",
  "content": [
    {
      "type": "text",
      "text": "Apple Inc faces several key risk factors..."
    },
    {
      "type": "tool_use",
      "name": "get_company_overview",
      "input": {"company_name": "APPLE INC"}
    }
  ],
  "usage": {
    "input_tokens": 150,
    "output_tokens": 350
  }
}
```

---

## Response Parsing

### Content Types

The response `content` array contains different block types:

| Type | Description |
|------|-------------|
| `text` | The generated answer text |
| `thinking` | Agent's reasoning process |
| `tool_use` | Tool invocations made |
| `tool_result` | Results from tools |

### Extracting the Answer

```python
def extract_text(response):
    """Extract text content from response."""
    return "\n".join(
        block["text"]
        for block in response["content"]
        if block["type"] == "text"
    )
```

---

# PHASE 3 (Optional): Databricks - ETL to Neo4j (45 min)

---

## Phase 3 Context

> Zenith Horizon's operations team has new aircraft and operator data sitting in Databricks. They need it loaded into Neo4j so the agents can answer questions about the full fleet. You'll build that data pipeline.

---

## Phase 3 Overview

### Participant Experience: Pre-Configured Environment

- CSV files pre-uploaded to Unity Catalog Volume
- Ready-to-run notebook provided

### Data Subset: Aircraft and Operators

- Aircraft nodes (tail numbers, models, fleet info)
- Operator nodes (airlines, operators)
- Relationships connecting aircraft to their operators

---

## Part A: Data Model Mapping

### From Tables to Graph

| Concept | Relational | Graph |
|---------|------------|-------|
| Entity | Table row | Node with label |
| Attribute | Column | Property |
| Reference | Foreign key | Relationship |
| Join table | Many-to-many | Direct connection |

### Example Mapping

```
Aircraft Table Row:
  tail_number: N12345
  model: Boeing 737
  operator_id: 42

Graph:
  (:Aircraft {tail_number: 'N12345', model: 'Boeing 737'})
      -[:OPERATED_BY]->
  (:Operator {id: 42})
```

---

## Why Graph for This Data?

### Connected Data Questions

Questions that become easy with graphs:

- "What aircraft does Delta operate?"
- "Which operators share the same aircraft models?"
- "What's the fleet composition for each operator?"

### The Graph Advantage

```cypher
-- Find operators with shared aircraft types
MATCH (o1:Operator)<-[:OPERATED_BY]-(a:Aircraft)-[:OPERATED_BY]->(o2:Operator)
WHERE o1 <> o2
RETURN o1.name, o2.name, a.model
```

This query would require complex JOINs in SQL.

---

## Part B: Load Data with Spark Connector

### The Neo4j Spark Connector

Enables bidirectional data transfer between Spark and Neo4j:
- Read from Neo4j into DataFrames
- Write DataFrames to Neo4j

### Writing Nodes

```python
# Write Aircraft nodes
aircraft_df.write \
    .format("org.neo4j.spark.DataSource") \
    .mode("Overwrite") \
    .option("url", NEO4J_URI) \
    .option("authentication.basic.username", NEO4J_USERNAME) \
    .option("authentication.basic.password", NEO4J_PASSWORD) \
    .option("labels", "Aircraft") \
    .option("node.keys", "tail_number") \
    .save()
```

---

## Writing Relationships

### Connecting Aircraft to Operators

```python
# Write OPERATED_BY relationships
relationships_df.write \
    .format("org.neo4j.spark.DataSource") \
    .mode("Overwrite") \
    .option("url", NEO4J_URI) \
    .option("authentication.basic.username", NEO4J_USERNAME) \
    .option("authentication.basic.password", NEO4J_PASSWORD) \
    .option("relationship", "OPERATED_BY") \
    .option("relationship.source.labels", "Aircraft") \
    .option("relationship.source.node.keys", "tail_number") \
    .option("relationship.target.labels", "Operator") \
    .option("relationship.target.node.keys", "operator_id") \
    .save()
```

---

## Validating the Load

### Simple Cypher Queries

After loading, validate with Cypher:

```cypher
-- Count nodes
MATCH (a:Aircraft) RETURN count(a) AS aircraft_count

-- Count relationships
MATCH ()-[r:OPERATED_BY]->() RETURN count(r) AS rel_count

-- Sample data
MATCH (a:Aircraft)-[:OPERATED_BY]->(o:Operator)
RETURN a.tail_number, a.model, o.name
LIMIT 5
```

---

# PHASE 4: Databricks - Multi-Agent with AgentBricks (45 min)

---

## Phase 4 Context

> Different teams at Zenith Horizon have different questions. Maintenance wants component reliability data. Operations wants delay analysis. You'll build an orchestrator that routes queries to the right specialist agent.

---

## Phase 4 Overview

### No-Code Visual Builder

- Build multi-agent using AgentBricks visual interface

### Agent Architecture

- **Agent A:** Calls Phase 2 AWS AgentCore agent (full Neo4j dataset)
- **Agent B:** Queries Phase 3 data (lakehouse + newly loaded graph data)
- **Orchestrator:** Routes queries to appropriate agent

### Deployment

- Deploy as serving endpoint

---

## Agent Tools Overview

### Three Retrieval Patterns

| Tool Type | What It Does | Best For |
|-----------|--------------|----------|
| **Cypher Templates** | Run pre-defined queries | Precise, controlled lookups |
| **Similarity Search** | Find semantically similar content | Exploring topics |
| **Text2Cypher** | Convert questions to Cypher | Flexible ad-hoc queries |

### How the Agent Chooses

The agent reads tool descriptions and matches them to questions:

- "Tell me about Apple" → `get_company_overview` (template)
- "What do filings say about AI?" → `search_filing_content` (similarity)
- "How many risk factors exist?" → `query_database` (Text2Cypher)

### Tool Descriptions Matter

Good descriptions help the agent choose correctly.

---

## Cypher Template Tools

### Controlled, Precise Queries

Cypher templates are pre-defined queries with parameters:

```cypher
MATCH (c:Company {name: $company_name})
OPTIONAL MATCH (c)-[:FACES_RISK]->(r:RiskFactor)
RETURN c.name, collect(r.name) AS risks
```

### Why Use Templates?

| Benefit | Description |
|---------|-------------|
| **Predictable** | Same query every time |
| **Optimized** | You control the query structure |
| **Secure** | No arbitrary query generation |
| **Fast** | No LLM query generation overhead |

---

## Similarity Search Tool

### Semantic Content Discovery

Similarity search finds content by **meaning**, not keywords.

### How It Works

```
User Question: "What do filings say about artificial intelligence?"
    ↓
Question → Embedding (vector)
    ↓
Find chunks with similar embeddings
    ↓
Return semantically relevant passages
```

### Configuration

| Setting | Purpose |
|---------|---------|
| **Embedding Provider** | OpenAI, Bedrock, etc. |
| **Embedding Model** | text-embedding-ada-002 |
| **Vector Index** | chunkEmbeddings |
| **Top K** | Number of results (e.g., 5) |

### Best For

- "What does [topic] mean?"
- "Find information about..."
- Conceptual, exploratory questions

---

## Text2Cypher Tool

### Natural Language to Database Queries

Text2Cypher uses an LLM to convert questions into Cypher:

```
"Which company has the most risk factors?"
    ↓
MATCH (c:Company)-[:FACES_RISK]->(r:RiskFactor)
RETURN c.name, count(r) AS riskCount
ORDER BY riskCount DESC
LIMIT 1
```

### When to Use

| Question Pattern | Example |
|------------------|---------|
| Counts | "How many products does Apple mention?" |
| Lists | "List all companies in the database" |
| Comparisons | "Which company has the most executives?" |
| Specific facts | "What is NVIDIA's ticker symbol?" |

### Trade-offs

- **Flexible** - Can answer any structured question
- **Less predictable** - LLM may generate different queries
- **Requires good schema understanding** - LLM needs to know your model

---

## LangGraph Architecture

### Graph-Based Agents

LangGraph represents agents as a **graph** of nodes and edges:

```
START → agent → (tools → agent) | END
```

### Core Components

| Component | Purpose |
|-----------|---------|
| **Nodes** | Functions that process state |
| **Edges** | Connections between nodes |
| **State** | Shared data (message history) |
| **Conditional Edges** | Route based on conditions |

### Why Graphs?

- **Flexible** - Add nodes for new capabilities
- **Debuggable** - Visualize the flow
- **Composable** - Build complex from simple
- **Stateful** - Track conversation history

---

## Building the Graph

### Minimal Agent Structure

```python
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode

# Create the graph
graph = StateGraph(MessagesState)

# Add nodes
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))

# Add edges
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")

# Compile
agent = graph.compile()
```

### The Flow

1. **START** → Call the agent (LLM)
2. **Agent** → Decide: use tools or respond?
3. **Tools** (if needed) → Execute tool, return to agent
4. **END** → Return final response

---

## Defining Tools

### What is a Tool?

A function the LLM can call to interact with external systems.

### Creating Tools with @tool

```python
from langchain_core.tools import tool
from datetime import datetime

@tool
def get_current_time() -> str:
    """Get the current date and time.

    Use this when the user asks about the current time
    or needs a timestamp.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

### Key Elements

| Element | Purpose |
|---------|---------|
| **@tool decorator** | Converts function to tool |
| **Docstring** | Becomes tool description (critical!) |
| **Type hints** | Define parameter types |
| **Return type** | What the tool returns |

---

## Tool Descriptions Matter

### The LLM Reads Your Docstrings

Tool selection is guided by descriptions:

```python
@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.

    Use this tool when the user asks to add, sum,
    or calculate the total of two numbers.

    Args:
        a: The first number
        b: The second number

    Returns:
        The sum of a and b
    """
    return a + b
```

### Best Practices

| Practice | Why |
|----------|-----|
| Be specific | Helps LLM choose correctly |
| Include examples | "When the user asks..." |
| Describe parameters | Clear input expectations |
| Explain returns | What the tool provides |

---

## Binding Tools to the LLM

### Making Tools Available

```python
# Define your tools
tools = [get_current_time, add_numbers]

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(tools)
```

### What Binding Does

1. **Converts tools** to a format the LLM understands
2. **Includes descriptions** in the system prompt
3. **Enables tool calls** in LLM responses

### The Agent Node

```python
def call_model(state: MessagesState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}
```

The agent receives messages, calls the LLM (with tools bound), and returns the response.

---

# PHASE 5: Neo4j Aura - Graph Exploration & Aura Agents (50 min)

---

## Phase 5 Context

> Before the final demo to Zenith Horizon's leadership, you'll explore the graph data yourself to understand what's possible. Then you'll build a no-code Aura Agent that executives can use without any technical training.

---

## Part A: Graph Exploration with Browser/Bloom (30 min)

---

## Aura Tools

### Query Workspace

A developer-friendly environment for Cypher:
- Write and execute Cypher queries
- Syntax highlighting and auto-completion
- Save and organize query collections
- Export results in multiple formats

### Explore (powered by Neo4j Bloom)

Visual graph exploration tool:
- Interactive canvas for your graph data
- Natural language and pattern-based search
- "Show me a graph" sample queries
- Export as PNG, CSV, or shareable scenes

### Dashboards

Data visualization with low/no code:
- Bar charts, line charts, pie charts
- Geographic maps
- 3D graph visualizations

---

## Explore the Knowledge Graph

### Visual Exploration

1. Click **Explore** in your Aura instance
2. Start with "Show me a graph" samples

### Try These Explorations

**Find Asset Manager Networks:**
- Search for "BlackRock"
- Expand to see owned companies
- Explore shared risk factors

**Discover Risk Patterns:**
- Search for "cybersecurity"
- See which companies face this risk
- Find common risk themes

### Apply Graph Algorithms

- Use **Degree Centrality** to find highly connected nodes
- Identify key entities in your graph

---

## The GraphRAG Solution

### From Unstructured to Structured

Documents contain structure that traditional RAG ignores:

- **Entities**: Companies, people, products, risks
- **Relationships**: Owns, faces, mentions, works for

### GraphRAG Extracts This Structure

```
Traditional RAG asks: "What chunks are similar to this query?"

GraphRAG asks: "What entities and relationships are relevant?"
```

### The Difference

**Traditional RAG:**
```
Question → Vector Search → Chunks → LLM → Answer
```

**GraphRAG:**
```
Question → Vector Search → Nodes → Graph Traversal → Enriched Context → LLM → Answer
```

Graph traversal adds relationship context that similarity search alone cannot provide.

---

## LLM Limitations

### Three Fundamental Problems

| Problem | Description |
|---------|-------------|
| **Hallucination** | Generates confident but wrong information |
| **Knowledge Cutoff** | No access to recent events or your data |
| **Relationship Blindness** | Can't connect information across documents |

### Hallucination

LLMs generate the most *probable* continuation, not the most *accurate*.

> In 2023, US lawyers were sanctioned for submitting an LLM-generated brief with six fictitious case citations.

### Knowledge Cutoff

Ask about your Q3 results or last week's board meeting - the LLM may generate a confident (and wrong) response.

### Relationship Blindness

"Which asset managers own companies facing cybersecurity risks?"

This requires *reasoning over relationships* - connecting entities across documents.

---

## The Solution: Context

### All Three Problems Have One Solution

**Providing context** addresses all three LLM limitations:

| Problem | How Context Helps |
|---------|-------------------|
| Hallucination | Facts to work with |
| Knowledge Cutoff | Access to your data |
| Relationship Blindness | Structured information |

### RAG: Retrieval-Augmented Generation

Instead of relying on what the LLM "knows," we:

1. **Retrieve** relevant information from your data
2. **Augment** the LLM's prompt with this context
3. **Generate** a response grounded in facts

### The Key Insight

The LLM becomes a **reasoning engine** over your data, not a source of truth.

---

## Part B: Build an Aura Agent (No-Code) (20 min)

---

## From Graph to Conversation

In Part A, you explored the knowledge graph manually. Now you'll make it **conversational**.

### What You'll Build

An AI-powered agent that helps users analyze the aircraft digital twin data by combining:
- **Semantic search** - Find content by meaning
- **Graph traversal** - Follow relationships
- **Natural language** - No Cypher required

### No Code Required

Aura Agents let you build intelligent interfaces through a visual UI - configure, test, and deploy without writing code.

---

## What is an Aura Agent?

### No-Code GraphRAG

Aura Agents provide AI-powered conversational interfaces to your graph database.

### How It Works

```
User Question
    ↓
Agent analyzes the question
    ↓
Selects appropriate tool(s)
    ↓
Retrieves data from Neo4j
    ↓
LLM synthesizes response
    ↓
Human-readable answer
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **Agent Instructions** | Guide the agent's behavior and tone |
| **Tools** | Capabilities the agent can use |
| **Target Instance** | Your Neo4j database |

---

## Aura Agent Tools Overview

### Three Retrieval Patterns

| Tool Type | What It Does | Best For |
|-----------|--------------|----------|
| **Cypher Templates** | Run pre-defined queries | Precise, controlled lookups |
| **Similarity Search** | Find semantically similar content | Exploring topics |
| **Text2Cypher** | Convert questions to Cypher | Flexible ad-hoc queries |

### How the Agent Chooses

The agent reads tool descriptions and matches them to questions:

- "Tell me about aircraft N12345" → `get_aircraft_overview` (template)
- "What do manuals say about vibration?" → `search_content` (similarity)
- "Which aircraft has the most delays?" → `query_database` (Text2Cypher)

### Tool Descriptions Matter

Good descriptions help the agent choose correctly.

---

## Cypher Template Tools

### Controlled, Precise Queries

Cypher templates are pre-defined queries with parameters:

```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
OPTIONAL MATCH (a)<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent)
RETURN a.tail_number, a.model, collect(m.description) AS events
```

### Why Use Templates?

| Benefit | Description |
|---------|-------------|
| **Predictable** | Same query every time |
| **Optimized** | You control the query structure |
| **Secure** | No arbitrary query generation |
| **Fast** | No LLM query generation overhead |

### Templates You'll Create

- `get_aircraft_overview` - Aircraft info + systems + maintenance
- `find_shared_issues` - Issues affecting multiple aircraft
- `get_route_delays` - Delay analysis for airport pairs

---

## Similarity Search Tool

### Semantic Content Discovery

Similarity search finds content by **meaning**, not keywords.

### How It Works

```
User Question: "What causes engine vibration issues?"
    ↓
Question → Embedding (vector)
    ↓
Find content with similar embeddings
    ↓
Return semantically relevant passages
```

### Configuration

| Setting | Purpose |
|---------|---------|
| **Embedding Provider** | OpenAI, Bedrock, etc. |
| **Embedding Model** | text-embedding-ada-002 |
| **Vector Index** | Your vector index name |
| **Top K** | Number of results (e.g., 5) |

### Best For

- "What does [topic] mean?"
- "Find information about..."
- Conceptual, exploratory questions

---

## Text2Cypher Tool

### Natural Language to Database Queries

Text2Cypher uses an LLM to convert questions into Cypher:

```
"Which aircraft has the most maintenance events?"
    ↓
MATCH (a:Aircraft)<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent)
RETURN a.tail_number, count(m) AS eventCount
ORDER BY eventCount DESC
LIMIT 1
```

### When to Use

| Question Pattern | Example |
|------------------|---------|
| Counts | "How many flights were delayed?" |
| Lists | "List all aircraft in the fleet" |
| Comparisons | "Which route has the most delays?" |
| Specific facts | "What model is aircraft N12345?" |

### Trade-offs

- **Flexible** - Can answer any structured question
- **Less predictable** - LLM may generate different queries
- **Requires good schema understanding** - LLM needs to know your model

---

## Lab: Create the Agent

### Step 1: Create Agent

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Select **Agents** → **Create Agent**
3. Configure:
   - **Name:** `{your-initials}-aircraft-analyst`
   - **Target Instance:** Your Aura database
   - **External Endpoint:** Enabled

### Step 2: Write Agent Instructions

```
You are an expert aircraft maintenance analyst assistant.
You help users understand:
- Maintenance events and their severity patterns
- System and component reliability
- Flight delay patterns and causes
- Relationships between aircraft, systems, and maintenance
```

Good instructions guide the agent's tone and focus.

---

## Lab: Adding Tools

### Step 3: Add Cypher Template Tools

**Tool 1: get_aircraft_overview**
```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (a)<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent)
RETURN a.tail_number, a.model,
       collect(DISTINCT s.name) AS systems,
       collect(DISTINCT m.description)[0..5] AS recent_events
```

**Tool 2: find_shared_issues**
```cypher
MATCH (a:Aircraft {model: $model})<-[:AFFECTS_AIRCRAFT]-(m:MaintenanceEvent)
WITH m.description AS issue, collect(DISTINCT a.tail_number) AS aircraft
WHERE size(aircraft) > 1
RETURN issue, aircraft
```

### Step 4: Add Text2Cypher

For flexible, ad-hoc queries about the aircraft data.

---

## Lab: Testing Your Agent

### Sample Questions by Tool Type

**Cypher Templates:**
- "Tell me about aircraft N12345"
- "What issues affect Boeing 737-800 aircraft?"

**Text2Cypher:**
- "Which aircraft has the most critical maintenance events?"
- "What routes have the highest delay rates?"

### What to Observe

For each question, check:
1. **Which tool** did the agent select?
2. **What context** was retrieved?
3. **How** was the response synthesized?

---

## Agent Reasoning

### Understanding Tool Selection

The agent shows its reasoning process:

```
Question: "Tell me about aircraft N12345"

Reasoning: This question asks for aircraft overview information.
           The get_aircraft_overview tool is designed for this.
           Parameter: tail_number = "N12345"

Action: Calling get_aircraft_overview with tail_number="N12345"

Result: Aircraft data with systems and maintenance events

Response: "Aircraft N12345 is a Boeing 737-800 with three
          major systems. Recent maintenance events include..."
```

### Why Reasoning Matters

- **Transparency** - Understand why the agent chose its approach
- **Debugging** - Identify when tools are misselected
- **Trust** - Users can verify the agent's logic

---

## Aura Agents Summary

### What You Built

A no-code Aura Agent combining three retrieval patterns:

| Pattern | Tool | Best For |
|---------|------|----------|
| Structured queries | Cypher Templates | Precise lookups |
| Semantic search | Similarity Search | Topic exploration |
| Flexible queries | Text2Cypher | Ad-hoc questions |

### Key Takeaways

- **Aura Agents** require no code to build
- **Tool descriptions** guide automatic selection
- **Multiple patterns** combine for comprehensive answers
- **Agent reasoning** shows how decisions are made

---

# WORKSHOP SUMMARY

---

## What You Delivered to Zenith Horizon

### The Problem You Solved

| Before | After |
|--------|-------|
| Data siloed across 3 platforms | Unified agent platform |
| Only 3 experts could query data | Anyone can ask in natural language |
| Days to get answers | Seconds to get insights |

### What You Built

| Phase | Deliverable |
|-------|-------------|
| **Phase 1** | Connected to all three Zenith Horizon platforms |
| **Phase 2** | Validated the AWS AgentCore infrastructure for maintenance queries |
| **Phase 3** | (Optional) Built ETL pipeline to sync Databricks → Neo4j |
| **Phase 4** | Created multi-agent orchestrator for different teams |
| **Phase 5a** | Explored the graph to validate data quality |
| **Phase 5b** | Built no-code Aura Agent for executive dashboard |

---

## Skills Gained

- **Knowledge Graphs** - Structuring data for AI
- **GraphRAG** - Combining vectors and graph traversal
- **Agent Design** - Tools, reasoning, and action
- **MCP Protocol** - Standard for AI tool integration
- **ETL with Spark** - Loading data to Neo4j
- **Multi-Agent Systems** - Orchestrating multiple agents
- **Aura Agents** - No-code AI interfaces to graph databases

---

## Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **Graph Database** | Data model optimized for relationships |
| **Neo4j Aura** | Fully managed cloud graph service |
| **Aura Agents** | No-code AI agents for conversational graph access |
| **Knowledge Graph** | Entities + relationships extracted from documents |
| **Vector Index** | Enables semantic search on embeddings |
| **MCP** | Open standard for AI tool integration |
| **GraphRAG** | Graph-enhanced retrieval augmented generation |
| **ReAct Pattern** | Reasoning and acting in a loop |

---

## Continue Learning

- [neo4j.com/graphacademy](https://neo4j.com/graphacademy) - Free courses
- [neo4j.com/docs/neo4j-graphrag-python](https://neo4j.com/docs/neo4j-graphrag-python/) - Library docs
- [modelcontextprotocol.io](https://modelcontextprotocol.io) - MCP specification
- [docs.databricks.com](https://docs.databricks.com) - Databricks documentation

---

## Architecture Recap

```
┌─────────────────────────────────────────────────────────────────────┐
│                      COMPLETE WORKSHOP ARCHITECTURE                  │
│                                                                      │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐    │
│  │  Databricks  │     │   AWS AgentCore  │     │  Neo4j Aura  │    │
│  │              │     │                  │     │              │    │
│  │  • Notebooks │────▶│  • MCP Gateway   │────▶│  • Graph DB  │    │
│  │  • ETL       │     │  • Neo4j MCP     │     │  • Vector    │    │
│  │  • AgentBricks│    │  • Claude Agent  │     │  • Explore   │    │
│  │              │     │                  │     │  • Aura Agent│    │
│  └──────────────┘     └──────────────────┘     └──────────────┘    │
│                                                                      │
│  Phase 1: Setup ────▶ Phase 2: Agent ────▶ Phase 3: ETL (Opt) ──▶  │
│  Phase 4: Multi-Agent ────▶ Phase 5: Explore + Aura Agents          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Mission Accomplished!

You've successfully delivered a unified agent platform to **Zenith Horizon Airlines**.

### What You Enabled

- **Maintenance engineers** can now ask about aircraft health in plain English
- **Operations analysts** can query delay patterns without SQL expertise
- **Executives** have a self-service dashboard via Aura Agents
- **Data teams** have a scalable architecture for future expansion

### Thank You!

You've completed the Neo4j + AWS + Databricks hands-on lab!
