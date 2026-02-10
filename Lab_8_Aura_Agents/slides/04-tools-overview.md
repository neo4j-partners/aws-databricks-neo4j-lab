# Agent Tools Overview

## Three Retrieval Patterns

| Tool Type | What It Does | Best For |
|-----------|--------------|----------|
| **Cypher Templates** | Run pre-defined queries with parameters | Precise, controlled lookups |
| **Text2Cypher** | Convert questions to Cypher via LLM | Flexible ad-hoc queries |
| **Similarity Search** | Find chunks by semantic meaning | Maintenance procedures, troubleshooting |

## How the Agent Chooses

The agent reads tool descriptions and matches them to questions:

- "Tell me about aircraft N95040A" -> `get_aircraft_overview` (template)
- "What are the sensor limits for N30268B?" -> `get_sensor_limits` (template)
- "Which airports have the most delays?" -> `query_aircraft_graph` (Text2Cypher)
- "How do I troubleshoot engine vibration?" -> `search_maintenance_docs` (similarity)

## Tool Descriptions Matter

Good descriptions help the agent choose the right tool automatically.

---

[<- Previous](03-what-is-aura-agent.md) | [Next: Cypher Templates ->](05-cypher-templates.md)
