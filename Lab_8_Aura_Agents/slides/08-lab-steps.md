# Lab Steps

## Step 1: Create the Agent

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Select **Agents** → **Create Agent**
3. Configure:
   - **Name:** `aircraft-analyst`
   - **Target Instance:** Your Aura database
   - **External Endpoint:** Enabled

## Step 2: Write Agent Instructions

```
You are an expert aircraft maintenance and operations analyst.
You help users understand:
- Aircraft topology: systems, components, sensors
- Maintenance events: faults, severity, corrective actions
- Flight operations: routes, delays, operator performance
- Component removals and cross-entity patterns
```

Good instructions guide the agent's tone and focus.

---

[← Previous](07-text2cypher.md) | [Next: Adding Tools →](09-adding-tools.md)
