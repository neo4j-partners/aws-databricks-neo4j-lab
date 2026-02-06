"""SQL Warehouse operations for serverless mode.

Executes SQL statements via the Statement Execution API instead of using a cluster.
"""

from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    Disposition,
    ExecuteStatementRequestOnWaitTimeout,
    Format,
    StatementState,
)
from rich.console import Console

from .config import VolumeConfig, WarehouseConfig
from .utils import print_header

console = Console()


def find_warehouse(client: WorkspaceClient, warehouse_name: str) -> str | None:
    """Find a SQL warehouse by name.

    Args:
        client: Databricks workspace client.
        warehouse_name: Name of the warehouse to find.

    Returns:
        Warehouse ID if found, None otherwise.
    """
    warehouses = client.warehouses.list()
    for wh in warehouses:
        if wh.name == warehouse_name:
            return wh.id
    return None


def get_or_start_warehouse(
    client: WorkspaceClient,
    config: WarehouseConfig,
) -> str:
    """Get a warehouse ID, starting it if necessary.

    Args:
        client: Databricks workspace client.
        config: Warehouse configuration.

    Returns:
        The warehouse ID.

    Raises:
        RuntimeError: If warehouse not found.
    """
    console.print(f"Looking for warehouse \"{config.name}\"...")

    warehouse_id = find_warehouse(client, config.name)
    if not warehouse_id:
        raise RuntimeError(
            f"Warehouse '{config.name}' not found. "
            "Set WAREHOUSE_NAME in .env or create a Starter Warehouse in your workspace."
        )

    console.print(f"  Found: {warehouse_id}")
    return warehouse_id


def execute_sql(
    client: WorkspaceClient,
    warehouse_id: str,
    sql: str,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    """Execute a SQL statement on a warehouse.

    Args:
        client: Databricks workspace client.
        warehouse_id: The warehouse ID.
        sql: SQL statement to execute.
        timeout_seconds: Maximum total wait time.

    Returns:
        Statement execution result.

    Raises:
        RuntimeError: If statement fails.
        TimeoutError: If statement doesn't complete in time.
    """
    import time

    # API max wait is 50 seconds, so we use that and poll if needed
    api_wait = "50s"

    response = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=sql,
        wait_timeout=api_wait,
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
        disposition=Disposition.INLINE,
        format=Format.JSON_ARRAY,
    )

    # Poll if statement is still running
    elapsed = 0
    poll_interval = 5
    while response.status and response.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        if elapsed >= timeout_seconds:
            # Cancel the statement
            if response.statement_id:
                client.statement_execution.cancel_execution(response.statement_id)
            raise TimeoutError(f"SQL execution timed out after {timeout_seconds}s")

        time.sleep(poll_interval)
        elapsed += poll_interval

        if response.statement_id:
            response = client.statement_execution.get_statement(response.statement_id)

    if response.status and response.status.state == StatementState.FAILED:
        error = response.status.error
        raise RuntimeError(f"SQL execution failed: {error}")

    return {
        "state": response.status.state if response.status else None,
        "row_count": response.manifest.total_row_count if response.manifest else 0,
    }


def create_lakehouse_tables_serverless(
    client: WorkspaceClient,
    warehouse_id: str,
    volume_config: VolumeConfig,
    timeout_seconds: int = 600,
) -> bool:
    """Create lakehouse tables using SQL warehouse (serverless mode).

    Args:
        client: Databricks workspace client.
        warehouse_id: SQL warehouse ID.
        volume_config: Volume configuration.
        timeout_seconds: Timeout for each statement.

    Returns:
        True if successful, False otherwise.
    """
    print_header("Creating Lakehouse Tables (Serverless)")

    catalog = volume_config.catalog
    volume_schema = volume_config.schema
    volume = volume_config.volume
    lakehouse_schema = volume_config.lakehouse_schema
    volume_path = f"/Volumes/{catalog}/{volume_schema}/{volume}"
    target = f"`{catalog}`.`{lakehouse_schema}`"

    tblprops = "TBLPROPERTIES ('delta.columnMapping.mode' = 'name')"

    statements = [
        # Create schema
        (
            "Creating lakehouse schema",
            f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{lakehouse_schema}`",
        ),
        # Aircraft table
        (
            "Creating aircraft table",
            f"""
            CREATE TABLE IF NOT EXISTS {target}.aircraft
            {tblprops}
            AS SELECT * FROM read_files('{volume_path}/nodes_aircraft.csv',
                format => 'csv', header => 'true', inferSchema => 'true')
            """,
        ),
        # Systems table
        (
            "Creating systems table",
            f"""
            CREATE TABLE IF NOT EXISTS {target}.systems
            {tblprops}
            AS SELECT * FROM read_files('{volume_path}/nodes_systems.csv',
                format => 'csv', header => 'true', inferSchema => 'true')
            """,
        ),
        # Sensors table
        (
            "Creating sensors table",
            f"""
            CREATE TABLE IF NOT EXISTS {target}.sensors
            {tblprops}
            AS SELECT * FROM read_files('{volume_path}/nodes_sensors.csv',
                format => 'csv', header => 'true', inferSchema => 'true')
            """,
        ),
        # Sensor readings table
        (
            "Creating sensor_readings table",
            f"""
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

    # Table comments
    comments = [
        f"COMMENT ON TABLE {target}.aircraft IS 'Fleet of aircraft with tail numbers, models, and operators'",
        f"COMMENT ON TABLE {target}.systems IS 'Aircraft systems including engines, avionics, and hydraulics'",
        f"COMMENT ON TABLE {target}.sensors IS 'Sensors installed on aircraft systems'",
        f"COMMENT ON TABLE {target}.sensor_readings IS 'Hourly sensor readings over 90 days (July-September 2024)'",
    ]

    try:
        # Execute table creation statements
        for desc, sql in statements:
            console.print(f"  {desc}...")
            execute_sql(client, warehouse_id, sql, timeout_seconds)
            console.print("    Done.")

        # Verify tables
        console.print()
        console.print("Verifying table row counts...")
        verify_sql = f"""
            SELECT 'aircraft' as table_name, COUNT(*) as row_count FROM {target}.aircraft
            UNION ALL
            SELECT 'systems', COUNT(*) FROM {target}.systems
            UNION ALL
            SELECT 'sensors', COUNT(*) FROM {target}.sensors
            UNION ALL
            SELECT 'sensor_readings', COUNT(*) FROM {target}.sensor_readings
        """
        execute_sql(client, warehouse_id, verify_sql, timeout_seconds)

        # Add comments
        console.print()
        console.print("Adding table comments...")
        for comment_sql in comments:
            execute_sql(client, warehouse_id, comment_sql, timeout_seconds)
        console.print("  Done.")

        return True

    except Exception as e:
        console.print(f"[red]Error creating tables: {e}[/red]")
        return False
