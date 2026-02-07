# Cypher Template Tools

## Controlled, Precise Queries

Cypher templates are pre-defined queries with parameters:

```cypher
MATCH (a:Aircraft {tail_number: $tail_number})
      -[:HAS_SYSTEM]->(s:System)
      -[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
RETURN a.tail_number, s.name, c.name, m.fault, m.severity
```

## Why Use Templates?

| Benefit | Description |
|---------|-------------|
| **Predictable** | Same query every time |
| **Optimized** | You control the query structure |
| **Secure** | No arbitrary query generation |
| **Fast** | No LLM query generation overhead |

## Templates You'll Create

- `get_aircraft_overview` - Aircraft info + systems + maintenance events
- `find_shared_faults` - Faults two aircraft have in common
- `get_maintenance_summary` - Events grouped by severity

---

[← Previous](04-tools-overview.md) | [Next: Similarity Search →](06-similarity-search.md)
