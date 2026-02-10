# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a hands-on workshop teaching AI agents and GraphRAG using Neo4j, AWS, and Databricks. The workshop uses an Aircraft Digital Twin dataset and progresses from setup through ETL, multi-agent orchestration, and semantic search across three platforms (AWS AgentCore, Databricks AgentBricks, Neo4j Aura Agents).

## Workshop Structure

- **Phase 1 (Labs 0-1)**: Environment setup — AWS console sign-in, Neo4j Aura database creation, backup restore
- **Phase 2 (Lab 4)**: AWS AgentCore — Explore pre-deployed multi-agent orchestrator with Neo4j MCP
- **Phase 3 (Labs 5-6)**: Databricks ETL + Multi-Agent Analytics — Load Aircraft Digital Twin to Neo4j, build multi-agent supervisor with Genie Space + Neo4j MCP
- **Phase 4 (Lab 7)**: Semantic Search / GraphRAG — Add embeddings and GraphRAG retrievers
- **Phase 5 (Lab 8)**: Neo4j Aura Agents — No-code agent with Cypher Templates and Text2Cypher

## Key Configuration

Credentials are entered directly in each notebook's Configuration cell. Each notebook has a section at the top where users set:

```python
NEO4J_URI = "neo4j+s://xxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "..."
```

Databricks notebooks use Foundation Model APIs (MLflow deployments client) which handle authentication automatically when running in Databricks.

## Lab Code Patterns

### Lab 4 - AWS AgentCore
Location: `Lab_4_AWS_Agent_Core/`

Pre-deployed multi-agent orchestrator using AgentCore with Neo4j MCP Server. Setup code in `setup/`:
- `orchestrator_agent.py`: Main routing agent
- `maintenance_agent.py`, `operations_agent.py`: Specialist agents
- `invoke_agent.py`: Python client for calling agents
- Uses Neo4j MCP tools: `get-schema` (read-only) and `read-cypher`

### Lab 5 - Databricks ETL to Neo4j
Location: `Lab_5_Databricks_ETL_Neo4j/`

Two notebooks:
- `01_aircraft_etl_to_neo4j.ipynb`: Loads Aircraft, System, Component nodes using Neo4j Spark Connector
- `02_load_neo4j_full.ipynb`: Loads full dataset (Sensors, Flights, Airports, Delays, MaintenanceEvents, Removals) using Python neo4j driver

Data is read from Unity Catalog Volume: `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/`

### Lab 6 - AgentBricks
Location: `Lab_6_AgentBricks/`

Documentation-only lab (no notebooks):
- `PART_A.md`: Create Genie Space for aircraft sensor analytics over Unity Catalog tables
- `PART_B.md`: Create Multi-Agent Supervisor combining Genie Space + Neo4j MCP agent

Data sources: `aws-databricks-neo4j-lab.lakehouse` (sensor tables) and Neo4j MCP connection

### Lab 7 - Semantic Search / GraphRAG
Location: `Lab_7_Semantic_Search/`

Three notebooks + utility module:
- `03_data_and_embeddings.ipynb`: Loads A320-200 Maintenance Manual, creates Document/Chunk nodes, generates embeddings, creates vector + fulltext indexes
- `04_graphrag_retrievers.ipynb`: VectorRetriever, VectorCypherRetriever, GraphRAG pipeline
- `05_hybrid_retrievers.ipynb`: HybridRetriever, HybridCypherRetriever (optional)

Key utility classes in `data_utils.py`:
- `Neo4jConnection`: Manages driver connection (credentials passed explicitly)
- `DatabricksEmbeddings`: Embedder using Foundation Model APIs (BGE-large, 1024 dims)
- `DatabricksLLM`: LLM using Foundation Model APIs (Llama 3.3 70B)
- `get_embedder()`, `get_llm()`: Factory functions
- `split_text()`: Wraps `FixedSizeSplitter` with async handling for Jupyter

Graph structure for chunked documents:
```
(:Document) <-[:FROM_DOCUMENT]- (:Chunk) -[:NEXT_CHUNK]-> (:Chunk)
```

### Lab 8 - Aura Agents
Location: `Lab_8_Aura_Agents/`

No-code lab using Neo4j Aura Agents console:
- Part A: Explore the Aircraft Digital Twin graph with Cypher queries
- Part B: Build an agent with Cypher Template tools, Text2Cypher tool
- `slides/`: 12 presentation slides

## Knowledge Graph Schema

The Aircraft Digital Twin dataset includes:
- **Nodes**: Aircraft, System, Component, Sensor, Airport, Flight, Delay, MaintenanceEvent, Removal, Document, Chunk
- **Relationships**: HAS_SYSTEM, HAS_COMPONENT, HAS_SENSOR, HAS_EVENT, OPERATES_FLIGHT, DEPARTS_FROM, ARRIVES_AT, HAS_DELAY, AFFECTS_SYSTEM, AFFECTS_AIRCRAFT, HAS_REMOVAL, REMOVED_COMPONENT, FROM_DOCUMENT, NEXT_CHUNK
- **Vector Index**: `maintenanceChunkEmbeddings` on Chunk.embedding (1024 dims, Databricks BGE-large)
- **Fulltext Index**: `maintenanceChunkText` on Chunk.text

## Running Notebooks

The notebooks are designed for Databricks:
1. Enter Neo4j credentials in each notebook's Configuration cell
2. Install dependencies per notebook (uses `%pip install`)
3. Databricks Foundation Model APIs require a Databricks workspace

## Admin Setup

Lab setup automation is in `lab_setup/`:
- `auto_scripts/`: CLI tool for cluster creation, data upload, table creation, warehouse setup
- `aircraft_digital_twin_data/`: CSV data files and maintenance manuals
- `scripts/`: Shell scripts for external location setup
- `docs/`: Manual setup and workspace configuration guides
