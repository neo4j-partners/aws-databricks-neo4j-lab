# Aircraft Digital Twin - Data Architecture

**Purpose:** Complete data schema reference for the aircraft digital twin system
**Audience:** Data engineers, analysts, developers working with the data model
**Last Updated:** 2025-11-01

---

## Overview

This document describes the complete data architecture for the aircraft digital twin demonstration, covering both **Neo4j graph database** (relationships and topology) and **Databricks Delta Lake** (time-series analytics).

### Dataset Summary

**Fleet Scale:**
- **20 aircraft** (Boeing 737-800, Airbus A320-200/A321neo, Embraer E190)
- **4 operators** (ExampleAir, SkyWays, RegionalCo, NorthernJet)
- **160 sensors** (4 per engine × 2 engines × 20 aircraft)
- **345,600+ sensor readings** (90 days of hourly telemetry)
- **800 flights** across 12 airports
- **300 maintenance events**

**Time Period:** July 1, 2024 - September 29, 2024 (90 days)

**Data Type:** Synthetic demo data designed to mirror real-world patterns from NASA turbofan data, FAA service difficulty reports, and BTS on-time performance statistics.

---

## Table of Contents

1. [Dual Database Strategy](#dual-database-strategy)
2. [Conceptual Data Model](#conceptual-data-model)
3. [Neo4j Graph Database Schema](#neo4j-graph-database-schema)
4. [Databricks Delta Lake Schema](#databricks-delta-lake-schema)
5. [Data Overlap & Integration](#data-overlap--integration)
6. [Data Characteristics](#data-characteristics)
7. [Query Patterns & Use Cases](#query-patterns--use-cases)
8. [CSV File Reference](#csv-file-reference)

---

## Dual Database Strategy

### Why Two Databases?

This architecture uses **two complementary databases** to optimize for different query patterns:

#### Neo4j Graph Database - For Relationships
**Purpose:** Model structural topology and complex relationships

**Best For:**
- "Which components are connected to Engine 1?"
- "Show all maintenance events affecting hydraulic systems"
- "Trace the path from aircraft → system → sensor → component"
- "Find all flights operated by aircraft AC1001"
- "Which delays were caused by maintenance on Engine 2?"

**Strengths:**
- Complex relationship traversals
- Pattern matching (find similar fault patterns)
- Graph algorithms (shortest path, connected components)
- Topology visualization

**Query Example:**
```cypher
// Find all components and sensors for Engine 1 on aircraft AC1001
MATCH (a:Aircraft {aircraft_id: 'AC1001'})-[:HAS_SYSTEM]->(s:System {type: 'Engine', name: 'CFM56-7B #1'})
MATCH (s)-[:HAS_COMPONENT]->(c:Component)
MATCH (s)-[:HAS_SENSOR]->(sen:Sensor)
RETURN s.name, collect(DISTINCT c.name) as components, collect(DISTINCT sen.name) as sensors
```

---

#### Databricks Delta Lake - For Analytics
**Purpose:** Time-series data analysis and high-volume aggregations

**Best For:**
- "What's the average EGT temperature over the last 30 days?"
- "Show hourly vibration trends for all engines"
- "Find sensors with readings above threshold"
- "Calculate daily fuel flow rates per aircraft"
- "Statistical analysis: mean, std dev, percentiles"

**Strengths:**
- Time-series queries (windowing, aggregations)
- Statistical operations (AVG, STDDEV, PERCENTILE)
- High-volume data processing (345K+ readings)
- SQL-based analytics
- Natural language queries via Databricks Genie

**Query Example:**
```sql
-- Average EGT by aircraft over last 30 days
SELECT
  a.tail_number,
  a.model,
  AVG(r.value) as avg_egt,
  STDDEV(r.value) as stddev_egt
FROM sensor_readings r
  JOIN sensors sen ON r.sensor_id = sen.sensor_id
  JOIN systems s ON sen.system_id = s.system_id
  JOIN aircraft a ON s.aircraft_id = a.aircraft_id
WHERE sen.type = 'EGT'
  AND r.timestamp >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY a.tail_number, a.model
ORDER BY avg_egt DESC
```

---

### When to Use Which Database

| Query Type | Use Neo4j | Use Databricks | Why |
|------------|-----------|----------------|-----|
| Relationship traversals | ✅ | ❌ | Graph optimized for connections |
| Time-series aggregations | ❌ | ✅ | Delta Lake optimized for temporal data |
| Topology exploration | ✅ | ❌ | Graph visualization, pattern matching |
| Statistical analysis | ❌ | ✅ | SQL analytics, large dataset processing |
| Natural language queries | ❌ | ✅ | Databricks Genie only queries Delta tables |
| Maintenance-flight correlation | ✅ | ⚠️ | Graph relationships better, but can join in SQL |
| Sensor trend analysis | ⚠️ | ✅ | Possible in Neo4j but Databricks more efficient |

**Note:** The Smart Chat backend automatically routes queries to the appropriate database based on the question.

---

## Conceptual Data Model

### Entity Hierarchy

```
Fleet (4 Operators: ExampleAir, SkyWays, RegionalCo, NorthernJet)
  │
  └─── Aircraft (20 aircraft with unique tail numbers)
         │
         ├─── Systems (4 per aircraft: 2 Engines, Avionics, Hydraulics)
         │      │
         │      ├─── Components (5-7 per system: Turbine, Compressor, Pump, etc.)
         │      │      │
         │      │      └─── MaintenanceEvents (Faults, severity, corrective actions)
         │      │
         │      └─── Sensors (4 per engine: EGT, Vibration, N1Speed, FuelFlow)
         │             │
         │             └─── Readings (2,160 hourly readings per sensor over 90 days)
         │
         └─── Operations
                │
                └─── Flights (~40 flights per aircraft)
                       │
                       ├─── Departure Airport (12 airports total)
                       ├─── Arrival Airport
                       └─── Delays (various causes: Weather, Maintenance, NAS, Carrier)
```

### Data Category Breakdown

| Category | Description | Storage | Primary Use |
|----------|-------------|---------|-------------|
| **Structural** | Aircraft, Systems, Components, Sensors | Both | Topology (Neo4j), Joins (Databricks) |
| **Operational** | Flights, Airports, Delays | Neo4j only | Flight routing, delay analysis |
| **Maintenance** | MaintenanceEvents | Neo4j only | Fault tracking, reliability analysis |
| **Time-Series** | Sensor Readings | Both | Relationships (Neo4j), Analytics (Databricks) |

---

## Neo4j Graph Database Schema

### Node Types (9 types)

#### 1. Aircraft (20 nodes)
Represents individual aircraft in the fleet.

**Properties:**
- `aircraft_id` (String, Unique) - Primary identifier (e.g., "AC1001")
- `tail_number` (String) - Registration number (e.g., "N95040A")
- `icao24` (String) - ICAO 24-bit transponder code
- `model` (String) - Aircraft model (e.g., "B737-800", "A320-200", "A321neo", "E190")
- `manufacturer` (String) - Boeing, Airbus, or Embraer
- `operator` (String) - Operating airline

**Sample:**
```csv
aircraft_id,tail_number,icao24,model,manufacturer,operator
AC1001,N95040A,448367,B737-800,Boeing,ExampleAir
AC1002,N30268B,aee78a,A320-200,Airbus,SkyWays
```

**File:** `nodes_aircraft.csv`

---

#### 2. System (~80 nodes)
Represents major aircraft systems.

**Properties:**
- `system_id` (String, Unique) - Primary identifier (e.g., "AC1001-S01")
- `aircraft_id` (String) - Parent aircraft reference
- `type` (String) - System category: Engine, Avionics, Hydraulics
- `name` (String) - Human-readable name (e.g., "CFM56-7B #1", "V2500 #1")

**System Types:**
- **Engine** - Primary propulsion (2 per aircraft)
- **Avionics** - Flight management electronics (1 per aircraft)
- **Hydraulics** - Fluid power systems (1 per aircraft)

**Sample:**
```csv
system_id,aircraft_id,type,name
AC1001-S01,AC1001,Engine,CFM56-7B #1
AC1001-S02,AC1001,Engine,CFM56-7B #2
AC1001-S03,AC1001,Avionics,Generic Avionics Suite
AC1001-S04,AC1001,Hydraulics,Generic Hydraulics System
```

**File:** `nodes_systems.csv`

---

#### 3. Component (~200 nodes)
Represents individual parts within systems.

**Properties:**
- `component_id` (String, Unique) - Primary identifier
- `system_id` (String) - Parent system reference
- `type` (String) - Component category
- `name` (String) - Component description

**Component Types by System:**
- **Engine:** Turbine, Compressor, Combustor, Nozzle, Control Unit
- **Avionics:** Flight Computer, Navigation Unit
- **Hydraulics:** Pump, Filter, Reservoir

**Sample:**
```csv
component_id,system_id,type,name
AC1001-S01-C01,AC1001-S01,Turbine,High-pressure Turbine
AC1001-S01-C02,AC1001-S01,Compressor,Low-pressure Compressor
AC1001-S01-C03,AC1001-S01,Combustor,Combustion Chamber
```

**File:** `nodes_components.csv`

---

#### 4. Sensor (160 nodes)
Represents monitoring sensors attached to systems.

**Properties:**
- `sensor_id` (String, Unique) - Primary identifier (e.g., "AC1001-S01-SN01")
- `system_id` (String) - Parent system reference
- `type` (String) - Sensor category (EGT, Vibration, N1Speed, FuelFlow)
- `name` (String) - Human-readable name
- `unit` (String) - Measurement unit (C, ips, rpm, kg/s)

**Sensor Types (Engine Systems Only):**
- **EGT** (Exhaust Gas Temperature) - Engine temperature in Celsius
- **Vibration** (Engine Vibration) - Vibration levels in inches per second
- **N1Speed** (Fan Speed N1) - Fan rotational speed in RPM
- **FuelFlow** (Fuel Flow) - Fuel consumption in kg/s

**Sensor Distribution:**
- 4 sensors per engine × 2 engines per aircraft × 20 aircraft = **160 sensors**

**Sample:**
```csv
sensor_id,system_id,type,name,unit
AC1001-S01-SN01,AC1001-S01,EGT,Exhaust Gas Temperature,C
AC1001-S01-SN02,AC1001-S01,Vibration,Engine Vibration,ips
AC1001-S01-SN03,AC1001-S01,N1Speed,Fan Speed N1,rpm
AC1001-S01-SN04,AC1001-S01,FuelFlow,Fuel Flow,kg/s
```

**File:** `nodes_sensors.csv`

---

#### 5. Reading (~345,600 nodes)
Represents time-series sensor measurements.

**Properties:**
- `reading_id` (String, Unique) - Primary identifier
- `sensor_id` (String) - Reference to sensor
- `timestamp` (DateTime) - Measurement timestamp (ISO 8601 format)
- `value` (Float) - Measured value

**Scale:**
- 2,160 readings per sensor (90 days × 24 hours)
- 160 sensors total
- **Total: 345,600 readings**

**Sample:**
```csv
reading_id,sensor_id,timestamp,value
AC1001-S01-SN01-R00001,AC1001-S01-SN01,2024-07-01T00:00:00,648.41072
AC1001-S01-SN01-R00002,AC1001-S01-SN01,2024-07-01T01:00:00,651.31381
AC1001-S01-SN01-R00003,AC1001-S01-SN01,2024-07-01T02:00:00,649.88234
```

**File:** `nodes_readings.csv`

**Note:** Reading nodes in Neo4j are optional for this system since time-series analytics are better performed in Databricks. The GENERATES relationships can be skipped if using Databricks for all sensor analytics.

---

#### 6. Airport (12 nodes)
Represents airports in the flight network.

**Properties:**
- `airport_id` (String, Unique) - Primary identifier
- `name` (String) - Airport name
- `city` (String) - City location
- `country` (String) - Country location
- `iata` (String) - IATA airport code (3 letters)
- `icao` (String) - ICAO airport code (4 letters)
- `lat` (Float) - Latitude coordinate
- `lon` (Float) - Longitude coordinate

**Sample:**
```csv
airport_id,name,city,country,iata,icao,lat,lon
AP001,John F. Kennedy International Airport,New York,USA,JFK,KJFK,40.6413,-73.7781
AP002,Los Angeles International Airport,Los Angeles,USA,LAX,KLAX,33.9416,-118.4085
```

**File:** `nodes_airports.csv`

---

#### 7. Flight (800 nodes)
Represents individual flight operations.

**Properties:**
- `flight_id` (String, Unique) - Primary identifier
- `flight_number` (String) - Airline flight number (e.g., "AA123")
- `aircraft_id` (String) - Operating aircraft reference
- `operator` (String) - Operating airline
- `origin` (String) - Departure airport code (IATA)
- `destination` (String) - Arrival airport code (IATA)
- `scheduled_departure` (DateTime) - Planned departure time
- `scheduled_arrival` (DateTime) - Planned arrival time

**Sample:**
```csv
flight_id,flight_number,aircraft_id,operator,origin,destination,scheduled_departure,scheduled_arrival
FL00001,AA123,AC1001,ExampleAir,JFK,LAX,2024-07-01T08:00:00,2024-07-01T11:30:00
FL00002,AA456,AC1001,ExampleAir,LAX,ORD,2024-07-01T14:00:00,2024-07-01T19:45:00
```

**File:** `nodes_flights.csv`

---

#### 8. Delay (~300 nodes)
Represents flight delays and their causes.

**Properties:**
- `delay_id` (String, Unique) - Primary identifier
- `cause` (String) - Delay reason (Weather, Maintenance, Carrier, NAS)
- `minutes` (Integer) - Delay duration in minutes

**Delay Causes:**
- **Weather** - Weather-related delays
- **Maintenance** - Maintenance or mechanical issues
- **Carrier** - Airline operational issues
- **NAS** - National Airspace System delays (air traffic control)

**Sample:**
```csv
delay_id,cause,minutes
DLY00001,Weather,45
DLY00002,Maintenance,30
DLY00003,NAS,15
```

**File:** `nodes_delays.csv`

---

#### 9. MaintenanceEvent (300 nodes)
Represents maintenance actions and incidents.

**Properties:**
- `event_id` (String, Unique) - Primary identifier
- `component_id` (String) - Affected component
- `system_id` (String) - Affected system
- `aircraft_id` (String) - Affected aircraft
- `fault` (String) - Fault description
- `severity` (String) - Severity level (MINOR, MAJOR, CRITICAL)
- `reported_at` (DateTime) - Event timestamp
- `corrective_action` (String) - Action taken

**Fault Types:**
- Bearing wear
- Contamination
- Fuel starvation
- Leak
- Overheat
- Sensor drift
- Electrical fault
- Vibration exceedance

**Severity Levels:**
- **MINOR** - Low impact, routine maintenance
- **MAJOR** - Significant issue, requires attention
- **CRITICAL** - Safety-critical, immediate action required

**Sample:**
```csv
event_id,component_id,system_id,aircraft_id,fault,severity,reported_at,corrective_action
ME0001,AC1001-S01-C01,AC1001-S01,AC1001,Bearing wear,MINOR,2024-07-15T10:00:00,Replaced bearing
ME0002,AC1001-S01-C02,AC1001-S01,AC1001,Overheat,MAJOR,2024-07-20T14:30:00,Replaced component
```

**File:** `nodes_maintenance.csv`

---

### Relationships (11 types)

#### Hierarchical Structure (Aircraft Topology)

**1. HAS_SYSTEM**
- **Pattern:** `(:Aircraft)-[:HAS_SYSTEM]->(:System)`
- **Cardinality:** One aircraft → many systems (typically 4)
- **File:** `rels_aircraft_system.csv`
- **Example:** Aircraft AC1001 → Engine AC1001-S01, Engine AC1001-S02, Avionics, Hydraulics

**2. HAS_COMPONENT**
- **Pattern:** `(:System)-[:HAS_COMPONENT]->(:Component)`
- **Cardinality:** One system → many components (5-7)
- **File:** `rels_system_component.csv`
- **Example:** Engine AC1001-S01 → Turbine, Compressor, Combustor, Nozzle, Control Unit

**3. HAS_SENSOR**
- **Pattern:** `(:System)-[:HAS_SENSOR]->(:Sensor)`
- **Cardinality:** One engine system → 4 sensors
- **File:** `rels_system_sensor.csv`
- **Example:** Engine AC1001-S01 → EGT sensor, Vibration sensor, N1Speed sensor, FuelFlow sensor

**4. GENERATES**
- **Pattern:** `(:Sensor)-[:GENERATES]->(:Reading)`
- **Cardinality:** One sensor → many readings (2,160)
- **Note:** Created from `nodes_readings.csv` during import (implicit relationship)
- **⚠️ Optional:** Can be skipped if using Databricks for all sensor analytics (345K+ relationships)

---

#### Operational Relationships (Flight Operations)

**5. OPERATES_FLIGHT**
- **Pattern:** `(:Aircraft)-[:OPERATES_FLIGHT]->(:Flight)`
- **Cardinality:** One aircraft → many flights (~40 per aircraft)
- **File:** `rels_aircraft_flight.csv`
- **Example:** Aircraft AC1001 operates flights FL00001, FL00002, FL00003...

**6. DEPARTS_FROM**
- **Pattern:** `(:Flight)-[:DEPARTS_FROM]->(:Airport)`
- **Cardinality:** One flight → one origin airport
- **File:** `rels_flight_departure.csv`
- **Example:** Flight FL00001 departs from JFK

**7. ARRIVES_AT**
- **Pattern:** `(:Flight)-[:ARRIVES_AT]->(:Airport)`
- **Cardinality:** One flight → one destination airport
- **File:** `rels_flight_arrival.csv`
- **Example:** Flight FL00001 arrives at LAX

**8. HAS_DELAY**
- **Pattern:** `(:Flight)-[:HAS_DELAY]->(:Delay)`
- **Cardinality:** One flight → zero or one delay
- **File:** `rels_flight_delay.csv`
- **Example:** Flight FL00001 has delay DLY00001 (Weather, 45 minutes)

---

#### Maintenance Relationships (Fault Tracking)

**9. HAS_EVENT**
- **Pattern:** `(:Component)-[:HAS_EVENT]->(:MaintenanceEvent)`
- **Cardinality:** One component → many events (over time)
- **File:** `rels_component_event.csv`
- **Example:** Turbine AC1001-S01-C01 has maintenance event ME0001

**10. AFFECTS_SYSTEM**
- **Pattern:** `(:MaintenanceEvent)-[:AFFECTS_SYSTEM]->(:System)`
- **Cardinality:** One event → one system
- **File:** `rels_event_system.csv`
- **Example:** Maintenance event ME0001 affects system AC1001-S01 (Engine #1)

**11. AFFECTS_AIRCRAFT**
- **Pattern:** `(:MaintenanceEvent)-[:AFFECTS_AIRCRAFT]->(:Aircraft)`
- **Cardinality:** One event → one aircraft
- **File:** `rels_event_aircraft.csv`
- **Example:** Maintenance event ME0001 affects aircraft AC1001

---

### Graph Schema Diagram

```
                    ┌──────────────┐
                    │   Aircraft   │
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │  Flight  │   │  System  │   │  System  │
     └────┬─────┘   └────┬─────┘   └────┬─────┘
          │              │              │
     ┌────┼────┐    ┌────┼────┐    ┌────┼────┐
     ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼
  Airport Delay  Component Sensor  Component Sensor
                     │       │
                     ▼       ▼
            MaintenanceEvent Reading
```

---

## Databricks Delta Lake Schema

### Catalog Structure

**Catalog:** `boeing_test`
**Schema:** `boeing_test_lakehouse`
**Full Path:** `boeing_test.boeing_test_lakehouse.<table_name>`

---

### Delta Tables

#### Table 1: sensor_readings (Required)
**Purpose:** Time-series sensor telemetry data

**Schema:**
```sql
CREATE TABLE boeing_test.boeing_test_lakehouse.sensor_readings (
  reading_id STRING,
  sensor_id STRING,
  timestamp TIMESTAMP,
  value DOUBLE
)
PARTITIONED BY (sensor_id)
```

**Properties:**
- **Rows:** 345,600+ (2,160 readings × 160 sensors)
- **Partitioning:** By `sensor_id` (160 partitions)
- **Optimization:** Delta format with ACID transactions, time travel
- **File Format:** Parquet with Delta transaction log

**Sample Data:**
| reading_id | sensor_id | timestamp | value |
|------------|-----------|-----------|-------|
| AC1001-S01-SN01-R00001 | AC1001-S01-SN01 | 2024-07-01 00:00:00 | 648.41 |
| AC1001-S01-SN01-R00002 | AC1001-S01-SN01 | 2024-07-01 01:00:00 | 651.31 |
| AC1001-S01-SN01-R00003 | AC1001-S01-SN01 | 2024-07-01 02:00:00 | 649.88 |

**Source CSV:** `nodes_readings.csv`

**Why Partition by sensor_id?**
- Most queries filter by specific sensor
- 160 balanced partitions (2,160 rows each)
- Enables partition pruning for fast single-sensor queries
- Better than partitioning by timestamp (would create 2,160 tiny partitions)

---

#### Table 2: sensors (Recommended)
**Purpose:** Sensor metadata for joining with readings

**Schema:**
```sql
CREATE TABLE boeing_test.boeing_test_lakehouse.sensors (
  sensor_id STRING,
  system_id STRING,
  type STRING,
  name STRING,
  unit STRING
)
```

**Properties:**
- **Rows:** 160
- **No Partitioning:** Small reference table
- **Purpose:** Enable queries like "Show EGT sensors" without memorizing sensor IDs

**Sample Data:**
| sensor_id | system_id | type | name | unit |
|-----------|-----------|------|------|------|
| AC1001-S01-SN01 | AC1001-S01 | EGT | Exhaust Gas Temperature | C |
| AC1001-S01-SN02 | AC1001-S01 | Vibration | Engine Vibration | ips |
| AC1001-S01-SN03 | AC1001-S01 | N1Speed | Fan Speed N1 | rpm |
| AC1001-S01-SN04 | AC1001-S01 | FuelFlow | Fuel Flow | kg/s |

**Source CSV:** `nodes_sensors.csv`

**Why This Table is Important:**
- **Without it:** Users must query "sensor_id = 'AC1001-S01-SN01'" (cryptic)
- **With it:** Users can query "type = 'EGT'" (human-readable)
- **Enables Genie:** Natural language queries like "Show EGT sensors for Engine 1"

---

#### Table 3: systems (Recommended)
**Purpose:** System metadata for aircraft hierarchy

**Schema:**
```sql
CREATE TABLE boeing_test.boeing_test_lakehouse.systems (
  system_id STRING,
  aircraft_id STRING,
  type STRING,
  name STRING
)
```

**Properties:**
- **Rows:** ~80 (4 systems × 20 aircraft)
- **No Partitioning:** Small reference table

**Sample Data:**
| system_id | aircraft_id | type | name |
|-----------|-------------|------|------|
| AC1001-S01 | AC1001 | Engine | CFM56-7B #1 |
| AC1001-S02 | AC1001 | Engine | CFM56-7B #2 |
| AC1001-S03 | AC1001 | Avionics | Generic Avionics Suite |
| AC1001-S04 | AC1001 | Hydraulics | Generic Hydraulics System |

**Source CSV:** `nodes_systems.csv`

**Why This Table is Important:**
- Enables grouping by system type: "Average readings by Engine vs. Avionics"
- Links sensors to aircraft: `sensors → systems → aircraft`
- Required for queries like "Show Engine 1 temperature for aircraft N95040A"

---

#### Table 4: aircraft (Recommended)
**Purpose:** Aircraft metadata

**Schema:**
```sql
CREATE TABLE boeing_test.boeing_test_lakehouse.aircraft (
  aircraft_id STRING,
  tail_number STRING,
  icao24 STRING,
  model STRING,
  manufacturer STRING,
  operator STRING
)
```

**Properties:**
- **Rows:** 20
- **No Partitioning:** Small reference table

**Sample Data:**
| aircraft_id | tail_number | icao24 | model | manufacturer | operator |
|-------------|-------------|--------|-------|--------------|----------|
| AC1001 | N95040A | 448367 | B737-800 | Boeing | ExampleAir |
| AC1002 | N30268B | aee78a | A320-200 | Airbus | SkyWays |

**Source CSV:** `nodes_aircraft.csv`

**Why This Table is Important:**
- Human-readable aircraft identification (tail numbers)
- Filter by aircraft model: "Compare fuel flow for 737-800 vs. A320"
- Group by operator: "Fleet health by airline"
- Required for Genie queries like "Show aircraft N95040A sensors"

---

### Join Relationships in Delta Lake

The four tables connect to enable comprehensive analytics:

```
aircraft (20 rows)
    │
    └── aircraft_id
          │
          ▼
    systems (~80 rows)
          │
          └── system_id
                │
                ▼
          sensors (160 rows)
                │
                └── sensor_id
                      │
                      ▼
                sensor_readings (345,600+ rows)
```

**Example Join Query:**
```sql
-- Full chain: readings → sensors → systems → aircraft
SELECT
  a.tail_number,
  a.model,
  s.name AS system_name,
  sen.type AS sensor_type,
  AVG(r.value) AS avg_reading,
  STDDEV(r.value) AS stddev_reading,
  COUNT(*) AS reading_count
FROM sensor_readings r
  JOIN sensors sen ON r.sensor_id = sen.sensor_id
  JOIN systems s ON sen.system_id = s.system_id
  JOIN aircraft a ON s.aircraft_id = a.aircraft_id
WHERE r.timestamp >= '2024-07-01'
  AND sen.type = 'EGT'
GROUP BY a.tail_number, a.model, s.name, sen.type
ORDER BY avg_reading DESC
```

---

### Performance Optimization

**Partitioning Strategy:**
- `sensor_readings` partitioned by `sensor_id` (160 partitions)
- Rationale: Most queries filter by sensor first, enables partition pruning
- Each partition: ~2,160 rows (manageable size)

**Delta Lake Optimization:**
```sql
-- Coalesce small files, z-order by timestamp
OPTIMIZE boeing_test.boeing_test_lakehouse.sensor_readings
ZORDER BY (timestamp);
```

**Query Performance Tips:**
1. **Filter by sensor_id first** (partition pruning)
2. **Filter by timestamp range** (time-series queries)
3. **Use Z-ORDER BY timestamp** for time-range queries
4. **Pre-aggregate** common metrics into summary tables (optional)

---

## Data Overlap & Integration

### What Data Exists in Both Databases?

| Data Entity | Neo4j | Databricks | Why Both? |
|-------------|-------|------------|-----------|
| **Aircraft** | ✅ Nodes (20) | ✅ Table (20 rows) | Neo4j: topology queries<br>Databricks: filtering/grouping |
| **Systems** | ✅ Nodes (~80) | ✅ Table (~80 rows) | Neo4j: relationships<br>Databricks: joins for analytics |
| **Sensors** | ✅ Nodes (160) | ✅ Table (160 rows) | Neo4j: graph structure<br>Databricks: metadata for queries |
| **Readings** | ✅ Nodes (345,600+) | ✅ Table (345,600+ rows) | Neo4j: GENERATES relationship<br>Databricks: time-series analytics |
| **Components** | ✅ Nodes (~200) | ❌ No | Neo4j only (relationships, no time-series need) |
| **Airports** | ✅ Nodes (12) | ❌ No | Neo4j only (flight routing) |
| **Flights** | ✅ Nodes (800) | ❌ No | Neo4j only (operational events) |
| **Delays** | ✅ Nodes (~300) | ❌ No | Neo4j only (linked to flights) |
| **Maintenance** | ✅ Nodes (300) | ❌ No | Neo4j only (event relationships) |

---

### Why Keep Data in Both?

**Neo4j is Authoritative For:**
- Complete aircraft topology (all 9 node types)
- All relationships (11 relationship types)
- Component-level detail
- Operational events (flights, delays)
- Maintenance event relationships
- Graph traversals and pattern matching

**Databricks is Authoritative For:**
- High-volume sensor readings (optimized storage)
- Time-series analytics and aggregations
- SQL-based reporting and dashboards
- Natural language queries via Genie
- Statistical analysis

**Shared Metadata (Aircraft, Systems, Sensors):**
- Enables independent queries on each system
- Allows Databricks to join sensor data with aircraft context
- Required for Genie to understand queries like "Show Engine 1 temperature for aircraft N95040A"
- Small dataset (260 total rows) - duplication is acceptable

---

### Integration Patterns

**Pattern 1: Smart Chat Backend Routes Queries**
- User asks: "Which aircraft had high vibration and recent maintenance?"
- Backend determines: Need Databricks (vibration data) + Neo4j (maintenance events)
- Agent calls both tools, synthesizes answer

**Pattern 2: Export from Neo4j to Databricks**
- Query Neo4j for specific entity IDs (e.g., aircraft with maintenance issues)
- Pass IDs to Databricks SQL query for sensor analysis
- Join results in application layer

**Pattern 3: Databricks Query References Neo4j**
- Query Databricks for sensor anomalies (e.g., EGT > threshold)
- Get sensor_id list
- Query Neo4j to find related systems, components, maintenance events

---

## Data Characteristics

### Time Range
- **Start Date:** July 1, 2024 00:00:00
- **End Date:** September 29, 2024 23:00:00
- **Duration:** 90 days (2,160 hours)
- **Reading Frequency:** Hourly
- **Expected Readings per Sensor:** 2,160
- **Total Expected Readings:** 345,600 (160 sensors × 2,160 hours)

### Fleet Composition

**Aircraft Distribution:**
| Model | Manufacturer | Count | Percentage |
|-------|--------------|-------|------------|
| B737-800 | Boeing | 8 | 40% |
| A320-200 | Airbus | 6 | 30% |
| A321neo | Airbus | 4 | 20% |
| E190 | Embraer | 2 | 10% |
| **Total** | — | **20** | **100%** |

**Operator Distribution:**
| Operator | Aircraft Count | Flights |
|----------|---------------|---------|
| ExampleAir | 8 | ~320 |
| SkyWays | 6 | ~240 |
| RegionalCo | 4 | ~160 |
| NorthernJet | 2 | ~80 |
| **Total** | **20** | **800** |

### Sensor Configuration

**Per Aircraft:**
- 2 Engines × 4 sensors per engine = **8 sensors per aircraft**
- 20 aircraft × 8 sensors = **160 sensors total**

**Sensor Type Distribution:**
| Type | Count | Unit | Typical Range |
|------|-------|------|---------------|
| EGT | 40 | °C | 640-700°C |
| Vibration | 40 | ips | 0.05-0.50 ips |
| N1Speed | 40 | rpm | 4,300-5,200 rpm |
| FuelFlow | 40 | kg/s | 0.85-1.95 kg/s |
| **Total** | **160** | — | — |

### Data Volume Summary

| Entity | Count | Database |
|--------|-------|----------|
| Aircraft | 20 | Both |
| Systems | ~80 | Both |
| Components | ~200 | Neo4j only |
| Sensors | 160 | Both |
| Readings | 345,600+ | Both |
| Airports | 12 | Neo4j only |
| Flights | 800 | Neo4j only |
| Delays | ~300 | Neo4j only |
| Maintenance Events | 300 | Neo4j only |
| **Total Nodes** | **~347,170** | — |
| **Total Relationships** | **~347,000+** | — |

---

### Data Quality & Simulation

**This is Synthetic Demo Data** designed to mirror real-world patterns:

**Sensor Layer (NASA Turbofan-like):**
- Hourly readings with realistic noise (±2-5% variation)
- Mild degradation trends over 90 days (sensors show increasing values)
- Operational variations based on flight patterns
- No missing data (complete time series)

**Maintenance Layer (FAA SDR-like):**
- 300 events with realistic fault types
- Distribution: ~50% MINOR, ~35% MAJOR, ~15% CRITICAL
- Correlated with sensor anomalies (high readings often precede events)
- Timing aligned with flight operations

**Operational Layer (BTS On-Time Performance-like):**
- 800 flights with realistic scheduling (peak morning/evening hours)
- Delay causes: 30% Weather, 25% Maintenance, 25% NAS, 20% Carrier
- Route network: 12 airports with hub-and-spoke patterns
- Flight duration: 1.5-5 hours typical

**Data Integrity:**
- ✅ **Referential integrity:** All foreign keys valid (sensor_id, aircraft_id, etc.)
- ✅ **Timestamps consistent:** No temporal anomalies
- ✅ **No null values:** All required fields populated
- ✅ **No duplicates:** All IDs are unique
- ✅ **Realistic ranges:** All sensor values within expected bounds

---

## Query Patterns & Use Cases

### Neo4j Query Patterns

#### 1. Predictive Maintenance
**Goal:** Find sensor trends before critical maintenance events

```cypher
// Average EGT in 7 days before critical maintenance
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System {type:'Engine'})
      -[:HAS_SENSOR]->(sn:Sensor {type:'EGT'})
      -[:GENERATES]->(r:Reading)
MATCH (s)-[:HAS_COMPONENT]->(c)-[:HAS_EVENT]->(m:MaintenanceEvent {severity:'CRITICAL'})
WHERE datetime(r.timestamp) <= datetime(m.reported_at)
  AND datetime(r.timestamp) >= datetime(m.reported_at) - duration('P7D')
RETURN a.tail_number,
       s.name,
       m.fault,
       m.reported_at,
       avg(r.value) as avg_egt_before_failure,
       count(r) as reading_count
ORDER BY avg_egt_before_failure DESC
```

---

#### 2. Flight Delay Analysis
**Goal:** Correlate maintenance events with flight delays

```cypher
// Flights delayed due to maintenance, with event details
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay {cause:'Maintenance'})
MATCH (a:Aircraft)-[:OPERATES_FLIGHT]->(f)
MATCH (a)-[:HAS_SYSTEM]->(s:System)
      -[:HAS_COMPONENT]->(c)
      -[:HAS_EVENT]->(m:MaintenanceEvent)
WHERE datetime(m.reported_at) <= datetime(f.scheduled_departure)
  AND datetime(m.reported_at) >= datetime(f.scheduled_departure) - duration('P1D')
RETURN f.flight_number,
       a.tail_number,
       f.scheduled_departure,
       d.minutes as delay_minutes,
       s.name as affected_system,
       c.name as affected_component,
       m.fault,
       m.severity,
       m.reported_at as maintenance_date
ORDER BY d.minutes DESC
```

---

#### 3. Component Reliability
**Goal:** Identify components with highest failure rates

```cypher
// Component failure rates by type and severity
MATCH (c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
WITH c.type as component_type,
     m.severity as severity,
     count(*) as event_count
RETURN component_type,
       severity,
       event_count,
       event_count * 100.0 / sum(event_count) OVER (PARTITION BY component_type) as percentage
ORDER BY component_type, event_count DESC
```

---

#### 4. Aircraft Topology
**Goal:** Get complete system hierarchy for an aircraft

```cypher
// Complete topology for aircraft N95040A
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
OPTIONAL MATCH (s)-[:HAS_SENSOR]->(sen:Sensor)
RETURN a.tail_number,
       a.model,
       s.name as system,
       collect(DISTINCT c.name) as components,
       collect(DISTINCT sen.name) as sensors
ORDER BY s.type, s.name
```

---

### Databricks SQL Query Patterns

#### 1. Time-Series Trend Analysis
**Goal:** Calculate daily averages for EGT sensors

```sql
-- Daily average EGT by aircraft over 90 days
SELECT
  DATE(r.timestamp) as date,
  a.tail_number,
  a.model,
  AVG(r.value) as avg_egt,
  STDDEV(r.value) as stddev_egt,
  MIN(r.value) as min_egt,
  MAX(r.value) as max_egt,
  COUNT(*) as reading_count
FROM sensor_readings r
  JOIN sensors sen ON r.sensor_id = sen.sensor_id
  JOIN systems s ON sen.system_id = s.system_id
  JOIN aircraft a ON s.aircraft_id = a.aircraft_id
WHERE sen.type = 'EGT'
  AND r.timestamp >= '2024-07-01'
  AND r.timestamp < '2024-10-01'
GROUP BY DATE(r.timestamp), a.tail_number, a.model
ORDER BY date, a.tail_number
```

---

#### 2. Anomaly Detection
**Goal:** Find sensors with readings above 95th percentile

```sql
-- Sensors with readings above 95th percentile
WITH percentiles AS (
  SELECT
    sen.type,
    PERCENTILE(r.value, 0.95) as p95_value
  FROM sensor_readings r
    JOIN sensors sen ON r.sensor_id = sen.sensor_id
  GROUP BY sen.type
)
SELECT
  a.tail_number,
  s.name as system,
  sen.sensor_id,
  sen.type,
  r.timestamp,
  r.value,
  p.p95_value,
  (r.value - p.p95_value) / p.p95_value * 100 as pct_above_p95
FROM sensor_readings r
  JOIN sensors sen ON r.sensor_id = sen.sensor_id
  JOIN systems s ON sen.system_id = s.system_id
  JOIN aircraft a ON s.aircraft_id = a.aircraft_id
  JOIN percentiles p ON sen.type = p.type
WHERE r.value > p.p95_value
ORDER BY pct_above_p95 DESC, r.timestamp DESC
LIMIT 100
```

---

#### 3. Fleet-Wide Comparison
**Goal:** Compare sensor performance across aircraft models

```sql
-- Average sensor readings by aircraft model and sensor type
SELECT
  a.model,
  sen.type,
  COUNT(DISTINCT a.aircraft_id) as aircraft_count,
  COUNT(*) as reading_count,
  AVG(r.value) as avg_value,
  STDDEV(r.value) as stddev_value,
  MIN(r.value) as min_value,
  MAX(r.value) as max_value
FROM sensor_readings r
  JOIN sensors sen ON r.sensor_id = sen.sensor_id
  JOIN systems s ON sen.system_id = s.system_id
  JOIN aircraft a ON s.aircraft_id = a.aircraft_id
GROUP BY a.model, sen.type
ORDER BY a.model, sen.type
```

---

#### 4. Time Window Aggregations
**Goal:** Calculate rolling 7-day averages

```sql
-- 7-day rolling average for vibration sensors
SELECT
  a.tail_number,
  s.name as engine,
  sen.sensor_id,
  r.timestamp,
  r.value,
  AVG(r.value) OVER (
    PARTITION BY sen.sensor_id
    ORDER BY r.timestamp
    ROWS BETWEEN 167 PRECEDING AND CURRENT ROW
  ) as rolling_7day_avg
FROM sensor_readings r
  JOIN sensors sen ON r.sensor_id = sen.sensor_id
  JOIN systems s ON sen.system_id = s.system_id
  JOIN aircraft a ON s.aircraft_id = a.aircraft_id
WHERE sen.type = 'Vibration'
  AND r.timestamp >= '2024-07-01'
ORDER BY a.tail_number, r.timestamp
```

**Note:** 167 PRECEDING = 7 days × 24 hours - 1

---

## CSV File Reference

### Node Files (9 files)

| File | Rows | Neo4j | Databricks | Description |
|------|------|-------|------------|-------------|
| `nodes_aircraft.csv` | 20 | ✅ | ✅ | Aircraft fleet metadata |
| `nodes_systems.csv` | ~80 | ✅ | ✅ | Aircraft systems (engines, avionics, hydraulics) |
| `nodes_components.csv` | ~200 | ✅ | ❌ | System components (turbines, pumps, etc.) |
| `nodes_sensors.csv` | 160 | ✅ | ✅ | Sensor metadata (type, unit) |
| `nodes_readings.csv` | 345,600+ | ✅ | ✅ | Sensor telemetry measurements |
| `nodes_airports.csv` | 12 | ✅ | ❌ | Airport locations and codes |
| `nodes_flights.csv` | 800 | ✅ | ❌ | Flight operations and schedules |
| `nodes_delays.csv` | ~300 | ✅ | ❌ | Flight delay information |
| `nodes_maintenance.csv` | 300 | ✅ | ❌ | Maintenance events and faults |

---

### Relationship Files (10 files)

| File | Relationship | From → To | Purpose |
|------|--------------|-----------|---------|
| `rels_aircraft_system.csv` | HAS_SYSTEM | Aircraft → System | Aircraft topology |
| `rels_system_component.csv` | HAS_COMPONENT | System → Component | System breakdown |
| `rels_system_sensor.csv` | HAS_SENSOR | System → Sensor | Sensor placement |
| `rels_component_event.csv` | HAS_EVENT | Component → MaintenanceEvent | Fault tracking |
| `rels_aircraft_flight.csv` | OPERATES_FLIGHT | Aircraft → Flight | Flight operations |
| `rels_flight_departure.csv` | DEPARTS_FROM | Flight → Airport | Origin airport |
| `rels_flight_arrival.csv` | ARRIVES_AT | Flight → Airport | Destination airport |
| `rels_flight_delay.csv` | HAS_DELAY | Flight → Delay | Delay information |
| `rels_event_system.csv` | AFFECTS_SYSTEM | MaintenanceEvent → System | Event impact |
| `rels_event_aircraft.csv` | AFFECTS_AIRCRAFT | MaintenanceEvent → Aircraft | Event impact |

**Note:** The GENERATES relationship (Sensor → Reading) is created from `nodes_readings.csv` during Neo4j import and is not a separate file.

---

## Summary

This data architecture provides a comprehensive aircraft digital twin system with:

✅ **Dual database strategy** optimized for different query patterns
✅ **Complete topology** modeling aircraft → systems → components → sensors
✅ **Time-series data** for predictive analytics (345K+ readings)
✅ **Operational context** with flights, delays, and maintenance events
✅ **Realistic simulation** with degradation trends and correlations
✅ **Reference integrity** across all entities
✅ **Flexible querying** via graph traversals (Neo4j) or SQL analytics (Databricks)

**For setup instructions, see:** [data_setup/README.md](../data_setup/README.md)

**For backend API usage, see:** [backend/README.md](../backend/README.md)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-01
**Maintainer:** Data Engineering Team
