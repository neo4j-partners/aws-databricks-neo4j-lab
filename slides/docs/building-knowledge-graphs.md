# Building Knowledge Graphs

A participant reference covering the GraphRAG pipeline — from documents to a queryable knowledge graph with schema design, chunking, entity resolution, and vector search.

---

## From Documents to Knowledge Graphs

### The neo4j-graphrag Python Package

The official Neo4j GenAI package for Python provides a first-party library to integrate Neo4j with generative AI applications.

**Key benefits:**
- Long-term support and fast feature deployment
- Reduces hallucinations through domain-specific context
- Combines knowledge graphs with LLMs for GraphRAG

**Supported providers:**
- **LLMs:** OpenAI, Anthropic, Cohere, Google, MistralAI, Ollama
- **Embeddings:** OpenAI, sentence-transformers, provider-specific models

### Building and Querying

| Category | Components |
|----------|------------|
| **Construction** | `SimpleKGPipeline`, `Pipeline` class |
| **Retrieval** | `VectorRetriever`, `Text2CypherRetriever`, hybrid methods |
| **Orchestration** | `GraphRAG` class for retrieval + generation |

### SimpleKGPipeline

The key component for graph construction:

1. Extracts text from documents (PDFs, text files)
2. Breaks text into manageable chunks
3. Uses an LLM to identify entities and relationships
4. Stores the structured data in Neo4j
5. Creates vector embeddings for semantic search

### The Transformation Process

| Step | What Happens |
|------|--------------|
| **Document Ingestion** | Read source documents (PDFs) |
| **Chunking** | Break into smaller pieces for processing |
| **Entity Extraction** | LLM identifies aircraft, systems, components, faults |
| **Relationship Extraction** | LLM finds connections between entities |
| **Graph Storage** | Save entities and relationships to Neo4j |
| **Vector Embeddings** | Generate embeddings for semantic search |

### From Tabular Data to Graph

**In flat CSV/tables:** Information is isolated across separate files.

**In a knowledge graph:** It becomes connected and traversable:

```
(Aircraft AC1001)-[:HAS_SYSTEM]->(Engine CFM56-7B #1)
(Engine CFM56-7B #1)-[:HAS_COMPONENT]->(High-pressure Turbine)
(High-pressure Turbine)-[:HAS_EVENT]->(Bearing wear, CRITICAL)
```

### The Complete Picture

After processing, your knowledge graph contains:

```
Aircraft → Systems → Components → MaintenanceEvents
                  → Sensors (with embeddings on maintenance chunks)
Aircraft → Flights → Airports
                   → Delays
```

### What the Graph Enables

| Question Type | How the Graph Helps |
|--------------|---------------------|
| "What maintenance events affect AC1001?" | Traverse HAS_SYSTEM → HAS_COMPONENT → HAS_EVENT |
| "Which flights departed from JFK?" | Follow DEPARTS_FROM relationships |
| "What sensors monitor Engine #1?" | Traverse HAS_SENSOR relationships |
| "How many critical maintenance events?" | Count MaintenanceEvent nodes by severity |

### Quality Depends on Decisions

The quality of your knowledge graph depends on several key decisions:

- **Schema design**: What entities and relationships should you extract?
- **Chunking strategy**: How large should chunks be?
- **Entity resolution**: How do you handle the same entity mentioned differently?
- **Prompt engineering**: How do you guide the LLM to extract accurately?

---

## Schema Design

### Why Schema Matters

Without a schema, extraction is unconstrained — the LLM extracts *everything*.

This creates graphs that are:
- **Non-specific**: Too many entity types with inconsistent labeling
- **Hard to query**: No predictable structure to write queries against
- **Noisy**: Irrelevant entities mixed with important ones

Providing a schema tells the LLM exactly what to look for.

### Three Schema Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **User-Provided** | You define exactly what to extract | Production systems |
| **Extracted** | LLM discovers schema from documents | Exploration |
| **Free** | No constraints, extract everything | Initial discovery |

### User-Provided Schema

```python
schema = {
    "node_types": [
        {"label": "Aircraft", "description": "An individual aircraft in the fleet"},
        {"label": "System", "description": "A major aircraft system (engine, avionics, hydraulics)"},
        {"label": "Component", "description": "A part within a system (turbine, compressor, pump)"},
    ],
    "relationship_types": [
        {"label": "HAS_SYSTEM", "description": "Aircraft contains this system"},
        {"label": "HAS_COMPONENT", "description": "System contains this component"},
    ],
    "patterns": [
        ("Aircraft", "HAS_SYSTEM", "System"),
        ("System", "HAS_COMPONENT", "Component"),
    ]
}
```

### Defining Node Types

Node types can be simple strings or detailed dictionaries:

**Simple:**
```python
node_types = ["Aircraft", "System", "Component"]
```

**With descriptions and properties:**
```python
node_types = [
    {"label": "Aircraft", "description": "An individual aircraft"},
    {
        "label": "Sensor",
        "properties": [{"name": "unit", "type": "STRING"}]
    }
]
```

Descriptions help the LLM understand what each type means.

### Patterns: Valid Connections

