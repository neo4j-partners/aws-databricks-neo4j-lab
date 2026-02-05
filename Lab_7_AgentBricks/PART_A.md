# Part A: Genie Space for Aircraft Sensor Analytics

In this part, you'll create a Databricks AI/BI Genie space that enables natural language queries over your aircraft sensor telemetry data. This Genie will become one of the sub-agents in your multi-agent system.

**Estimated Time:** 30 minutes

---

## Prerequisites

Before starting, verify that the sensor data tables exist in your Unity Catalog:

```sql
-- Run in a SQL warehouse or notebook
SELECT COUNT(*) FROM aircraft_workshop.aircraft_lab.sensor_readings;
SELECT COUNT(*) FROM aircraft_workshop.aircraft_lab.sensors;
SELECT COUNT(*) FROM aircraft_workshop.aircraft_lab.systems;
SELECT COUNT(*) FROM aircraft_workshop.aircraft_lab.aircraft;
```

Expected counts:
- `sensor_readings`: ~345,600 rows
- `sensors`: 160 rows
- `systems`: ~80 rows
- `aircraft`: 20 rows

---

## Step 1: Create the Genie Space

### 1.1 Navigate to AI/BI Genie

1. In your Databricks workspace, click **New** > **Genie space**
2. Or navigate to **AI/BI** in the left sidebar and click **New Genie space**

### 1.2 Configure Basic Settings

1. **Name:** `Aircraft Sensor Analyst [YOUR_INITIALS]`
   - Example: `Aircraft Sensor Analyst RK`
2. **Description:** "Analyzes aircraft engine sensor telemetry including EGT, vibration, N1 speed, and fuel flow metrics"
3. Click **Create**

---

## Step 2: Add Data Sources

### 2.1 Select the Warehouse

1. In the Genie configuration, click **Select warehouse**
2. Choose a **Serverless SQL Warehouse** or **Pro SQL Warehouse**
   - Serverless is recommended for best performance

### 2.2 Add Unity Catalog Tables

Click **Add tables** and select the following from `aircraft_workshop.aircraft_lab`:

1. **sensor_readings**
   - Primary table with 345,600+ time-series measurements
   - Columns: `reading_id`, `sensor_id`, `ts`, `value`

2. **sensors**
   - Sensor metadata (type, unit, location)
   - Columns: `sensor_id`, `system_id`, `type`, `name`, `unit`

3. **systems**
   - Aircraft systems (engines, avionics, hydraulics)
   - Columns: `system_id`, `aircraft_id`, `type`, `name`

4. **aircraft**
   - Fleet inventory and metadata
   - Columns: `aircraft_id`, `tail_number`, `icao24`, `model`, `manufacturer`, `operator`

> **Tip:** These tables form a join chain: `sensor_readings` -> `sensors` -> `systems` -> `aircraft`

---

## Step 3: Add Sample Questions

Sample questions train the Genie to understand domain-specific language. Click **Add sample questions** and enter these examples:

### Time-Series Analytics

```
What is the average EGT temperature for aircraft N95040A over the last 30 days?
```

```
Show daily average vibration readings for Engine 1 on aircraft AC1001
```

```
What was the maximum fuel flow recorded in August 2024?
```

### Fleet Comparisons

```
Compare average EGT temperatures between Boeing 737 and Airbus A320 aircraft
```

```
Which aircraft has the highest average vibration readings?
```

```
Show fuel flow rates by operator
```

### Anomaly Detection

```
Find sensors with readings above their 95th percentile value
```

```
Show all EGT readings above 690 degrees Celsius
```

```
Which engines have N1 speed readings outside the normal range of 4500-5000 rpm?
```

### Trend Analysis

```
Show the trend of EGT temperatures over the 90-day period for aircraft N95040A
```

```
Calculate the 7-day rolling average of vibration for Engine 1 on AC1001
```

---

## Step 4: Add Instructions

Instructions provide domain knowledge and query conventions. Click **Add instructions** and enter:

```
# Aircraft Sensor Analytics Domain Knowledge

## Sensor Types and Normal Ranges
- EGT (Exhaust Gas Temperature): Normal range 640-700 degrees Celsius, measured in C
- Vibration: Normal range 0.05-0.50 inches per second, measured in ips
- N1Speed (Fan Speed N1): Normal range 4,300-5,200 RPM, measured in rpm
- FuelFlow: Normal range 0.85-1.95 kg/s, measured in kg/s

## Fleet Information
- 20 aircraft in the fleet
- 4 operators: ExampleAir, SkyWays, RegionalCo, NorthernJet
- Models: B737-800 (Boeing), A320-200 (Airbus), A321neo (Airbus), E190 (Embraer)

## Sensor Configuration
- Each aircraft has 2 engines
- Each engine has 4 sensors: EGT, Vibration, N1Speed, FuelFlow
- Total: 160 sensors across the fleet (20 aircraft x 2 engines x 4 sensors)

## Data Conventions
- Timestamps are in ISO 8601 format (e.g., 2024-07-01T00:00:00)
- Data period: July 1, 2024 to September 29, 2024 (90 days)
- Readings are hourly (24 per day per sensor)
- 2,160 readings per sensor over the 90-day period

## Sensor ID Format
- Format: AC{aircraft_number}-S{system_number}-SN{sensor_number}
- Example: AC1001-S01-SN01 = Aircraft 1001, Engine 1 (S01), EGT sensor (SN01)
- S01 and S02 are always engines; S03 is Avionics; S04 is Hydraulics
- SN01=EGT, SN02=Vibration, SN03=N1Speed, SN04=FuelFlow

## Engine Names by Model
- B737-800: CFM56-7B engines
- A320-200: V2500-A1 engines
- A321neo: PW1100G engines
- E190: CF34-10E engines

## Query Conventions
- When asked about "Engine 1", filter by systems where name contains "#1"
- When asked about "Engine 2", filter by systems where name contains "#2"
- Use tail_number for human-readable aircraft references (e.g., N95040A)
- Use aircraft_id for internal references (e.g., AC1001)
- Always include units in results (C, ips, rpm, kg/s)
```

