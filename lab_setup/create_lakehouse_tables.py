"""
Create Lakehouse Tables (Step 4)

Creates Delta Lake tables from CSV files in a Databricks Unity Catalog volume.
These tables are used by Databricks Genie in Lab 7.

Usage (run in Databricks as a Python script or notebook):
    # With defaults (catalog=aws-databricks-neo4j-lab, volume_schema=lab-schema, volume=lab-volume)
    %run ./create_lakehouse_tables

    # Or execute via Databricks CLI:
    databricks jobs create ...

    # The script uses widget parameters when available, otherwise defaults.
"""

import sys


DEFAULTS = {
    "catalog": "aws-databricks-neo4j-lab",
    "volume_schema": "lab-schema",
    "volume": "lab-volume",
    "lakehouse_schema": "lakehouse",
}


def get_config():
    """Get configuration from Databricks widgets or CLI args or defaults."""
    config = dict(DEFAULTS)

    # Try Databricks widgets first (available when run in a notebook/job)
    try:
        dbutils  # noqa: F821
        for key, default in DEFAULTS.items():
            try:
                dbutils.widgets.text(key, default, key)  # noqa: F821
                config[key] = dbutils.widgets.get(key)  # noqa: F821
            except Exception:
                pass
    except NameError:
        pass

    # Fall back to CLI args: create_lakehouse_tables.py <catalog> [volume_schema] [volume]
    if len(sys.argv) > 1:
        config["catalog"] = sys.argv[1]
    if len(sys.argv) > 2:
        config["volume_schema"] = sys.argv[2]
    if len(sys.argv) > 3:
        config["volume"] = sys.argv[3]

    return config


