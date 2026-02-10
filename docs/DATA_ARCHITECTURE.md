# Data Architecture

## Dataset Overview

The workshop uses a comprehensive **Aircraft Digital Twin** dataset that models a complete aviation fleet over 90 operational days. The data is split across two platforms, each chosen for the workload it handles best:

- **Databricks Lakehouse** stores the **time-series sensor telemetry** — 345,600+ hourly readings across 90 days. Columnar storage and SQL make the Lakehouse ideal for aggregations, trend analysis, and statistical comparisons over large volumes of timestamped data.
- **Neo4j Aura** stores the **richly connected relational data** — aircraft topology, component hierarchies, maintenance events, flights, delays, and airport routes. A graph database handles multi-hop relationship traversals natively, avoiding the expensive JOINs a tabular database would require for queries like "Which components caused flight delays?"

Together the dataset includes:

![Dual Database Architecture](images/dual-database-architecture.png)

- **20 Aircraft** with tail numbers, models, and operators
- **80 Systems** (Engines, Avionics, Hydraulics) per aircraft
- **320 Components** (Turbines, Compressors, Pumps, etc.)
- **160 Sensors** with monitoring metadata
- **345,600+ Sensor Readings** (hourly telemetry over 90 days)
- **800 Flights** with departure/arrival information
- **300 Maintenance Events** with fault severity and corrective actions
- **12 Airports** in the route network

---

## Databricks Lakehouse (Time-Series Analytics)

| Table | Rows | Description |
|-------|------|-------------|
| `sensor_readings` | 345,600+ | Hourly sensor telemetry (90 days) |
| `sensors` | 160 | Sensor metadata (type, unit, system) |
| `systems` | ~80 | Aircraft systems (engines, avionics, hydraulics) |
| `aircraft` | 20 | Fleet metadata (tail number, model, operator) |

**Sensor Types:**
- **EGT** (Exhaust Gas Temperature): 640-700 C
- **Vibration**: 0.05-0.50 ips
- **N1Speed** (Fan Speed): 4,300-5,200 rpm
- **FuelFlow**: 0.85-1.95 kg/s

---

## Neo4j Knowledge Graph (Relationships)

| Node Type | Count | Purpose |
|-----------|-------|---------|
| Aircraft | 20 | Fleet inventory |
| System | ~80 | Component hierarchy |
| Component | 320 | Parts and assemblies |
| Sensor | 160 | Monitoring equipment |
| MaintenanceEvent | 300 | Fault tracking |
| Flight | 800 | Operations |
| Delay | ~300 | Delay causes |
| Airport | 12 | Route network |
| Removal | ~60 | Component removal tracking |

---

## Knowledge Graph Data Model

The Aircraft Digital Twin graph models the complete operational lifecycle of an aviation fleet.

### Graph Structure

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│ Aircraft │──────>│  System  │──────>│Component │
│          │ HAS_  │          │ HAS_  │          │
│ N95040A  │SYSTEM │ Engine 1 │COMPON │ Turbine  │
└──────────┘       └──────────┘       └──────────┘
     │                  │                  │
     │ OPERATES_        │ HAS_             │ HAS_
     │ FLIGHT           │ SENSOR           │ EVENT
     v                  v                  v
┌──────────┐       ┌──────────┐       ┌──────────┐
│  Flight  │       │  Sensor  │       │Maintenan │
│          │       │          │       │ceEvent   │
│ UA1234   │       │ EGT-001  │       │ Critical │
└──────────┘       └──────────┘       └──────────┘
     │
     │ DEPARTS_FROM / ARRIVES_AT
     v
┌──────────┐
│ Airport  │
│          │
│   ORD    │
└──────────┘
```

### Node Types

| Node Label | Description | Key Properties |
|------------|-------------|----------------|
| `Aircraft` | Fleet inventory | `aircraft_id`, `tail_number`, `model`, `operator` |
| `System` | Major aircraft systems | `system_id`, `type`, `name` |
| `Component` | Parts within systems | `component_id`, `type`, `name` |
| `Sensor` | Monitoring equipment | `sensor_id`, `type`, `unit` |
| `Flight` | Flight operations | `flight_id`, `flight_number`, `origin`, `destination` |
| `Airport` | Route network locations | `airport_id`, `iata`, `icao`, `city` |
| `MaintenanceEvent` | Fault and repair records | `event_id`, `fault`, `severity`, `corrective_action` |
| `Delay` | Flight delay information | `delay_id`, `cause`, `minutes` |
| `Removal` | Component removal history | `removal_id`, `reason`, `tsn`, `csn` |

### Relationship Types

| Relationship | Direction | Description |
|--------------|-----------|-------------|
| `HAS_SYSTEM` | `(Aircraft)->(System)` | Aircraft contains this system |
| `HAS_COMPONENT` | `(System)->(Component)` | System contains this component |
| `HAS_SENSOR` | `(System)->(Sensor)` | System has this sensor |
| `HAS_EVENT` | `(Component)->(MaintenanceEvent)` | Component had this maintenance event |
| `OPERATES_FLIGHT` | `(Aircraft)->(Flight)` | Aircraft operated this flight |
| `DEPARTS_FROM` | `(Flight)->(Airport)` | Flight departs from this airport |
| `ARRIVES_AT` | `(Flight)->(Airport)` | Flight arrives at this airport |
| `HAS_DELAY` | `(Flight)->(Delay)` | Flight had this delay |
| `AFFECTS_SYSTEM` | `(MaintenanceEvent)->(System)` | Event affected this system |
| `HAS_REMOVAL` | `(Aircraft)->(Removal)` | Aircraft had this component removal |