---

## Step 5: Test the Genie

### 5.1 Start a Conversation

Click **Start conversation** or go to the chat interface.

### 5.2 Test Basic Queries

Try these progressively complex queries:

**Query 1: Simple Aggregation**
```
What is the average EGT temperature across all sensors?
```
Expected: A single number around 650-680 degrees Celsius

**Query 2: Filtering by Aircraft**
```
Show the average EGT for aircraft N95040A
```
Expected: Average EGT for that specific aircraft

**Query 3: Time-Series Trend**
```
Show daily average EGT for aircraft AC1001 in July 2024
```
Expected: ~30 rows with date and average value

**Query 4: Cross-Table Join**
```
Compare average vibration readings by aircraft model
```
Expected: Results grouped by B737-800, A320-200, A321neo, E190

**Query 5: Statistical Analysis**
```
Find the top 5 sensors with the highest average readings for their type
```
Expected: Top sensors with their average values and types

### 5.3 Validate SQL Generation

For each query, click **View SQL** to verify the generated query is correct:

Example for "Compare average vibration by aircraft model":
```sql
SELECT
    a.model,
    AVG(r.value) as avg_vibration,
    COUNT(*) as reading_count
FROM sensor_readings r
JOIN sensors sen ON r.sensor_id = sen.sensor_id
JOIN systems s ON sen.system_id = s.system_id
JOIN aircraft a ON s.aircraft_id = a.aircraft_id
WHERE sen.type = 'Vibration'
GROUP BY a.model
ORDER BY avg_vibration DESC
```

---

## Step 6: Refine Based on Testing

### Common Refinements

1. **If queries miss joins:**
   Add to instructions: "Always join through sensors -> systems -> aircraft for aircraft-level queries"

2. **If units are missing:**
   Add to instructions: "Include the unit column from sensors table in all results"

3. **If time filtering is wrong:**
   Add sample question: "Show readings from July 2024" with expected date range

4. **If sensor types are confused:**
   Add more examples distinguishing EGT from Vibration queries

### Add More Sample Questions as Needed

Based on your testing, add questions that the Genie struggled with:

```
Show all vibration readings above 0.4 ips in the last 30 days
```

```
What is the standard deviation of EGT readings by aircraft?
```

---

## Step 7: Save and Note the Genie Space ID

### 7.1 Save Configuration

Click **Save** to preserve your Genie space configuration.

### 7.2 Record the Genie Space Name

Note the exact name of your Genie space (e.g., `Aircraft Sensor Analyst RK`). You'll need this in Part B when configuring the multi-agent supervisor.

---

## Summary

You've created a Genie space that can:

- Query 345,600+ sensor readings using natural language
- Aggregate by aircraft, model, operator, or sensor type
- Perform statistical analysis (averages, percentiles, standard deviation)
- Join across the data model to provide context-rich answers
- Understand domain-specific terminology (EGT, N1Speed, etc.)

---

## Sample SQL Templates

For reference, here are common query patterns the Genie should generate:

### Average by Sensor Type
```sql
SELECT sen.type, AVG(r.value) as avg_value, sen.unit
FROM sensor_readings r
JOIN sensors sen ON r.sensor_id = sen.sensor_id
GROUP BY sen.type, sen.unit
```

### Daily Trend for Specific Aircraft
```sql
SELECT DATE(r.ts) as date, AVG(r.value) as avg_value
FROM sensor_readings r
JOIN sensors sen ON r.sensor_id = sen.sensor_id
JOIN systems s ON sen.system_id = s.system_id
JOIN aircraft a ON s.aircraft_id = a.aircraft_id
WHERE a.tail_number = 'N95040A'
  AND sen.type = 'EGT'
GROUP BY DATE(r.ts)
ORDER BY date
```

### Percentile Analysis
```sql
WITH percentiles AS (
    SELECT sen.type, PERCENTILE(r.value, 0.95) as p95
    FROM sensor_readings r
    JOIN sensors sen ON r.sensor_id = sen.sensor_id
    GROUP BY sen.type
)
SELECT sen.sensor_id, sen.type, r.ts, r.value, p.p95
FROM sensor_readings r
JOIN sensors sen ON r.sensor_id = sen.sensor_id
JOIN percentiles p ON sen.type = p.type
WHERE r.value > p.p95
ORDER BY r.value DESC
LIMIT 100
```

### Fleet Comparison
```sql
SELECT a.model, a.manufacturer,
       COUNT(DISTINCT a.aircraft_id) as aircraft_count,
       AVG(r.value) as avg_egt,
       STDDEV(r.value) as stddev_egt
FROM sensor_readings r
JOIN sensors sen ON r.sensor_id = sen.sensor_id
JOIN systems s ON sen.system_id = s.system_id
JOIN aircraft a ON s.aircraft_id = a.aircraft_id
WHERE sen.type = 'EGT'
GROUP BY a.model, a.manufacturer
ORDER BY avg_egt DESC
```

---

## Next Steps

Proceed to **Part B** to create the multi-agent supervisor that combines this Genie space with the Neo4j MCP agent for comprehensive aircraft intelligence.
