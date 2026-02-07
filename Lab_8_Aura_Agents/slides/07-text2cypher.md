# Text2Cypher Tool

## Natural Language to Database Queries

Text2Cypher uses an LLM to convert questions into Cypher:

```
"Which aircraft has the most critical maintenance events?"
    ↓
MATCH (a:Aircraft)-[:HAS_SYSTEM]->()-[:HAS_COMPONENT]->()
      -[:HAS_EVENT]->(m:MaintenanceEvent {severity: 'Critical'})
RETURN a.tail_number, count(m) AS criticalEvents
ORDER BY criticalEvents DESC LIMIT 1
```

## When to Use

| Question Pattern | Example |
|------------------|---------|
| Counts | "How many flights does ExampleAir operate?" |
| Lists | "List all airports in the route network" |
| Comparisons | "Which aircraft has the most delays?" |
| Specific facts | "What model is aircraft N95040A?" |

## Trade-offs

- **Flexible** - Can answer any structured question
- **Less predictable** - LLM may generate different queries
- **Requires good schema understanding** - LLM needs to know your model

---

[← Previous](06-similarity-search.md) | [Next: Lab Steps →](08-lab-steps.md)
