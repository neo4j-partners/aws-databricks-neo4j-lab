# The Problem Agents Solve

## Users Don't Know Cypher

Your knowledge graph is powerful, but querying it requires Cypher:

```cypher
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)
      -[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
WHERE a.tail_number = 'N95040A' AND m.severity = 'Critical'
RETURN c.name, m.fault
```

**Most users can't write this.**

## Users Don't Know Retriever Types

You have different retrieval patterns:
- Cypher templates for precise lookups
- Text2Cypher for flexible queries
- Graph traversal for relationships

**Users just want to ask questions.**

## The Solution

An agent that **understands questions** and **chooses the right approach** automatically.

---

[← Previous](01-intro.md) | [Next: What is an Aura Agent? →](03-what-is-aura-agent.md)
