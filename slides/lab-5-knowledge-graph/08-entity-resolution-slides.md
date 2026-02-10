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


# Entity Resolution

---

## The Duplicate Entity Problem

When entities are extracted from text, the same real-world entity can appear with different names:

- "CFM56-7B" vs "CFM56-7B Engine" vs "CFM56-7B #1"
- "Engine 1" vs "Engine #1" vs "the left engine"
- "High-pressure Turbine" vs "HP Turbine" vs "HPT"

**Without resolution:** Your graph contains multiple nodes representing the same thing.

---

## Why This Breaks Queries

```cypher
// This might miss events if the component appears under different names
MATCH (c:Component {name: 'High-pressure Turbine'})-[:HAS_EVENT]->(m:MaintenanceEvent)
RETURN m.fault
```

If some events are connected to "HP Turbine" and others to "High-pressure Turbine", your query returns incomplete results.

**You can't trust basic queries like "How many faults affect the HP Turbine?"**

---

## Why Entity Resolution Matters

Entity resolution ensures:

- **Query accuracy**: One node per real-world entity
- **Relationship completeness**: All relationships connect to the canonical entity
- **Aggregation correctness**: Counts and summaries reflect reality

---

## Default Resolution in SimpleKGPipeline

By default, `SimpleKGPipeline` performs basic resolution:

- Entities with the **same label** and **identical name** are merged
- "Component: High-pressure Turbine" + "Component: High-pressure Turbine" = one node

**But it misses variations:**
- "HP Turbine" and "hp turbine" (case difference)
- "CFM56-7B" and "CFM56-7B." (punctuation)
- "Engine 1" and "Engine #1" (name variation)

---

## Resolution Trade-offs

<div style="display: flex; gap: 2rem;">

<div style="flex: 1;">

### Too Aggressive

- "CFM56-7B #1" (Engine 1) merged with "CFM56-7B #2" (Engine 2)
- Distinct engines incorrectly combined
- Maintenance history becomes meaningless

</div>

<div style="flex: 1;">

### Too Conservative

- "HP Turbine" and "High-pressure Turbine" remain separate
- Queries miss maintenance events
- Fault counts are wrong

</div>

</div>

**The right balance depends on your domain.**

---

## Resolution Strategies

**Strategy 1: Upstream Normalization**

Guide the LLM during extraction:

```python
prompt_template = """
When extracting component names, normalize to standard names:
- "HP Turbine", "HPT", "High-pressure Turbine" → "High-pressure Turbine"
- "Engine 1", "Engine #1", "left engine" → "CFM56-7B #1"
- Use the full standard name when known
"""
```

---

## Strategy 2: Reference Lists

Provide a canonical list of entities:

```python
prompt_template = """
Only extract components from this approved list:
- High-pressure Turbine
- Low-pressure Compressor
- Combustion Chamber

Match variations to the canonical name.
"""
```

This works well when you know the entities in advance.

---

## Strategy 3: Post-Processing Resolvers

Apply resolvers after extraction:

```python
from neo4j_graphrag.experimental.components.entity_resolvers import FuzzyMatchResolver

resolver = FuzzyMatchResolver(
    driver=driver,
    similarity_threshold=0.85,  # How similar names must be to merge
)

# Run after pipeline completion
resolver.resolve()
```

**Available Resolvers:**
- **SpacySemanticMatchResolver**: Semantic similarity using spaCy
- **FuzzyMatchResolver**: String similarity using RapidFuzz

---

## Disabling Resolution

You can disable entity resolution entirely:

```python
pipeline = SimpleKGPipeline(
    driver=driver,
    llm=llm,
    embedder=embedder,
    entities=entities,
    relations=relations,
    perform_entity_resolution=False,  # No resolution
)
```

Useful for debugging or applying custom resolution logic later.

---

## Validating Resolution

After resolution, verify your entity counts:

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

## Summary

In this lesson, you learned:

- **Entity resolution** merges duplicate nodes representing the same real-world entity
- **Default resolution** catches exact matches only
- **Post-processing resolvers** catch variations using semantic or fuzzy matching
- **The trade-off**: Too aggressive merges distinct entities; too conservative keeps duplicates
- **Strategies include**: Upstream normalization, reference lists, post-processing resolvers

**Next:** Learn about vectors and semantic search.
