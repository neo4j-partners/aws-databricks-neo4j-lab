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


# Vectors and Semantic Search

---

## What is a Vector?

Vectors are lists of numbers.

The vector `[1, 2, 3]` represents a point in three-dimensional space.

In machine learning, vectors can represent much more complex data—including the *meaning* of text.

---

## What are Embeddings?

Embeddings are numerical representations of text encoded as high-dimensional vectors (often 1,536 dimensions).

**The key property:** Similar meanings produce similar vectors.

- "Engine bearing wear requires replacement" and "turbine component degradation" → vectors close together
- "Engine bearing wear requires replacement" and "flight departed from JFK" → vectors far apart

This enables **semantic search**—finding content by meaning, not just keywords.

---

## Why Vectors Matter for GraphRAG

Your knowledge graph now has:
- Structured entities (aircraft, systems, components, sensors)
- Relationships (HAS_SYSTEM, HAS_COMPONENT, HAS_EVENT)
- Text chunks from source documents

**But how do you *find* relevant information when a user asks a question?**

---

## Without Vectors vs With Vectors

**Without vectors:**
- You need exact keyword matches
- "What engine problems occurred?" won't find chunks about "bearing wear" or "vibration exceedance"

**With vectors:**
- The question and chunks become embeddings
- You find chunks with similar *meaning*, regardless of exact words
- "Engine problems" finds content about "bearing wear" and "overheat"

---

## Similarity Search

Vector similarity is typically measured by **cosine similarity**—the angle between two vectors:

| Score | Meaning |
|-------|---------|
| Near 1.0 | Very similar meanings |
| Near 0.5 | Somewhat related |
| Near 0.0 | Unrelated |

When you search, your question becomes an embedding, and the system finds chunks with embeddings close to your question.

---

## Storing Vectors in Neo4j

When SimpleKGPipeline processes documents:

1. Each chunk gets an embedding from the embedding model
2. The embedding is stored as a property on the Chunk node
3. A vector index enables fast similarity search across all chunks

```cypher
// Chunks have embedding properties
MATCH (c:Chunk)
RETURN c.text, size(c.embedding) AS embeddingDimensions
LIMIT 1
```

---

## Searching a Vector Index

```cypher
// Create an embedding for the query
WITH genai.vector.encode(
    "What maintenance issues affect the turbine?",
    "OpenAI",
    { token: $apiKey }
) AS queryEmbedding

// Search the vector index for similar chunks
CALL db.index.vector.queryNodes('maintenanceChunkEmbeddings', 5, queryEmbedding)
YIELD node, score

RETURN node.text AS content, score
ORDER BY score DESC
```

This finds the 5 chunks most semantically similar to the query.

---

## Combining Vectors with Graph Traversal

**The real power of GraphRAG:** Start with semantic search, then traverse the graph.

```cypher
WITH genai.vector.encode(
    "What maintenance issues affect the turbine?",
    "OpenAI",
    { token: $apiKey }
) AS queryEmbedding

CALL db.index.vector.queryNodes('maintenanceChunkEmbeddings', 5, queryEmbedding)
YIELD node, score

// Traverse from chunk to its parent document
MATCH (node)-[:FROM_DOCUMENT]->(d:Document)
RETURN node.text AS content, score, d.path AS sourceDocument
```

Returns both similar text AND the source document it came from.

---

## The Complete Knowledge Graph

Your knowledge graph now has everything needed for GraphRAG:

| Component | Purpose |
|-----------|---------|
| **Documents** | Source provenance |
| **Chunks** | Searchable text units |
| **Embeddings** | Enable semantic search |
| **Entities** | Structured domain knowledge |
| **Relationships** | Connections between entities |

---

## Three Retrieval Patterns

This structure enables three retrieval patterns:

1. **Vector search**: Find semantically similar content
2. **Vector + Graph**: Find similar content, then traverse to related entities
3. **Text2Cypher**: Query the graph structure directly

You'll learn these patterns in detail in Lab 7.

---

## Summary

In this lesson, you learned:

- **Vectors** are numerical representations of data
- **Embeddings** encode text meaning as high-dimensional vectors
- **Similar meanings** produce similar vectors, enabling semantic search
- **Neo4j stores vectors** alongside graph data with vector indexes
- **Semantic search** finds relevant chunks by meaning, not keywords
- **Vector + Graph** combines semantic search with relationship traversal

**Your knowledge graph is complete.** In Lab 7, you'll learn how to retrieve context using Vector, Vector Cypher, and Text2Cypher retrievers.
