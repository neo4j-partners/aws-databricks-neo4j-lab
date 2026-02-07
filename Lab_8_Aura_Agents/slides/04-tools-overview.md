# Agent Tools Overview

## Retrieval Patterns

| Tool Type | What It Does | Best For |
|-----------|--------------|----------|
| **Cypher Templates** | Run pre-defined queries | Precise, controlled lookups |
| **Text2Cypher** | Convert questions to Cypher | Flexible ad-hoc queries |

## How the Agent Chooses

The agent reads tool descriptions and matches them to questions:

- "Tell me about aircraft N95040A" → `get_aircraft_overview` (template)
- "What faults do two aircraft share?" → `find_shared_faults` (template)
- "Which airports have the most delays?" → `query_aircraft_graph` (Text2Cypher)

## Tool Descriptions Matter

Good descriptions help the agent choose correctly.

---

[← Previous](03-what-is-aura-agent.md) | [Next: Cypher Templates →](05-cypher-templates.md)
