"""SQL Warehouse management and SQL execution.

Provides warehouse discovery and SQL statement execution via the Statement Execution API.
"""

import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    Disposition,
    ExecuteStatementRequestOnWaitTimeout,
    Format,
    StatementState,
)

from .config import WarehouseConfig
from .log import Level, log
from .models import SqlResult


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
    log(f"Looking for warehouse \"{config.name}\"...")

    warehouse_id = find_warehouse(client, config.name)
    if not warehouse_id:
        raise RuntimeError(
            f"Warehouse '{config.name}' not found. "
            "Set WAREHOUSE_NAME in .env or create a Starter Warehouse in your workspace."
        )

    log(f"  Found: {warehouse_id}")
    return warehouse_id


def execute_sql(
    client: WorkspaceClient,
    warehouse_id: str,
    sql: str,
    timeout_seconds: int = 600,
) -> SqlResult:
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
        state = response.status.state if response.status else "unknown"
        log(f"  SQL still {state} ({elapsed}s elapsed)...", level=Level.DEBUG)

        if response.statement_id:
            response = client.statement_execution.get_statement(response.statement_id)

    if response.status and response.status.state == StatementState.FAILED:
        error = response.status.error
        raise RuntimeError(f"SQL execution failed: {error}")

    return SqlResult(
        state=response.status.state if response.status else None,
        row_count=(response.manifest.total_row_count or 0) if response.manifest else 0,
    )