def create_lakehouse_schema(spark, catalog, lakehouse_schema):
    """Create the lakehouse schema if it doesn't exist."""
    print(f"Creating schema `{catalog}`.`{lakehouse_schema}`...")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{lakehouse_schema}`")
    print("  Schema ready.")


def create_tables(spark, catalog, volume_schema, volume, lakehouse_schema):
    """Create Delta Lake tables from CSV files in the volume."""
    volume_path = f"/Volumes/{catalog}/{volume_schema}/{volume}"
    target = f"`{catalog}`.`{lakehouse_schema}`"

    tblprops = "TBLPROPERTIES ('delta.columnMapping.mode' = 'name')"

    tables = [
        {
            "name": "aircraft",
            "sql": f"""
                CREATE TABLE IF NOT EXISTS {target}.aircraft
                {tblprops}
                AS SELECT * FROM read_files('{volume_path}/nodes_aircraft.csv',
                    format => 'csv', header => 'true', inferSchema => 'true')
            """,
        },
        {
            "name": "systems",
            "sql": f"""
                CREATE TABLE IF NOT EXISTS {target}.systems
                {tblprops}
                AS SELECT * FROM read_files('{volume_path}/nodes_systems.csv',
                    format => 'csv', header => 'true', inferSchema => 'true')
            """,
        },
        {
            "name": "sensors",
            "sql": f"""
                CREATE TABLE IF NOT EXISTS {target}.sensors
                {tblprops}
                AS SELECT * FROM read_files('{volume_path}/nodes_sensors.csv',
                    format => 'csv', header => 'true', inferSchema => 'true')
            """,
        },
        {
            "name": "sensor_readings",
            "sql": f"""
                CREATE TABLE IF NOT EXISTS {target}.sensor_readings
                {tblprops}
                PARTITIONED BY (sensor_id)
                AS SELECT
                    reading_id,
                    sensor_id,
                    to_timestamp(ts) as timestamp,
                    CAST(value AS DOUBLE) as value
                FROM read_files('{volume_path}/nodes_readings.csv',
                    format => 'csv', header => 'true', inferSchema => 'true')
            """,
        },
    ]

    for table in tables:
        print(f"  Creating table {target}.{table['name']}...")
        spark.sql(table["sql"])
        print(f"    Done.")


def verify_tables(spark, catalog, lakehouse_schema):
    """Verify row counts for all lakehouse tables."""
    target = f"`{catalog}`.`{lakehouse_schema}`"

    print("\nVerifying table row counts...")
    result = spark.sql(f"""
        SELECT 'aircraft' as table_name, COUNT(*) as row_count FROM {target}.aircraft
        UNION ALL
        SELECT 'systems', COUNT(*) FROM {target}.systems
        UNION ALL
        SELECT 'sensors', COUNT(*) FROM {target}.sensors
        UNION ALL
        SELECT 'sensor_readings', COUNT(*) FROM {target}.sensor_readings
    """)
    result.show()

    expected = {
        "aircraft": 20,
        "systems": 80,
        "sensors": 160,
        "sensor_readings": 345600,
    }

    rows = result.collect()
    all_ok = True
    for row in rows:
        name = row["table_name"]
        count = row["row_count"]
        exp = expected.get(name)
        status = "OK" if count == exp else f"MISMATCH (expected {exp})"
        print(f"  {name}: {count} rows - {status}")
        if count != exp:
            all_ok = False

    if all_ok:
        print("\nAll table counts match expected values.")
    else:
        print("\nWARNING: Some table counts do not match expected values.")


def add_table_comments(spark, catalog, lakehouse_schema):
    """Add table and column comments to help Databricks Genie understand the data."""
    target = f"`{catalog}`.`{lakehouse_schema}`"

    print("\nAdding table and column comments for Genie...")

    comments = [
        # Aircraft table
        f"COMMENT ON TABLE {target}.aircraft IS 'Fleet of aircraft with tail numbers, models, and operators'",
        f"COMMENT ON COLUMN {target}.aircraft.`:ID(Aircraft)` IS 'Unique aircraft identifier'",
        f"COMMENT ON COLUMN {target}.aircraft.tail_number IS 'Aircraft registration/tail number (e.g., N95040A)'",
        f"COMMENT ON COLUMN {target}.aircraft.model IS 'Aircraft model (e.g., B737-800, A320-200)'",
        f"COMMENT ON COLUMN {target}.aircraft.operator IS 'Airline operator name'",
        # Systems table
        f"COMMENT ON TABLE {target}.systems IS 'Aircraft systems including engines, avionics, and hydraulics'",
        f"COMMENT ON COLUMN {target}.systems.`:ID(System)` IS 'Unique system identifier'",
        f"COMMENT ON COLUMN {target}.systems.type IS 'System type (Engine, Avionics, Hydraulics)'",
        f"COMMENT ON COLUMN {target}.systems.name IS 'Human-readable system name'",
        # Sensors table
        f"COMMENT ON TABLE {target}.sensors IS 'Sensors installed on aircraft systems'",
        f"COMMENT ON COLUMN {target}.sensors.`:ID(Sensor)` IS 'Unique sensor identifier'",
        f"COMMENT ON COLUMN {target}.sensors.type IS 'Sensor type: EGT (Exhaust Gas Temperature in Celsius), Vibration (ips), N1Speed (RPM), FuelFlow (kg/s)'",
        f"COMMENT ON COLUMN {target}.sensors.unit IS 'Unit of measurement'",
        # Sensor readings table
        f"COMMENT ON TABLE {target}.sensor_readings IS 'Hourly sensor readings over 90 days (July-September 2024)'",
        f"COMMENT ON COLUMN {target}.sensor_readings.reading_id IS 'Unique reading identifier'",
        f"COMMENT ON COLUMN {target}.sensor_readings.sensor_id IS 'Foreign key to sensors table'",
        f"COMMENT ON COLUMN {target}.sensor_readings.timestamp IS 'Reading timestamp (hourly intervals)'",
        f"COMMENT ON COLUMN {target}.sensor_readings.value IS 'Sensor reading value in the sensor unit'",
    ]

    for sql in comments:
        spark.sql(sql)

    print("  Comments added.")


def main():
    config = get_config()
    catalog = config["catalog"]
    volume_schema = config["volume_schema"]
    volume = config["volume"]
    lakehouse_schema = config["lakehouse_schema"]

    print("==========================================")
    print("Create Lakehouse Tables (Step 4)")
    print("==========================================")
    print(f"  Catalog:          {catalog}")
    print(f"  Volume:           /Volumes/{catalog}/{volume_schema}/{volume}/")
    print(f"  Lakehouse schema: {catalog}.{lakehouse_schema}")
    print("==========================================\n")

    # Step 4.1: Create lakehouse schema
    create_lakehouse_schema(spark, catalog, lakehouse_schema)

    # Step 4.2: Create Delta Lake tables
    print("\nCreating Delta Lake tables from CSV files...")
    create_tables(spark, catalog, volume_schema, volume, lakehouse_schema)

    # Step 4.3: Verify tables
    verify_tables(spark, catalog, lakehouse_schema)

    # Step 4.4: Add comments for Genie
    add_table_comments(spark, catalog, lakehouse_schema)

    print("\n==========================================")
    print("Lakehouse setup complete!")
    print("==========================================")


if __name__ == "__main__":
    main()
