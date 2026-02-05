# Lab 6 - Semantic Search for Aircraft Maintenance

In this lab, you'll add semantic search capabilities to your aircraft knowledge graph. Building on the aircraft topology loaded in Lab 5, you'll create a Document-Chunk structure for the A320-200 Maintenance Manual and enable AI-powered retrieval of maintenance procedures.

## Prerequisites

Before starting, make sure you have:
- Completed **Lab 5** (Databricks ETL) to load the aircraft graph (Aircraft, System, Component nodes)
- Neo4j Aura credentials from Lab 1 (URI, username, password)
- Running in a **Databricks notebook environment** (for Foundation Model API access)
- **Maintenance manual uploaded** to the Unity Catalog Volume (see `lab_setup/README.md`)

## Lab Overview

This lab consists of two notebooks that add semantic search to your existing knowledge graph:

### 01_data_and_embeddings.ipynb - Data Preparation
Build the foundation for semantic search over maintenance documentation:
- Understand the Document -> Chunk graph structure
- Load the A320-200 Maintenance Manual into Neo4j
- Create Document and Chunk nodes with relationships
- Generate embeddings using Databricks Foundation Model APIs (BGE-large)
- Create a vector index in Neo4j
- Perform similarity search to find relevant maintenance procedures

### 02_graphrag_retrievers.ipynb - Retrieval Strategies
Learn retrieval patterns from simple to graph-enhanced:
- Set up a VectorRetriever using Neo4j's vector index
- Use GraphRAG to combine vector search with LLM-generated answers
- Create custom Cypher queries with VectorCypherRetriever
- Connect maintenance documentation to your aircraft topology
- Compare standard vs. graph-enhanced retrieval results

## Knowledge Graph Structure

After completing this lab, your knowledge graph will combine:

**From Lab 5 (Structured Data):**
```
(:Aircraft)-[:HAS_SYSTEM]->(:System)-[:HAS_COMPONENT]->(:Component)
```

**From Lab 6 (Unstructured Data):**
```
(:Document) <-[:FROM_DOCUMENT]- (:Chunk) -[:NEXT_CHUNK]-> (:Chunk)
```

## Databricks Foundation Model APIs

This lab uses Databricks-hosted embedding and LLM models:

### Embedding Models
| Model | Dimensions | Context | Best For |
|-------|------------|---------|----------|
| `databricks-bge-large-en` | 1024 | 512 tokens | Short text, fast |
| `databricks-gte-large-en` | 1024 | 8192 tokens | Long documents |

### LLM Models
| Model | Description |
|-------|-------------|
| `databricks-meta-llama-3-3-70b-instruct` | Llama 3.3 70B (default) |
| `databricks-dbrx-instruct` | DBRX Instruct |
| `databricks-mixtral-8x7b-instruct` | Mixtral 8x7B |

These models are pre-deployed and ready to use via the MLflow deployments client.

## Maintenance Manual Content

The A320-200 Maintenance and Troubleshooting Manual is loaded from the Unity Catalog Volume at:
```
/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/MAINTENANCE_A320.md
```

This comprehensive manual includes:

- **Aircraft Overview**: Fleet configuration (5 aircraft), specifications
- **System Architecture**: Engine (V2500-A1), Avionics, Hydraulics systems
- **Troubleshooting Procedures**: EGT overheat, vibration exceedance, fuel starvation, bearing wear
- **Fault Codes**: Complete reference for Engine, Avionics, and Hydraulics faults
- **Decision Trees**: Diagnostic flows for common issues
- **Scheduled Maintenance**: Inspection intervals and task cards

## Sample Queries

After completing this lab, you can ask questions like:
- "How do I troubleshoot engine vibration?"
- "What are the EGT limits during takeoff?"
- "What causes hydraulic pressure loss?"
- "When should I replace the fuel filter?"
- "What oil analysis levels indicate bearing wear?"

## Configuration

Each notebook has a **Configuration** cell at the top where you enter your Neo4j credentials:

```python
NEO4J_URI = ""  # e.g., "neo4j+s://xxxxxxxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = ""  # Your password from Lab 1
```

The embedding and LLM models use Databricks Foundation Model APIs which are pre-deployed and require no additional configuration. When running in Databricks, the MLflow deployments client automatically handles authentication.

## Key Concepts

- **Chunks**: Smaller pieces of text split from the maintenance manual for efficient retrieval
- **Embeddings**: 1024-dimensional vectors (BGE-large) that capture semantic meaning
- **Vector Index**: Enables fast similarity search across embeddings
- **VectorRetriever**: Simple semantic search over embedded chunks
- **VectorCypherRetriever**: Graph-enhanced retrieval using custom Cypher queries
- **GraphRAG**: Combining retrieval with LLM generation for context-aware answers

## Getting Started

1. Ensure Lab 5 is complete (aircraft topology loaded)
2. Verify the maintenance manual is uploaded to the Volume:
   ```
   /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/MAINTENANCE_A320.md
   ```
3. Upload the notebook files and `data_utils.py` to your Databricks workspace
4. Open `01_data_and_embeddings.ipynb`
5. Enter your Neo4j credentials in the Configuration cell
6. Run cells sequentially to load the maintenance manual and create embeddings
7. Continue to `02_graphrag_retrievers.ipynb` for retrieval strategies

## Files

| File | Description |
|------|-------------|
| `01_data_and_embeddings.ipynb` | Data loading and embedding generation |
| `02_graphrag_retrievers.ipynb` | Retrieval strategies and GraphRAG |
| `data_utils.py` | Utility functions for Neo4j and Databricks |
| `maintenance_manual.md` | Local copy of A320-200 Maintenance Manual (for reference) |
| `README.md` | This file |

**Note:** The `MAINTENANCE_A320.md` file from `lab_setup/aircraft_digital_twin_data/` must be uploaded to the Unity Catalog Volume before running the notebooks. See `lab_setup/README.md` for upload instructions.

## Technical Details

### Embedding Generation
The `DatabricksEmbeddings` class uses the MLflow deployments client:

```python
import mlflow.deployments
client = mlflow.deployments.get_deploy_client("databricks")
response = client.predict(
    endpoint="databricks-bge-large-en",
    inputs={"input": ["text to embed"]},
)
embedding = response["data"][0]["embedding"]  # 1024-dim vector
```

### API Format
Databricks Foundation Models use OpenAI-compatible format:
- **Input**: `{"input": ["text1", "text2"]}`
- **Output**: `{"data": [{"embedding": [0.1, ...]}, ...]}`
