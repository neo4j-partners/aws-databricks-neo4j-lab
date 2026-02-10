# Agent Reasoning

## Understanding Tool Selection

The agent shows its reasoning process:

```
Question: "What are the sensor operating limits for N30268B?"

Reasoning: This question asks about sensor operating limits for a
           specific aircraft. The get_sensor_limits tool is designed
           for this. Parameter: tail_number = "N30268B"

Action: Calling get_sensor_limits with tail_number="N30268B"

Result: Sensor data with operating limits from the A320-200 manual

Response: "Aircraft N30268B (A320-200) has the following sensor
          operating limits:
          - EGT: ... (from V2500 #1 and V2500 #2 engines)
          - Vibration: ...
          - N1Speed: ...
          - FuelFlow: ..."
```

## Why Reasoning Matters

- **Transparency** - Understand why the agent chose its approach
- **Debugging** - Identify when tools are misselected
- **Trust** - Users can verify the agent's logic
- **Provenance** - Cross-links trace data back to source manuals

---

[<- Previous](10-testing.md) | [Next: Summary ->](12-summary.md)
