# Alternative: Python SDK for Lakehouse Table Creation

If you prefer Python over the bash script (`create_lakehouse_tables.sh`), you can use the `databricks-sdk` package to execute the same SQL statements programmatically.

## Prerequisites

```bash
pip install databricks-sdk
```

Authentication is inherited automatically from:
1. Databricks CLI profile (`~/.databrickscfg`)
2. Environment variables (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`)
3. Azure CLI / AWS credentials (if configured)

## Script

```python
#!/usr/bin/env python3
"""Create lakehouse Delta tables from CSV files in a Databricks Volume."""

import sys
import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

CATALOG = sys.argv[1] if len(sys.argv) > 1 else "aws-databricks-neo4j-lab"
SCHEMA = "lab-schema"
VOLUME = "lab-volume"
LAKEHOUSE_SCHEMA = "lakehouse"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"

# --- SQL Statements ---

CREATE_SCHEMA = f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{LAKEHOUSE_SCHEMA}`"

CREATE_TABLES = [
    f"""CREATE TABLE IF NOT EXISTS `{CATALOG}`.{LAKEHOUSE_SCHEMA}.aircraft
USING DELTA
AS SELECT * FROM csv.`{VOLUME_PATH}/nodes_aircraft.csv`
OPTIONS (header = 'true', inferSchema = 'true')""",

    f"""CREATE TABLE IF NOT EXISTS `{CATALOG}`.{LAKEHOUSE_SCHEMA}.systems
USING DELTA
AS SELECT * FROM csv.`{VOLUME_PATH}/nodes_systems.csv`
OPTIONS (header = 'true', inferSchema = 'true')""",

    f"""CREATE TABLE IF NOT EXISTS `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensors
USING DELTA
AS SELECT * FROM csv.`{VOLUME_PATH}/nodes_sensors.csv`
OPTIONS (header = 'true', inferSchema = 'true')""",

    f"""CREATE TABLE IF NOT EXISTS `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensor_readings
USING DELTA
PARTITIONED BY (sensor_id)
AS SELECT
    reading_id,
    sensor_id,
    to_timestamp(ts) as timestamp,
    CAST(value AS DOUBLE) as value
FROM csv.`{VOLUME_PATH}/nodes_readings.csv`
OPTIONS (header = 'true', inferSchema = 'true')""",
]

COMMENTS = [
    # Aircraft
    f"COMMENT ON TABLE `{CATALOG}`.{LAKEHOUSE_SCHEMA}.aircraft IS 'Fleet of aircraft with tail numbers, models, and operators'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.aircraft.`_id:ID(Aircraft)` IS 'Unique aircraft identifier'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.aircraft.tail_number IS 'Aircraft registration/tail number (e.g., N95040A)'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.aircraft.model IS 'Aircraft model (e.g., B737-800, A320-200)'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.aircraft.operator IS 'Airline operator name'",
    # Systems
    f"COMMENT ON TABLE `{CATALOG}`.{LAKEHOUSE_SCHEMA}.systems IS 'Aircraft systems including engines, avionics, and hydraulics'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.systems.`_id:ID(System)` IS 'Unique system identifier'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.systems.type IS 'System type (Engine, Avionics, Hydraulics)'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.systems.name IS 'Human-readable system name'",
    # Sensors
    f"COMMENT ON TABLE `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensors IS 'Sensors installed on aircraft systems'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensors.`_id:ID(Sensor)` IS 'Unique sensor identifier'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensors.type IS 'Sensor type: EGT (Exhaust Gas Temperature in Celsius), Vibration (ips), N1Speed (RPM), FuelFlow (kg/s)'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensors.unit IS 'Unit of measurement'",
    # Sensor readings
    f"COMMENT ON TABLE `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensor_readings IS 'Hourly sensor readings over 90 days (July-September 2024)'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensor_readings.reading_id IS 'Unique reading identifier'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensor_readings.sensor_id IS 'Foreign key to sensors table'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensor_readings.timestamp IS 'Reading timestamp (hourly intervals)'",
    f"COMMENT ON COLUMN `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensor_readings.value IS 'Sensor reading value in the sensor unit'",
]

VERIFY_QUERY = f"""
SELECT 'aircraft' as table_name, COUNT(*) as row_count FROM `{CATALOG}`.{LAKEHOUSE_SCHEMA}.aircraft
UNION ALL
SELECT 'systems', COUNT(*) FROM `{CATALOG}`.{LAKEHOUSE_SCHEMA}.systems
UNION ALL
SELECT 'sensors', COUNT(*) FROM `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensors
UNION ALL
SELECT 'sensor_readings', COUNT(*) FROM `{CATALOG}`.{LAKEHOUSE_SCHEMA}.sensor_readings
"""


def execute_sql(client, warehouse_id, sql, description=""):
    """Execute a SQL statement and wait for completion."""
    if description:
        print(f"  {description}...", end=" ", flush=True)

    response = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=sql,
        wait_timeout="50s",
    )

    # Poll if still running
    while response.status and response.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        time.sleep(2)
        response = client.statement_execution.get_statement(response.statement_id)

    if response.status and response.status.state == StatementState.SUCCEEDED:
        if description:
            print("OK")
        return response
    else:
        error = response.status.error if response.status else "Unknown error"
        if description:
            print(f"FAILED: {error}")
        raise RuntimeError(f"SQL failed: {error}\n  Statement: {sql[:100]}...")


def main():
    client = WorkspaceClient()

    # Find a SQL warehouse
    warehouses = list(client.warehouses.list())
    if not warehouses:
        print("Error: No SQL warehouses found. Create one in the Databricks UI.")
        sys.exit(1)

    warehouse = warehouses[0]
    print(f"Using warehouse: {warehouse.name} ({warehouse.id})")
    print()

    # Create schema
    print("Creating lakehouse schema...")
    execute_sql(client, warehouse.id, CREATE_SCHEMA, "CREATE SCHEMA")
    print()

    # Create tables
    print("Creating Delta Lake tables...")
    table_names = ["aircraft", "systems", "sensors", "sensor_readings"]
    for sql, name in zip(CREATE_TABLES, table_names):
        execute_sql(client, warehouse.id, sql, f"CREATE TABLE {name}")
    print()

    # Add comments
    print("Adding table/column comments for Genie...")
    for sql in COMMENTS:
        execute_sql(client, warehouse.id, sql)
    print("  Comments added.")
    print()

    # Verify
    print("Verifying row counts...")
    result = execute_sql(client, warehouse.id, VERIFY_QUERY)
    if result.result and result.result.data_array:
        print(f"  {'Table':<20} {'Rows':>10}")
        print(f"  {'-'*20} {'-'*10}")
        for row in result.result.data_array:
            print(f"  {row[0]:<20} {row[1]:>10}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
```

## Usage

```bash
# Default catalog (aws-databricks-neo4j-lab)
python create_lakehouse_tables.py

# Custom catalog
python create_lakehouse_tables.py my-catalog
```

## When to use this instead of the bash script

- You need richer error handling or retry logic
- You want to integrate table creation into a larger Python workflow
- You prefer Python over bash for maintainability
