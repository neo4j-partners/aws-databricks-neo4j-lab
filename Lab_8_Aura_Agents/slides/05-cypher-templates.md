# Cypher Template Tools

## Controlled, Precise Queries

Cypher templates are pre-defined queries with parameters:

```cypher
MATCH (a:Aircraft {tail_number: $tail_number})-[:HAS_SYSTEM]->(sys:System)
      -[:HAS_SENSOR]->(s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit)
RETURN sys.name AS system, s.type AS sensor_type,
       ol.minValue AS min, ol.maxValue AS max
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
- `get_maintenance_summary` - Events grouped by severity
- `get_sensor_limits` - Operating limits from maintenance manuals
- `find_shared_faults` - Faults two aircraft have in common
- `find_manual` - Maintenance manual for an aircraft

---

[<- Previous](04-tools-overview.md) | [Next: Similarity Search ->](06-similarity-search.md)