Patterns specify which relationships are valid between node types:

```python
patterns = [
    ("Aircraft", "HAS_SYSTEM", "System"),
    ("System", "HAS_COMPONENT", "Component"),
    ("Component", "HAS_EVENT", "MaintenanceEvent"),
]
```

Without patterns, the LLM might create nonsensical relationships like `(Sensor)-[:HAS_SYSTEM]->(Aircraft)`.

### Workshop Schema

**Node Types:**

| Node Type | Description |
|-----------|-------------|
| Aircraft | Individual aircraft with tail number and model |
| System | Engine, Avionics, or Hydraulics system |
| Component | Turbine, Compressor, Pump, etc. |
| Sensor | EGT, Vibration, N1Speed, FuelFlow monitors |
| MaintenanceEvent | Faults with severity (MINOR, MAJOR, CRITICAL) |

**Relationships:**

| Relationship | Pattern |
|-------------|---------|
| HAS_SYSTEM | Aircraft → System |
| HAS_COMPONENT | System → Component |
| HAS_SENSOR | System → Sensor |
| HAS_EVENT | Component → MaintenanceEvent |
| OPERATES_FLIGHT | Aircraft → Flight |

### When to Use Each Mode

| Mode | Best For |
|------|----------|
| **User-Provided** | Production systems with known query patterns |
| **Extracted** | Exploration when you're learning the domain |
| **Free** | Initial discovery of what's in your documents |

For most production GraphRAG applications, a user-provided schema produces the most reliable results.

---

## Chunking Strategies

### Why Chunking Matters

LLMs have context limits. You can't pass an entire 200-page maintenance manual to an LLM for entity extraction. Documents must be broken into smaller pieces — **chunks** — that fit within processing limits.

How you chunk documents affects both **extraction quality** and **retrieval quality**.

### The Dual Impact of Chunk Size

**For Entity Extraction:**
- Larger chunks provide more context for understanding entities
- The LLM sees more surrounding text, making better extraction decisions
- "The engine" can be resolved to "CFM56-7B #1" when full context is visible

**For Retrieval:**
- Smaller chunks enable more precise matches
- When searching, you want the most relevant *portion*, not a huge blob
- Less irrelevant content mixed with relevant content

### The Trade-off

**Large Chunks (2000 chars):**
- Better entity extraction
- Less precise retrieval
- Returns more than needed

**Small Chunks (200 chars):**
- Less context for extraction
- More precise retrieval
- Focused search results

### Chunk Size Parameters

The `FixedSizeSplitter` has two key parameters:

- **`chunk_size`**: Maximum number of characters per chunk
- **`chunk_overlap`**: Characters shared between consecutive chunks

```python
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter

splitter = FixedSizeSplitter(chunk_size=500, chunk_overlap=50)
```

Overlap ensures context isn't lost at chunk boundaries.

### Typical Chunk Sizes

| Chunk Size | Best For |
|------------|----------|
| 200-500 chars | High-precision retrieval, FAQ-style content |
| 500-1000 chars | Balanced extraction and retrieval |
| 1000-2000 chars | Context-heavy extraction, narrative documents |
| 2000+ chars | Maximum context, fewer chunks |

For maintenance manuals with technical, interconnected information, **500-1000 characters** often provides a good balance.

### Evaluating Chunk Quality

After chunking, verify the results:

```cypher
// Check chunk count per document
MATCH (d:Document)<-[:FROM_DOCUMENT]-(c:Chunk)
RETURN d.path, count(c) AS chunkCount
ORDER BY chunkCount DESC

// Check chunk size distribution
MATCH (c:Chunk)
RETURN
    min(size(c.text)) AS minSize,
    max(size(c.text)) AS maxSize,
    avg(size(c.text)) AS avgSize
```

**Good chunks:** Reasonable count per document, consistent sizes, coherent complete thoughts.

**Signs of problems:** Too few chunks (too large), highly variable sizes (inconsistent processing), incomplete sentences (overlap too small).

Start with a moderate size (500-800 characters), evaluate results, and adjust.

---

## Entity Resolution

### The Duplicate Entity Problem

When entities are extracted from text, the same real-world entity can appear with different names:

- "CFM56-7B" vs "CFM56-7B Engine" vs "CFM56-7B #1"
- "Engine 1" vs "Engine #1" vs "the left engine"
- "High-pressure Turbine" vs "HP Turbine" vs "HPT"

Without resolution, your graph contains multiple nodes representing the same thing.

### Why This Breaks Queries

```cypher
// This might miss events if the component appears under different names
MATCH (c:Component {name: 'High-pressure Turbine'})-[:HAS_EVENT]->(m:MaintenanceEvent)
RETURN m.fault
```

If some events are connected to "HP Turbine" and others to "High-pressure Turbine", your query returns incomplete results.

### Resolution Ensures

- **Query accuracy**: One node per real-world entity
- **Relationship completeness**: All relationships connect to the canonical entity
- **Aggregation correctness**: Counts and summaries reflect reality

### Default Resolution in SimpleKGPipeline

By default, `SimpleKGPipeline` performs basic resolution — entities with the same label and identical name are merged.

