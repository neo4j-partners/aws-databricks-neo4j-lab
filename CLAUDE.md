# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a hands-on workshop teaching GraphRAG (Graph Retrieval-Augmented Generation) using Neo4j and AWS Bedrock. The workshop uses SEC 10-K filings as the dataset and progresses from no-code tools to building custom agents.

## Workshop Structure

- **Part 1 (Labs 0-2)**: No-code exploration using Neo4j Aura console and Aura Agents visual builder
- **Part 2 (Labs 4-5)**: Python-based GraphRAG with LangGraph and neo4j-graphrag library
- **Part 3 (Labs 6-7)**: Advanced API integration and MCP (Model Context Protocol) agents

## Key Configuration

Credentials are entered directly in each notebook's Configuration cell. Each notebook has a section at the top where users set:

```python
NEO4J_URI = "neo4j+s://xxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "..."
```

Databricks notebooks use Foundation Model APIs (MLflow deployments client) which handle authentication automatically when running in Databricks.

## Lab Code Patterns

### Lab 4 - Basic LangGraph Agent
Location: `Lab_4_Intro_to_Bedrock_and_Agents/basic_langgraph_agent.ipynb`

Uses `ChatBedrockConverse` from langchain-aws with the ReAct pattern:
```python
from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
```

For cross-region inference profiles (MODEL_ID starting with `us.` or `global.`), derive base_model_id:
```python
if MODEL_ID.startswith("us.anthropic."):
    BASE_MODEL_ID = MODEL_ID.replace("us.anthropic.", "anthropic.")
```

### Lab 5 - GraphRAG
Location: `Lab_5_GraphRAG/`

Uses a forked neo4j-graphrag with Bedrock support:
```bash
pip install "neo4j-graphrag[bedrock] @ git+https://github.com/neo4j-partners/neo4j-graphrag-python.git@bedrock-embeddings"
```

Key utility classes in `data_utils.py`:
- `Neo4jConnection`: Manages driver connection (credentials passed explicitly)
- `get_embedder()`: Returns `DatabricksEmbeddings` using Foundation Model APIs
- `get_llm()`: Returns `DatabricksLLM` using Foundation Model APIs
- `split_text()`: Wraps `FixedSizeSplitter` with async handling for Jupyter

Graph structure for chunked documents:
```
(:Document) <-[:FROM_DOCUMENT]- (:Chunk) -[:NEXT_CHUNK]-> (:Chunk)
```

### Lab 6 - Aura Agents API
Location: `Lab_6_Aura_Agents_API/aura_agent_client.ipynb`

Contains `AuraAgentClient` class for OAuth2 authentication and agent invocation:
- Token URL: `https://api.neo4j.io/oauth/token`
- Uses client credentials flow with Basic Auth
- Tokens cached and auto-refreshed on 401

### Lab 7 - MCP Agent
Location: `Lab_7_Neo4j_MCP_Agent/`

Two implementations:
- `neo4j_langgraph_mcp_agent.ipynb`: LangGraph + langchain-mcp-adapters
- `neo4j_strands_mcp_agent.ipynb`: Alternative using Strands framework

MCP connection pattern:
```python
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
```

## Knowledge Graph Schema

The SEC 10-K dataset includes:
- **Nodes**: Document, Chunk, Company, Product, RiskFactor, Executive, FinancialMetric, AssetManager
- **Relationships**: FROM_DOCUMENT, NEXT_CHUNK, FROM_CHUNK, FACES_RISK, OFFERS, HAS_EXECUTIVE, REPORTS, OWNS
- **Vector Index**: `chunkEmbeddings` on Chunk.embedding (1024 dims for Titan, 1536 for OpenAI)
- **Fulltext Indexes**: `chunkText`, `search_entities`

## Running Notebooks

The notebooks are designed for Databricks but can be adapted locally:
1. Enter Neo4j credentials in each notebook's Configuration cell
2. Install dependencies per notebook (uses `%pip install`)
3. Databricks Foundation Model APIs require a Databricks workspace

## Dependencies

Lab 5 uses `pyproject.toml` at `Lab_5_GraphRAG/src/pyproject.toml`:
- Python 3.11+
- neo4j-graphrag
- mlflow, nest-asyncio
