---
marp: true
theme: default
paginate: true
---

<style>
section {
  --marp-auto-scaling-code: false;
}

li {
  opacity: 1 !important;
  animation: none !important;
  visibility: visible !important;
}

/* Disable all fragment animations */
.marp-fragment {
  opacity: 1 !important;
  visibility: visible !important;
}

ul > li,
ol > li {
  opacity: 1 !important;
}
</style>


# From Documents to Knowledge Graphs
## with the Neo4j GraphRAG Package

---

## The neo4j-graphrag Python Package

The official Neo4j GenAI package for Python provides a first-party library to integrate Neo4j with generative AI applications.

**Key benefits:**
- Long-term support and fast feature deployment
- Reduces hallucinations through domain-specific context
- Combines knowledge graphs with LLMs for GraphRAG

---

## Supported Providers

**LLMs:**
- OpenAI, Anthropic, Cohere, Google, MistralAI, Ollama

**Embeddings:**
- OpenAI, sentence-transformers, provider-specific models

This flexibility lets you choose the models that best fit your requirements and budget.

---

## Building and Querying

The package provides tools for both constructing and querying knowledge graphs:

| Category | Components |
|----------|------------|
| **Construction** | `SimpleKGPipeline`, `Pipeline` class |
| **Retrieval** | `VectorRetriever`, `Text2CypherRetriever`, hybrid methods |
| **Orchestration** | `GraphRAG` class for retrieval + generation |

---

## SimpleKGPipeline

The key component for graph construction:

**What it does:**
1. Extracts text from documents (PDFs, text files)
2. Breaks text into manageable chunks
3. Uses an LLM to identify entities and relationships
4. Stores the structured data in Neo4j
5. Creates vector embeddings for semantic search

---

## The Transformation Process

| Step | What Happens |
|------|--------------|
| **Document Ingestion** | Read source documents (PDFs) |
| **Chunking** | Break into smaller pieces for processing |
| **Entity Extraction** | LLM identifies aircraft, systems, components, faults |
| **Relationship Extraction** | LLM finds connections between entities |
| **Graph Storage** | Save entities and relationships to Neo4j |
| **Vector Embeddings** | Generate embeddings for semantic search |

---

## The Aircraft Digital Twin Example

Throughout this workshop, you'll work with a knowledge graph built from an Aircraft Digital Twin dataset.

**This dataset models:**
- 20 aircraft across 4 operators (Boeing 737, Airbus A320/A321, Embraer E190)
- Systems per aircraft (engines, avionics, hydraulics)
- Components within systems (turbines, compressors, pumps)
- Sensors generating time-series telemetry (EGT, vibration, fuel flow)
- Flights, delays, and maintenance events

---

## From Tabular Data to Graph

**In flat CSV/tables:** Information is isolated across separate files.

**In a knowledge graph:** It becomes connected and traversable:

```
(Aircraft AC1001)-[:HAS_SYSTEM]->(Engine CFM56-7B #1)
(Engine CFM56-7B #1)-[:HAS_COMPONENT]->(High-pressure Turbine)
(High-pressure Turbine)-[:HAS_EVENT]->(Bearing wear, CRITICAL)
```

---

## The Complete Picture

After processing, your knowledge graph contains:

```
Aircraft → Systems → Components → MaintenanceEvents
                  → Sensors (with embeddings on maintenance chunks)
Aircraft → Flights → Airports
                   → Delays
```

This structure enables questions that traditional RAG can't answer.

---

## What the Graph Enables

| Question Type | How the Graph Helps |
|--------------|---------------------|
| "What maintenance events affect AC1001?" | Traverse HAS_SYSTEM → HAS_COMPONENT → HAS_EVENT |
| "Which flights departed from JFK?" | Follow DEPARTS_FROM relationships |
| "What sensors monitor Engine #1?" | Traverse HAS_SENSOR relationships |
| "How many critical maintenance events?" | Count MaintenanceEvent nodes by severity |

---

## Quality Depends on Decisions

The quality of your knowledge graph depends on several key decisions:

- **Schema design**: What entities and relationships should you extract?
- **Chunking strategy**: How large should chunks be?
- **Entity resolution**: How do you handle the same entity mentioned differently?
- **Prompt engineering**: How do you guide the LLM to extract accurately?

The following lessons cover each of these decisions.

---

## Summary

In this lesson, you learned:

- **neo4j-graphrag** is the official package for building GraphRAG applications
- **SimpleKGPipeline** orchestrates the transformation from documents to graphs
- **The process**: Document → Chunks → Entity Extraction → Relationship Extraction → Graph Storage → Embeddings
- **Graph structure** enables queries that traverse relationships, not just find similar text

**Next:** Learn about schema design in SimpleKGPipeline.
