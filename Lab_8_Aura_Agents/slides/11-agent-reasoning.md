# Agent Reasoning

## Understanding Tool Selection

The agent shows its reasoning process:

```
Question: "Tell me about aircraft N95040A"

Reasoning: This question asks for aircraft overview information.
           The get_aircraft_overview tool is designed for this.
           Parameter: tail_number = "N95040A"

Action: Calling get_aircraft_overview with tail_number="N95040A"

Result: Aircraft data with systems and maintenance events

Response: "Aircraft N95040A is a Boeing B737-800 operated by
          ExampleAir with 4 systems and recent maintenance..."
```

## Why Reasoning Matters

- **Transparency** - Understand why the agent chose its approach
- **Debugging** - Identify when tools are misselected
- **Trust** - Users can verify the agent's logic

---

[← Previous](10-testing.md) | [Next: Summary →](12-summary.md)
