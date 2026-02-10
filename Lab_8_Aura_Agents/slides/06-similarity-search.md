# Similarity Search Tool

## Semantic Content Discovery

Similarity search finds content by **meaning**, not keywords.

## How It Works

```
User Question: "How do I troubleshoot engine vibration?"
    |
Question -> Embedding (OpenAI text-embedding-3-small)
    |
Find chunks with similar embeddings (vector index)
    |
Return semantically relevant maintenance procedures
```

## Configuration

| Setting | Value |
|---------|-------|
| **Embedding Provider** | OpenAI (same key used during `enrich`) |
| **Vector Index** | `maintenanceChunkEmbeddings` on Chunk.embedding |
| **Top K** | 5 results |

## Best For

- "How do I troubleshoot engine vibration?"
- "What are the EGT limits during takeoff?"
- "What is the engine inspection schedule?"

The graph contains ~154 embedded chunks from three maintenance manuals (A320-200, A321neo, B737-800).

---

[<- Previous](05-cypher-templates.md) | [Next: Text2Cypher ->](07-text2cypher.md)
