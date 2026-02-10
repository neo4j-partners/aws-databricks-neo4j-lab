# The Problem Agents Solve

## Users Don't Know Cypher

Your knowledge graph is powerful, but querying it requires Cypher:

```cypher
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(sys:System)
      -[:HAS_SENSOR]->(s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit)
RETURN sys.name, s.type, ol.minValue, ol.maxValue
```

**Most users can't write this.**

## Users Don't Know Which Retrieval Pattern to Use

Your graph supports multiple retrieval patterns:
- Cypher templates for precise lookups
- Text2Cypher for flexible queries
- Vector similarity search for semantic content
- Cross-link traversal for provenance

**Users just want to ask questions.**

## The Solution

An agent that **understands questions** and **chooses the right approach** automatically.

---

[<- Previous](01-intro.md) | [Next: What is an Aura Agent? ->](03-what-is-aura-agent.md)