**But it misses variations:**
- "HP Turbine" and "hp turbine" (case difference)
- "CFM56-7B" and "CFM56-7B." (punctuation)
- "Engine 1" and "Engine #1" (name variation)

### Resolution Trade-offs

**Too Aggressive:**
- "CFM56-7B #1" (Engine 1) merged with "CFM56-7B #2" (Engine 2)
- Distinct engines incorrectly combined
- Maintenance history becomes meaningless

**Too Conservative:**
- "HP Turbine" and "High-pressure Turbine" remain separate
- Queries miss maintenance events
- Fault counts are wrong

The right balance depends on your domain.

### Resolution Strategies

**Strategy 1: Upstream Normalization** — Guide the LLM during extraction:

```python
prompt_template = """
When extracting component names, normalize to standard names:
- "HP Turbine", "HPT", "High-pressure Turbine" → "High-pressure Turbine"
- "Engine 1", "Engine #1", "left engine" → "CFM56-7B #1"
- Use the full standard name when known
"""
```

**Strategy 2: Reference Lists** — Provide a canonical list of entities:

```python
prompt_template = """
Only extract components from this approved list:
- High-pressure Turbine
- Low-pressure Compressor
- Combustion Chamber

Match variations to the canonical name.
"""
```

**Strategy 3: Post-Processing Resolvers** — Apply resolvers after extraction:

```python
from neo4j_graphrag.experimental.components.entity_resolvers import FuzzyMatchResolver

resolver = FuzzyMatchResolver(
    driver=driver,
    similarity_threshold=0.85,
)
resolver.resolve()
```

Available resolvers: **SpacySemanticMatchResolver** (semantic similarity using spaCy) and **FuzzyMatchResolver** (string similarity using RapidFuzz).

### Validating Resolution

After resolution, verify entity counts:

```cypher
// Check for potential duplicates
MATCH (c:Component)
WITH c.name AS name, collect(c) AS nodes
WHERE size(nodes) > 1
RETURN name, size(nodes) AS duplicates

// Check component name variations
MATCH (c:Component)
WHERE c.name CONTAINS 'Turbine' OR c.name CONTAINS 'turbine'
RETURN c.name, count{(c)-[:HAS_EVENT]->()} AS events
```

---

## Vectors and Semantic Search

### What is a Vector?

Vectors are lists of numbers. The vector `[1, 2, 3]` represents a point in three-dimensional space. In machine learning, vectors can represent much more complex data — including the *meaning* of text.

### What are Embeddings?

Embeddings are numerical representations of text encoded as high-dimensional vectors (often 1,536 dimensions).

**The key property:** Similar meanings produce similar vectors.

- "Engine bearing wear requires replacement" and "turbine component degradation" → vectors close together
- "Engine bearing wear requires replacement" and "flight departed from JFK" → vectors far apart

This enables **semantic search** — finding content by meaning, not just keywords.

### Why Vectors Matter for GraphRAG

Your knowledge graph has structured entities, relationships, and text chunks from source documents. Vectors let you *find* relevant information when a user asks a question.

**Without vectors:**
- You need exact keyword matches
- "What engine problems occurred?" won't find chunks about "bearing wear" or "vibration exceedance"

**With vectors:**
- The question and chunks become embeddings
- You find chunks with similar *meaning*, regardless of exact words
- "Engine problems" finds content about "bearing wear" and "overheat"

### Similarity Search

Vector similarity is typically measured by **cosine similarity** — the angle between two vectors:

| Score | Meaning |
|-------|---------|
| Near 1.0 | Very similar meanings |
| Near 0.5 | Somewhat related |
| Near 0.0 | Unrelated |

### Storing Vectors in Neo4j

When SimpleKGPipeline processes documents:

1. Each chunk gets an embedding from the embedding model
2. The embedding is stored as a property on the Chunk node
3. A vector index enables fast similarity search across all chunks

```cypher
MATCH (c:Chunk)
RETURN c.text, size(c.embedding) AS embeddingDimensions
LIMIT 1
```

### Combining Vectors with Graph Traversal

The real power of GraphRAG — start with semantic search, then traverse the graph:

```cypher
CALL db.index.vector.queryNodes('maintenanceChunkEmbeddings', 5, queryEmbedding)
YIELD node, score

// Traverse from chunk to its parent document
MATCH (node)-[:FROM_DOCUMENT]->(d:Document)
RETURN node.text AS content, score, d.path AS sourceDocument
```

Returns both similar text AND the source document it came from.

### The Complete Knowledge Graph

Your knowledge graph now has everything needed for GraphRAG:

| Component | Purpose |
|-----------|---------|
| **Documents** | Source provenance |
| **Chunks** | Searchable text units |
| **Embeddings** | Enable semantic search |
| **Entities** | Structured domain knowledge |
| **Relationships** | Connections between entities |

### Three Retrieval Patterns

This structure enables three retrieval patterns:

1. **Vector search**: Find semantically similar content
2. **Vector + Graph**: Find similar content, then traverse to related entities
3. **Text2Cypher**: Query the graph structure directly

These patterns are covered in detail in Lab 7.
