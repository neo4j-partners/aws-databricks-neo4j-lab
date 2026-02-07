"""Main entry point for Databricks environment setup.

Provides CLI interface for setting up Databricks clusters, libraries,
data files, and lakehouse tables for the Neo4j workshop.

Runs two parallel tracks:
  Track A: Cluster creation + library installation
  Track B: Data upload + lakehouse table creation (via SQL Warehouse)
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

import typer
from databricks.sdk import WorkspaceClient
from rich.console import Console

from .cluster import get_or_create_cluster, wait_for_cluster_running
from .config import Config, VolumeConfig
from .data_upload import upload_data_files, verify_upload
from .lakehouse_tables import create_lakehouse_tables
from .libraries import ensure_libraries_installed
from .utils import (
    get_current_user,
    get_workspace_client,
    print_header,
)
from .warehouse import get_or_start_warehouse

app = typer.Typer(
    name="databricks-setup",
    help="Setup Databricks environment for Neo4j workshop.",
    add_completion=False,
)

console = Console()


@app.command()
def setup(
    volume: Annotated[
        str,
        typer.Argument(
            help="Target volume in format 'catalog.schema.volume'",
        ),
    ] = "aws-databricks-neo4j-lab.lab-schema.lab-volume",
    cluster_only: Annotated[
        bool,
        typer.Option(
            "--cluster-only",
            help="Only create cluster and install libraries (skip data upload and tables)",
        ),
    ] = False,
    tables_only: Annotated[
        bool,
        typer.Option(
            "--tables-only",
            help="Only upload data and create lakehouse tables (skip cluster creation)",
        ),
    ] = False,
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile", "-p",
            help="Databricks CLI profile to use",
        ),
    ] = None,
) -> None:
    """Set up Databricks environment for the Neo4j workshop.

    Runs two parallel tracks by default:

      Track A: Create (or reuse) a compute cluster and install libraries.

      Track B: Upload data files and create lakehouse tables via SQL Warehouse.

    Configuration is loaded from lab_setup/.env (CLUSTER_NAME, USER_EMAIL, etc.).
    The Neo4j Spark Connector requires Dedicated (Single User) access mode.

    Examples:

        # All defaults (both tracks run in parallel)
        databricks-setup

        # Cluster + libraries only
        databricks-setup --cluster-only

        # Data upload + lakehouse tables only
        databricks-setup --tables-only

        # Explicit volume
        databricks-setup my-catalog.my-schema.my-volume
    """
    if cluster_only and tables_only:
        console.print("[red]Error: --cluster-only and --tables-only are mutually exclusive[/red]")
        raise typer.Exit(code=1)

    try:
        _run_setup(
            volume=volume,
            cluster_only=cluster_only,
            tables_only=tables_only,
            profile=profile,
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None


def _run_cluster_track(
    client: WorkspaceClient,
    config: Config,
) -> str:
    """Track A: create/reuse cluster and install libraries.

    Args:
        client: Databricks workspace client.
        config: Full configuration.

    Returns:
        The cluster ID.
    """
    print_header("Track A: Cluster + Libraries")
    cluster_id = get_or_create_cluster(client, config.cluster, config.user_email or "")
    wait_for_cluster_running(client, cluster_id)
    ensure_libraries_installed(client, cluster_id, config.library)
    return cluster_id


def _run_tables_track(
    client: WorkspaceClient,
    config: Config,
) -> bool:
    """Track B: upload data and create lakehouse tables via SQL Warehouse.

    Args:
        client: Databricks workspace client.
        config: Full configuration.

    Returns:
        True if successful, False otherwise.
    """
    print_header("Track B: Data Upload + Lakehouse Tables")
    warehouse_id = get_or_start_warehouse(client, config.warehouse)
    upload_data_files(client, config.data, config.volume)
    verify_upload(client, config.volume)
    return create_lakehouse_tables(
        client,
        warehouse_id,
        config.volume,
        config.warehouse.timeout_seconds,
    )


def _run_setup(
    volume: str,
    cluster_only: bool,
    tables_only: bool,
    profile: str | None,
) -> None:
    """Internal implementation of setup command."""

    # Load configuration
    config = Config.load()

    # Parse volume specification (needed unless cluster-only)
    if not cluster_only:
        config.volume = VolumeConfig.from_string(volume)

    # Use profile from CLI or config
    effective_profile = profile or config.databricks_profile

    # Create Databricks client
    client = get_workspace_client(effective_profile)

    # Resolve user email (needed for cluster track)
    if not tables_only and not config.user_email:
        console.print("Detecting current Databricks user...")
        config.user_email = get_current_user(client)

    # Validate data directory exists (needed for tables track)
    if not cluster_only and not config.data.data_dir.exists():
        raise RuntimeError(f"Data directory not found: {config.data.data_dir}")

    # Print configuration summary
    _print_config_summary(config, cluster_only, tables_only)

    # Run tracks
    cluster_id: str | None = None
    tables_ok: bool | None = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        cluster_future = None
        tables_future = None

        # Track A: cluster + libraries (skip if --tables-only)
        if not tables_only:
            cluster_future = executor.submit(_run_cluster_track, client, config)

        # Track B: upload + lakehouse tables (skip if --cluster-only)
        if not cluster_only:
            tables_future = executor.submit(_run_tables_track, client, config)

        # Gather results — re-raise exceptions from threads
        if cluster_future is not None:
            cluster_id = cluster_future.result()
        if tables_future is not None:
            tables_ok = tables_future.result()

    # Final summary
    _print_summary(cluster_id, tables_ok, config)


def _print_config_summary(
    config: Config,
    cluster_only: bool,
    tables_only: bool,
) -> None:
    """Print configuration overview before running tracks."""
    print_header("Databricks Environment Setup")

    if tables_only:
        console.print("[cyan]Mode: Tables only (SQL Warehouse)[/cyan]")
    elif cluster_only:
        console.print("[cyan]Mode: Cluster only[/cyan]")
    else:
        console.print("[cyan]Mode: Full setup (parallel tracks)[/cyan]")

    if not tables_only:
        console.print(f"Cluster:    {config.cluster.name}")
        console.print(f"Runtime:    {config.cluster.spark_version}")
        console.print(f"Node:       {config.cluster.get_node_type()} (single node)")
        if config.user_email:
            console.print(f"User:       {config.user_email}")

    if not cluster_only:
        console.print(f"Warehouse:  {config.warehouse.name}")
        console.print(f"Volume:     {config.volume.full_path}")
        console.print(f"Lakehouse:  {config.volume.catalog}.{config.volume.lakehouse_schema}")

    console.print()


def _print_summary(
    cluster_id: str | None,
    tables_ok: bool | None,
    config: Config,
) -> None:
    """Print final setup summary."""
    all_ok = (tables_ok is None or tables_ok) and cluster_id is not None or tables_ok

    print_header("Setup Complete" if all_ok else "Setup Completed with Errors")

    if cluster_id is not None:
        console.print(f"Cluster ID:   {cluster_id}")
        console.print(f"Cluster Name: {config.cluster.name}")
        console.print(f"User:         {config.user_email}")
        console.print("Access Mode:  Dedicated (Single User)")

    if tables_ok is not None:
        console.print(f"Volume:       {config.volume.full_path}")
        console.print(f"Lakehouse:    {config.volume.catalog}.{config.volume.lakehouse_schema}")
        if not tables_ok:
            console.print("[red]Lakehouse table creation had errors.[/red]")

    console.print()
    if cluster_id is not None:
        console.print("To check cluster status:")
        console.print(f"  databricks clusters get {cluster_id}")


if __name__ == "__main__":
    app()
