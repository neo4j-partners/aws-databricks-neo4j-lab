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


# Schema Design in SimpleKGPipeline

---

## Why Schema Matters

Without a schema, extraction is unconstrained—the LLM extracts *everything*.

**This creates graphs that are:**
- **Non-specific**: Too many entity types with inconsistent labeling
- **Hard to query**: No predictable structure to write queries against
- **Noisy**: Irrelevant entities mixed with important ones

Providing a schema tells the LLM exactly what to look for.

---

## Schema in SimpleKGPipeline

SimpleKGPipeline accepts a `schema` parameter that guides extraction:

- **Node types**: What kinds of entities should be extracted
- **Relationship types**: What connections between entities matter
- **Patterns**: Which node-relationship-node combinations are valid

The pipeline uses the schema to guide extraction, prune invalid data, and ensure consistency.

---

## Three Schema Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **User-Provided** | You define exactly what to extract | Production systems |
| **Extracted** | LLM discovers schema from documents | Exploration |
| **Free** | No constraints, extract everything | Initial discovery |

---

## User-Provided Schema

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

---

## Automatic Schema Extraction

Let the LLM discover the schema from your documents:

```python
pipeline = SimpleKGPipeline(
    driver=driver,
    llm=llm,
    embedder=embedder,
    schema="EXTRACTED",  # or simply omit schema
)
```

Useful when you don't know what entities exist in your documents.

---

## Free Mode

Extract everything without constraints:

```python
pipeline = SimpleKGPipeline(
    driver=driver,
    llm=llm,
    embedder=embedder,
    schema="FREE",
)
```

Most comprehensive extraction, but inconsistent structure.

---

## Defining Node Types

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

---

## Patterns: Valid Connections

Patterns specify which relationships are valid between node types:

```python
patterns = [
    ("Aircraft", "HAS_SYSTEM", "System"),
    ("System", "HAS_COMPONENT", "Component"),
    ("Component", "HAS_EVENT", "MaintenanceEvent"),
]
```

Without patterns, the LLM might create nonsensical relationships like:
`(Sensor)-[:HAS_SYSTEM]->(Aircraft)`

---

## Schema for This Workshop

| Node Type | Description |
|-----------|-------------|
| Aircraft | Individual aircraft with tail number and model |
| System | Engine, Avionics, or Hydraulics system |
| Component | Turbine, Compressor, Pump, etc. |
| Sensor | EGT, Vibration, N1Speed, FuelFlow monitors |
| MaintenanceEvent | Faults with severity (MINOR, MAJOR, CRITICAL) |

---

## Relationships for This Workshop

| Relationship | Pattern |
|-------------|---------|
| HAS_SYSTEM | Aircraft → System |
| HAS_COMPONENT | System → Component |
| HAS_SENSOR | System → Sensor |
| HAS_EVENT | Component → MaintenanceEvent |
| OPERATES_FLIGHT | Aircraft → Flight |

This focuses on the aircraft topology and maintenance tracking.

---

## When to Use Each Mode

| Mode | Best For |
|------|----------|
| **User-Provided** | Production systems with known query patterns |
| **Extracted** | Exploration when you're learning the domain |
| **Free** | Initial discovery of what's in your documents |

For most production GraphRAG applications, a user-provided schema produces the most reliable results.

---

## Learn More

This lesson covers how to use schemas in SimpleKGPipeline.

For deep dives into schema design principles—including iterative refinement, domain modeling, and advanced patterns—see the dedicated **Neo4j GraphRAG Python course** on GraphAcademy.

---

## Summary

In this lesson, you learned:

- **Schema guides extraction**: Tells SimpleKGPipeline what to find
- **Three modes**: User-provided (control), Extracted (discovery), Free (exploration)
- **Node and relationship types**: Define what to extract with optional descriptions
- **Patterns**: Specify valid connections between node types
- **Production systems**: Benefit most from user-provided schemas

**Next:** Learn about chunking strategies and their trade-offs.
