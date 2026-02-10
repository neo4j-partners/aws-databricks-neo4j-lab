# Text2Cypher Tool

## Natural Language to Database Queries

Text2Cypher uses an LLM to convert questions into Cypher:

```
"Which aircraft has the most critical maintenance events?"
    |
MATCH (me:MaintenanceEvent {severity: 'CRITICAL'})-[:AFFECTS_AIRCRAFT]->(a:Aircraft)
RETURN a.tail_number, count(me) AS criticalEvents
ORDER BY criticalEvents DESC LIMIT 1
```

## When to Use

| Question Pattern | Example |
|------------------|---------|
| Aggregations | "Which aircraft has the most delays?" |
| Cross-entity | "Which sensors have operating limits defined?" |
| Comparisons | "What are the top causes of flight delays?" |
| Provenance | "Trace the EGT limit back to its source manual" |

## Trade-offs

- **Flexible** - Can answer any structured question about the graph
- **Less predictable** - LLM may generate different queries
- **Requires good schema understanding** - LLM reads the graph schema

---

[<- Previous](06-similarity-search.md) | [Next: Lab Steps ->](08-lab-steps.md)
