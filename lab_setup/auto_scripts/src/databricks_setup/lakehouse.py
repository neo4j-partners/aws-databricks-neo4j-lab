"""Lakehouse table creation via Databricks Command Execution API.

Handles creating Delta Lake tables by executing Python code on a cluster.
"""

from enum import StrEnum
from pathlib import Path
from typing import Any

from databricks.sdk import WorkspaceClient
from rich.console import Console

from .config import DataConfig, VolumeConfig
from .utils import poll_until, print_header

console = Console()


class CommandStatus(StrEnum):
    """Command execution status."""

    QUEUED = "Queued"
    RUNNING = "Running"
    CANCELLING = "Cancelling"
    FINISHED = "Finished"
    CANCELLED = "Cancelled"
    ERROR = "Error"


def create_execution_context(
    client: WorkspaceClient,
    cluster_id: str,
) -> str:
    """Create an execution context for running Python commands.

    Args:
        client: Databricks workspace client.
        cluster_id: The cluster ID.

    Returns:
        The context ID.
    """
    console.print("Creating execution context...")

    response = client.api_client.do(
        "POST",
        "/api/1.2/contexts/create",
        body={"clusterId": cluster_id, "language": "python"},
    )

    context_id = response.get("id")
    if not context_id:
        raise RuntimeError(f"Failed to create execution context: {response}")

    console.print(f"  Context ID: {context_id}")
    return str(context_id)


def destroy_execution_context(
    client: WorkspaceClient,
    cluster_id: str,
    context_id: str,
) -> None:
    """Destroy an execution context.

    Args:
        client: Databricks workspace client.
        cluster_id: The cluster ID.
        context_id: The context ID to destroy.
    """
    console.print()
    console.print("Destroying execution context...")

    try:
        client.api_client.do(
            "POST",
            "/api/1.2/contexts/destroy",
            body={"clusterId": cluster_id, "contextId": context_id},
        )
        console.print("  Done.")
    except Exception as e:
        console.print(f"  [yellow]Warning: Failed to destroy context: {e}[/yellow]")


def execute_command(
    client: WorkspaceClient,
    cluster_id: str,
    context_id: str,
    code: str,
) -> str:
    """Execute a Python command and return the command ID.

    Args:
        client: Databricks workspace client.
        cluster_id: The cluster ID.
        context_id: The execution context ID.
        code: Python code to execute.

    Returns:
        The command ID.
    """
    response = client.api_client.do(
        "POST",
        "/api/1.2/commands/execute",
        body={
            "clusterId": cluster_id,
            "contextId": context_id,
            "language": "python",
            "command": code,
        },
    )

    command_id = response.get("id")
    if not command_id:
        raise RuntimeError(f"Failed to submit command: {response}")

    return str(command_id)


def get_command_status(
    client: WorkspaceClient,
    cluster_id: str,
    context_id: str,
    command_id: str,
) -> dict[str, Any]:
    """Get the status of a command execution.

    Args:
        client: Databricks workspace client.
        cluster_id: The cluster ID.
        context_id: The execution context ID.
        command_id: The command ID.

    Returns:
        The command status response.
    """
    result: dict[str, Any] = client.api_client.do(
        "GET",
        f"/api/1.2/commands/status?clusterId={cluster_id}&contextId={context_id}&commandId={command_id}",
    )
    return result


def wait_for_command(
    client: WorkspaceClient,
    cluster_id: str,
    context_id: str,
    command_id: str,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Wait for a command to complete.

    Args:
        client: Databricks workspace client.
        cluster_id: The cluster ID.
        context_id: The execution context ID.
        command_id: The command ID.
        timeout_seconds: Maximum time to wait.

    Returns:
        The final command status.
    """
    console.print("Waiting for table creation to complete...")

    def check_status() -> tuple[bool, dict[str, Any]]:
        status = get_command_status(client, cluster_id, context_id, command_id)
        state = status.get("status", "Unknown")
        console.print(f"  Status: {state}")

        if state in (CommandStatus.FINISHED.value, CommandStatus.CANCELLED.value, CommandStatus.ERROR.value):
            return True, status
        return False, status

    return poll_until(
        check_status,
        timeout_seconds=timeout_seconds,
        interval_seconds=10,
        description="command execution",
    )


def build_lakehouse_script(
    script_path: Path,
    volume_config: VolumeConfig,
) -> str:
    """Build the Python code to execute for lakehouse table creation.

    Prepends sys.argv overrides to the script content.

    Args:
        script_path: Path to the create_lakehouse_tables.py script.
        volume_config: Volume configuration.

    Returns:
        The complete Python code to execute.
    """
    script_content = script_path.read_text()

    preamble = f"""import sys
sys.argv = ["create_lakehouse_tables.py", "{volume_config.catalog}", "{volume_config.schema}", "{volume_config.volume}"]

"""
    return preamble + script_content


def create_lakehouse_tables(
    client: WorkspaceClient,
    cluster_id: str,
    data_config: DataConfig,
    volume_config: VolumeConfig,
) -> bool:
    """Create lakehouse tables by executing the Python script on the cluster.

    Args:
        client: Databricks workspace client.
        cluster_id: The cluster ID.
        data_config: Data configuration (contains script path).
        volume_config: Volume configuration.

    Returns:
        True if successful, False otherwise.
    """
    print_header("Creating Lakehouse Tables")

    if not data_config.lakehouse_script.exists():
        console.print(f"[red]Error: Script not found: {data_config.lakehouse_script}[/red]")
        return False

    context_id = create_execution_context(client, cluster_id)

    try:
        code = build_lakehouse_script(data_config.lakehouse_script, volume_config)
        console.print("Executing create_lakehouse_tables.py...")

        command_id = execute_command(client, cluster_id, context_id, code)
        console.print(f"  Command ID: {command_id}")
        console.print()

        result = wait_for_command(client, cluster_id, context_id, command_id)

        # Process results
        results = result.get("results", {})
        result_type = results.get("resultType", "unknown")

        if result_type in ("text", "table"):
            data = results.get("data", "")
            if data:
                console.print()
                console.print(data)
            return True
        elif result_type == "error":
            console.print()
            console.print("[red]Table creation FAILED:[/red]")
            console.print(results.get("summary", ""))
            console.print(results.get("cause", ""))
            return False
        else:
            console.print(f"[yellow]Unexpected result type: {result_type}[/yellow]")
            return True

    finally:
        destroy_execution_context(client, cluster_id, context_id)
