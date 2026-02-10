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


# The Limits of Traditional RAG

---

## RAG Helps, But Introduces New Challenges

We've seen how RAG provides context to LLMs:
- Retrieves relevant chunks based on semantic similarity
- Grounds responses in actual documents
- Reduces hallucination

**But traditional RAG also introduced new problems:**
- Retrieves similar content, not necessarily *relevant* content
- Misses relationships between pieces of information
- Can actually make responses *worse* when context is poor

---

## The Problem with Traditional RAG

Traditional RAG treats documents as isolated, unstructured blobs.

**What traditional RAG sees:**
```
Chunk 1: "Aircraft AC1001 engine reported bearing wear..."
Chunk 2: "Flight FL00123 was delayed 45 minutes at JFK..."
Chunk 3: "EGT sensor readings exceeded threshold on Engine #1..."
```

**What traditional RAG misses:**
- Which flights were delayed because of that bearing wear?
- Is the high EGT reading on the same engine with the fault?
- Which other aircraft share this engine type and might be at risk?

---

## Retrieves Similar Content, Not Connected Information

Traditional RAG can find text about bearing wear and text about flight delays.

**But it can't tell you:**
- Which flights were delayed because of maintenance events on a specific engine

**Why?** Each chunk is independent—there's no understanding of how information connects.

---

## Context ROT: When More Context Makes Things Worse

A surprising discovery: **too much irrelevant context degrades LLM performance**.

**What happens:**
- RAG retrieves chunks that are *similar* but not truly *relevant*
- The LLM's context window fills with tangentially related information
- The model gets confused, distracted, or misled by the noise

**This became known as "Context ROT"** (Retrieval of Tangents)—the retrieved context actually *rots* the quality of the response.

---

## Context ROT: The Research

![bg right:55% contain](../images/context_rot_hero_plot.png)

Research shows that as irrelevant context increases, LLM accuracy **decreases dramatically**.

The graph shows how adding more retrieved chunks often hurts rather than helps.

**Key insight:** Quality of context matters more than quantity.

[Source: Chroma Research - Context ROT](https://research.trychroma.com/context-rot)

---

## Questions Traditional RAG Can't Answer

| Question | Why Traditional RAG Struggles |
|----------|------------------------------|
| "Which aircraft have engines with critical maintenance events?" | Requires traversing Aircraft → System → Component → Event |
| "What components share the same fault types across the fleet?" | Requires finding shared patterns across multiple aircraft |
| "How many flights were delayed due to maintenance?" | Requires aggregation, not similarity search |
| "What sensors are on the same system as a failed component?" | Requires traversing entity relationships |

These questions need *structured context* that preserves relationships.

---

## From Unstructured to Structured

**The core insight:** Information isn't truly unstructured.

Documents contain:
- **Entities**: Aircraft, systems, components, sensors, flights
- **Relationships**: HAS_SYSTEM, HAS_COMPONENT, OPERATES_FLIGHT, HAS_EVENT

Traditional RAG ignores this structure. It treats a document as a bag of words to embed and search.

---

## The GraphRAG Solution

GraphRAG extracts structure, creating a *knowledge graph* that preserves:

- **Entities**: The things mentioned in documents
- **Relationships**: How those things connect
- **Properties**: Attributes and details about entities

**Traditional RAG asks**: "What chunks are similar to this query?"

**GraphRAG asks**: "What entities and relationships are relevant to this query?"

---

![bg contain](../images/graph_mem.jpg)

---

![bg contain](../images/agentic_tools.jpg)

---

## Three Retrieval Patterns

GraphRAG enables three retrieval patterns:

| Pattern | What It Does |
|---------|--------------|
| **Vector search** | Find semantically similar content (what traditional RAG does) |
| **Graph traversal** | Follow relationships from relevant content to connected entities |
| **Database queries** | Answer precise questions about entities and relationships |

The combination is more powerful than any single approach.

---

## Summary

In this lesson, you learned:

- **Traditional RAG helps** but introduces new challenges
- **Context ROT**: Poor retrieval can make responses *worse* than no retrieval
- **The limitation**: Traditional RAG treats documents as isolated blobs, missing relationships
- **Questions requiring relationships** can't be answered with similarity search alone
- **GraphRAG** extracts structure from documents, preserving entities and relationships

**Next:** Learn how to transform documents into knowledge graphs.
