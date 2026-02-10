# Known Data Mismatches

## Sensor Type vs Manual Parameter Names

The CSV sensor `type` values don't exactly match the parameter names used in the maintenance manuals. The LLM extraction schema instructs the model to use the CSV names, but results may vary.

| CSV Sensor `type` | Manual parameter name | Match? |
|---|---|---|
| `EGT` | EGT | exact |
| `Vibration` | Vibration | exact |
| `N1Speed` | N1 (% RPM) | **mismatch** — manual says "N1", CSV says "N1Speed" |
| `FuelFlow` | Fuel Flow (kg/s) | **mismatch** — manual says "Fuel Flow", CSV says "FuelFlow" |

**Impact:** The `Sensor -[:HAS_LIMIT]-> OperatingLimit` cross-link matches on `OperatingLimit.parameterName = Sensor.type`. If the LLM extracts "N1" instead of "N1Speed", those sensors won't get linked.

**Fix options:**
1. Rename CSV sensor types to match manual names (`N1Speed` -> `N1`, `FuelFlow` -> `Fuel Flow`)
2. Update the manuals to use the CSV names consistently
3. Use fuzzy matching in the cross-link Cypher query

## E190 Aircraft — No Maintenance Manual

Aircraft AC1004, AC1008, AC1012, AC1016, AC1020 (model E190, operator NorthernJet) have no maintenance manual. They will not have Document or OperatingLimit links after enrichment.
