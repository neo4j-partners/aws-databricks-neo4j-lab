"""Lakehouse table definitions and creation logic.

Single source of truth for all Delta Lake table SQL used by Databricks Genie.
Creates tables via Statement Execution API on a SQL Warehouse.
"""

from databricks.sdk import WorkspaceClient
from rich.console import Console

from .config import VolumeConfig
from .models import SqlStep
from .utils import print_header
from .warehouse import execute_sql

console = Console()

EXPECTED_ROW_COUNTS: dict[str, int] = {
    "aircraft": 20,
    "systems": 80,
    "sensors": 160,
    "sensor_readings": 345600,
}


def _lakehouse_target(volume_config: VolumeConfig) -> str:
    """Return the backtick-quoted `catalog`.`lakehouse_schema` target."""
    return f"`{volume_config.catalog}`.`{volume_config.lakehouse_schema}`"


def get_table_creation_sql(
    volume_config: VolumeConfig,
) -> list[SqlStep]:
    """Return labelled SQL steps for schema and table creation.

    Args:
        volume_config: Volume configuration with catalog, schema, volume, lakehouse_schema.

    Returns:
        List of SqlStep(description, sql) for each step.
    """
    volume_path = volume_config.volumes_path
    target = _lakehouse_target(volume_config)
    tblprops = "TBLPROPERTIES ('delta.columnMapping.mode' = 'name')"

    return [
        SqlStep(
            description="Creating lakehouse schema",
            sql=f"CREATE SCHEMA IF NOT EXISTS {target}",
        ),
        SqlStep(
            description="Creating aircraft table",
            sql=f"""
            CREATE TABLE IF NOT EXISTS {target}.aircraft
            {tblprops}
            AS SELECT * FROM read_files('{volume_path}/nodes_aircraft.csv',
                format => 'csv', header => 'true', inferSchema => 'true')
            """,
        ),
        SqlStep(
            description="Creating systems table",
            sql=f"""
            CREATE TABLE IF NOT EXISTS {target}.systems
            {tblprops}
            AS SELECT * FROM read_files('{volume_path}/nodes_systems.csv',
                format => 'csv', header => 'true', inferSchema => 'true')
            """,
        ),
        SqlStep(
            description="Creating sensors table",
            sql=f"""
            CREATE TABLE IF NOT EXISTS {target}.sensors
            {tblprops}
            AS SELECT * FROM read_files('{volume_path}/nodes_sensors.csv',
                format => 'csv', header => 'true', inferSchema => 'true')
            """,
        ),
        SqlStep(
            description="Creating sensor_readings table",
            sql=f"""
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
        ),
    ]


def get_comment_sql(volume_config: VolumeConfig) -> list[str]:
    """Return all COMMENT statements for tables and columns.

    Includes both table-level and column-level comments to help
    Databricks Genie understand the data model.

    Args:
        volume_config: Volume configuration.

    Returns:
        List of SQL COMMENT statements.
    """
    target = _lakehouse_target(volume_config)

    return [
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


def get_verification_sql(volume_config: VolumeConfig) -> str:
    """Return the UNION ALL row count verification query.

    Args:
        volume_config: Volume configuration.

    Returns:
        SQL query string.
    """
    target = _lakehouse_target(volume_config)

    return f"""
        SELECT 'aircraft' as table_name, COUNT(*) as row_count FROM {target}.aircraft
        UNION ALL
        SELECT 'systems', COUNT(*) FROM {target}.systems
        UNION ALL
        SELECT 'sensors', COUNT(*) FROM {target}.sensors
        UNION ALL
        SELECT 'sensor_readings', COUNT(*) FROM {target}.sensor_readings
    """


def create_lakehouse_tables(
    client: WorkspaceClient,
    warehouse_id: str,
    volume_config: VolumeConfig,
    timeout_seconds: int = 600,
) -> bool:
    """Create lakehouse tables via Statement Execution API.

    Args:
        client: Databricks workspace client.
        warehouse_id: SQL Warehouse ID.
        volume_config: Volume configuration.
        timeout_seconds: Timeout per SQL statement.

    Returns:
        True if successful, False otherwise.
    """
    print_header("Creating Lakehouse Tables")

    try:
        # Create schema and tables
        for step in get_table_creation_sql(volume_config):
            console.print(f"  {step.description}...")
            execute_sql(client, warehouse_id, step.sql, timeout_seconds)
            console.print("    Done.")

        # Verify row counts
        console.print()
        console.print("Verifying table row counts...")
        execute_sql(client, warehouse_id, get_verification_sql(volume_config), timeout_seconds)
        console.print("  Verification complete.")

        # Add table and column comments
        console.print()
        console.print("Adding table and column comments...")
        for comment_sql in get_comment_sql(volume_config):
            execute_sql(client, warehouse_id, comment_sql, timeout_seconds)
        console.print("  Done.")

        return True

    except Exception as e:
        console.print(f"[red]Error creating tables: {e}[/red]")
        return False
