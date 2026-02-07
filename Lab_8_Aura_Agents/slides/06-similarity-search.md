# Similarity Search Tool (Optional)

## Semantic Content Discovery

Similarity search finds content by **meaning**, not keywords.

## How It Works

```
User Question: "How do I troubleshoot engine vibration?"
    ↓
Question → Embedding (vector)
    ↓
Find chunks with similar embeddings
    ↓
Return semantically relevant maintenance procedures
```

## Configuration

| Setting | Purpose |
|---------|---------|
| **Embedding Provider** | Must match embeddings in the index |
| **Vector Index** | maintenanceChunkEmbeddings |
| **Top K** | Number of results (e.g., 5) |

## Best For

- "How do I troubleshoot...?"
- "What are the limits for...?"
- Procedural and specification questions

> **Note:** Requires a compatible embedding provider. See the README for details.

---

[← Previous](05-cypher-templates.md) | [Next: Text2Cypher →](07-text2cypher.md)
