# Lab 7: Sample Cypher Queries

Copy and paste these queries into the [Neo4j Aura Query interface](https://console.neo4j.io) to explore the Document-Chunk graph and semantic search capabilities built in this lab.

## Cypher Concepts Used

| Concept | What It Does |
|---|---|
| `MATCH (n:Label)` | Find nodes by label — the starting point for most queries |
| `(a)-[:REL]->(b)` | Traverse a relationship between two nodes (direction matters) |
| `OPTIONAL MATCH` | Like a SQL LEFT JOIN — keeps the row even if the pattern has no match |
| `RETURN ... AS alias` | Project properties and rename columns |
| `count()`, `collect()` | Aggregate functions — count rows or gather values into a list |
| `COALESCE(a, b)` | Returns the first non-null value — useful for handling missing optional matches |
| `substring(str, start, len)` | Extract part of a string — handy for previewing long text |
| `ORDER BY ... DESC` | Sort results (ascending by default) |
| `LIMIT n` | Cap the number of returned rows |
| `db.index.vector.queryNodes()` | Run a vector similarity search against a named vector index |
| `db.index.fulltext.queryNodes()` | Run a keyword search against a named fulltext index |
| `CALL { ... }` | Subquery block — used to scope intermediate results or call procedures |

---

## Document-Chunk Structure

### View all documents and their chunk counts

```sql
MATCH (d:Document)
OPTIONAL MATCH (d)<-[:FROM_DOCUMENT]-(c:Chunk)
RETURN d.documentId AS DocumentId,
       d.title AS Title,
       d.aircraftType AS AircraftType,
       count(c) AS ChunkCount
```

> **Concepts**: `OPTIONAL MATCH` keeps documents even if they have no chunks yet. `count()` aggregates the matched chunks per document.

### Browse the first few chunks of a document

```sql
MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
RETURN c.index AS ChunkIndex,
       substring(c.text, 0, 120) AS Preview,
       d.documentId AS Document
ORDER BY c.index
LIMIT 10
```

> **Concepts**: `substring()` truncates long text for readable output. `ORDER BY c.index` preserves the original document order.

### Walk the chunk chain

```sql
MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
OPTIONAL MATCH (c)-[:NEXT_CHUNK]->(next:Chunk)
RETURN c.index AS ChunkIndex,
       substring(c.text, 0, 80) AS Preview,
       next.index AS NextChunkIndex
ORDER BY c.index
LIMIT 10
```

> **Concepts**: `OPTIONAL MATCH` on `NEXT_CHUNK` keeps the last chunk in the chain (which has no successor). This shows the linked-list structure that preserves reading order.

### Find the first and last chunks

```sql
MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
WHERE NOT EXISTS { (:Chunk)-[:NEXT_CHUNK]->(c) }
   OR NOT EXISTS { (c)-[:NEXT_CHUNK]->(:Chunk) }
RETURN c.index AS ChunkIndex,
       CASE
         WHEN NOT EXISTS { (:Chunk)-[:NEXT_CHUNK]->(c) } THEN 'FIRST'
         ELSE 'LAST'
       END AS Position,
       substring(c.text, 0, 100) AS Preview
ORDER BY c.index
```

> **Concepts**: `EXISTS { pattern }` checks whether a pattern exists in the graph. Negating it finds chain endpoints — the first chunk has no incoming `NEXT_CHUNK`, the last has no outgoing.

---

## Vector Similarity Search

> **Prerequisite:** These queries require the `maintenanceChunkEmbeddings` vector index and embeddings on Chunk nodes, created in notebook 03.

### Search for engine troubleshooting procedures

```sql
// Embed the query text and find the 5 most similar chunks
CALL db.index.vector.queryNodes(
  'maintenanceChunkEmbeddings',
  5,
  genai.vector.encode(
    'How do I troubleshoot engine vibration?',
    'AllMiniLmL6V2'
  )
)
YIELD node, score
RETURN score,
       node.index AS ChunkIndex,
       substring(node.text, 0, 200) AS Content
ORDER BY score DESC
```

> **Concepts**: `db.index.vector.queryNodes()` searches the named vector index and returns matching nodes ranked by cosine similarity. `genai.vector.encode()` generates an embedding from query text using the Aura built-in model.

### Search for hydraulic system limits

```sql
CALL db.index.vector.queryNodes(
  'maintenanceChunkEmbeddings',
  3,
  genai.vector.encode(
    'What are the hydraulic system pressure limits?',
    'AllMiniLmL6V2'
  )
)
YIELD node, score
RETURN score,
       node.index AS ChunkIndex,
       node.text AS FullText
ORDER BY score DESC
```

> **Concepts**: Same pattern as above with `top_k=3`. Returns the full text instead of a substring — useful when you want to read complete procedures.

### Vector search with document metadata

```sql
CALL db.index.vector.queryNodes(
  'maintenanceChunkEmbeddings',
  3,
  genai.vector.encode(
    'EGT limits during takeoff',
    'AllMiniLmL6V2'
  )
)
YIELD node, score
MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)
RETURN score,
       doc.documentId AS Document,
       doc.aircraftType AS AircraftType,
       node.index AS ChunkIndex,
       substring(node.text, 0, 200) AS Content
ORDER BY score DESC
```

> **Concepts**: After the vector search, a `MATCH` traverses `FROM_DOCUMENT` to enrich each result with the source document's metadata. This is the pattern used by VectorCypherRetriever in notebook 04.

---

## Fulltext Keyword Search

> **Prerequisite:** These queries require the `maintenanceChunkText` fulltext index, created in notebook 03.

### Search for a specific term

```sql
CALL db.index.fulltext.queryNodes('maintenanceChunkText', 'V2500')
YIELD node, score
RETURN score,
       node.index AS ChunkIndex,
       substring(node.text, 0, 200) AS Content
ORDER BY score DESC
LIMIT 5
```

> **Concepts**: `db.index.fulltext.queryNodes()` performs keyword search using Lucene scoring. Exact term matches rank highest. Unlike vector search, this finds chunks containing the literal string "V2500".

### Search with multiple keywords

```sql
CALL db.index.fulltext.queryNodes('maintenanceChunkText', 'hydraulic pressure contamination')
YIELD node, score
RETURN score,
       node.index AS ChunkIndex,
       substring(node.text, 0, 200) AS Content
ORDER BY score DESC
LIMIT 5
```

> **Concepts**: Multiple keywords are OR'd together by default — chunks matching more keywords score higher. This is useful for domain-specific terminology where exact terms matter.

---

## Graph-Enhanced Retrieval

### Adjacent chunk retrieval (context window)

```sql
CALL db.index.vector.queryNodes(
  'maintenanceChunkEmbeddings',
  3,
  genai.vector.encode(
    'engine vibration diagnostic procedure',
    'AllMiniLmL6V2'
  )
)
YIELD node, score
OPTIONAL MATCH (prev:Chunk)-[:NEXT_CHUNK]->(node)
OPTIONAL MATCH (node)-[:NEXT_CHUNK]->(next:Chunk)
RETURN node.index AS ChunkIndex,
       score,
       substring(COALESCE(prev.text, ''), 0, 80) AS PreviousChunk,
       substring(node.text, 0, 80) AS MatchedChunk,
       substring(COALESCE(next.text, ''), 0, 80) AS NextChunk
ORDER BY score DESC
```

> **Concepts**: After finding the best-matching chunks, `OPTIONAL MATCH` traverses `NEXT_CHUNK` in both directions to gather surrounding context. `COALESCE(..., '')` handles the first/last chunks that have no predecessor or successor. This is the pattern used by the adjacent-chunk retriever in notebooks 04 and 05.

### Connect chunks to aircraft systems

```sql
CALL db.index.vector.queryNodes(
  'maintenanceChunkEmbeddings',
  3,
  genai.vector.encode(
    'engine fuel pump maintenance',
    'AllMiniLmL6V2'
  )
)
YIELD node, score
MATCH (node)-[:FROM_DOCUMENT]->(doc:Document)
OPTIONAL MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)
  WHERE (node.text CONTAINS 'Engine' AND s.name CONTAINS 'Engine')
     OR (node.text CONTAINS 'Hydraulic' AND s.name CONTAINS 'Hydraulic')
     OR (node.text CONTAINS 'Avionics' AND s.name CONTAINS 'Avionics')
RETURN score,
       doc.aircraftType AS AircraftType,
       node.index AS ChunkIndex,
       substring(node.text, 0, 150) AS Content,
       collect(DISTINCT s.name) AS RelatedSystems,
       collect(DISTINCT a.tail_number) AS AffectedAircraft
ORDER BY score DESC
```

> **Concepts**: Combines vector search with graph traversal to connect maintenance documentation to the aircraft topology from Lab 5. `OPTIONAL MATCH` ensures chunks are returned even if no system keyword matches. `collect(DISTINCT ...)` gathers unique system names and tail numbers per chunk.

---

## Indexes and Schema

### List all indexes

```sql
SHOW INDEXES
```

> **Concepts**: Shows all indexes in the database including the `maintenanceChunkEmbeddings` vector index and `maintenanceChunkText` fulltext index created in notebook 03.

### Verify the vector index

```sql
SHOW INDEXES
YIELD name, type, labelsOrTypes, properties, options
WHERE type = 'VECTOR'
RETURN name, labelsOrTypes, properties, options
```

> **Concepts**: Filters index metadata to show only vector indexes. The `options` column reveals the configured dimensions and similarity function (cosine).

### Verify the fulltext index

```sql
SHOW INDEXES
YIELD name, type, labelsOrTypes, properties
WHERE type = 'FULLTEXT'
RETURN name, labelsOrTypes, properties
```

> **Concepts**: Filters to show only fulltext indexes. Confirms that the `maintenanceChunkText` index covers the `text` property on `Chunk` nodes.

### View the complete graph schema

```sql
CALL db.schema.visualization()
```

> **Concepts**: Introspects the database and returns every node label, relationship type, and how they connect. After Lab 7, you should see Document and Chunk nodes alongside the Aircraft topology from Lab 5.
