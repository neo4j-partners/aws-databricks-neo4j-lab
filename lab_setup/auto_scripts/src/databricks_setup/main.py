"""Main entry point for Databricks environment setup.

Provides CLI interface for setting up Databricks clusters, libraries,
data files, and lakehouse tables for the Neo4j workshop.
"""

from typing import Annotated

import typer
from databricks.sdk import WorkspaceClient
from rich.console import Console

from .cluster import get_or_create_cluster, wait_for_cluster_running
from .config import Config, VolumeConfig
from .data_upload import upload_data_files, verify_upload
from .lakehouse import create_lakehouse_tables
from .libraries import ensure_libraries_installed
from .utils import (
    get_current_user,
    get_workspace_client,
    print_config_summary,
    print_header,
)
from .warehouse import create_lakehouse_tables_serverless, get_or_start_warehouse

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
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile", "-p",
            help="Databricks CLI profile to use",
        ),
    ] = None,
) -> None:
    """Set up Databricks environment for the Neo4j workshop.

    Creates (or reuses) a compute cluster, installs libraries, uploads data files,
    and creates lakehouse tables.

    Configuration is loaded from lab_setup/.env (CLUSTER_NAME, USER_EMAIL, etc.).
    The Neo4j Spark Connector requires Dedicated (Single User) access mode.

    Examples:

        # All defaults
        databricks-setup

        # Cluster + libraries only
        databricks-setup --cluster-only

        # Explicit volume
        databricks-setup my-catalog.my-schema.my-volume
    """
    try:
        _run_setup(
            volume=volume,
            cluster_only=cluster_only,
            profile=profile,
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None


def _run_setup(
    volume: str,
    cluster_only: bool,
    profile: str | None,
) -> None:
    """Internal implementation of setup command."""

    # Load configuration
    config = Config.load()

    # Parse volume specification
    if not cluster_only:
        config.volume = VolumeConfig.from_string(volume)

    # Use profile from CLI or config
    effective_profile = profile or config.databricks_profile

    # Create Databricks client
    client = get_workspace_client(effective_profile)

    # Resolve user email (only needed for cluster mode)
    if not config.use_serverless:
        if not config.user_email:
            console.print("Detecting current Databricks user...")
            config.user_email = get_current_user(client)

    # Validate data files exist (unless cluster-only mode)
    if not cluster_only:
        if not config.data.data_dir.exists():
            raise RuntimeError(f"Data directory not found: {config.data.data_dir}")
        # Only need lakehouse script for cluster mode
        if not config.use_serverless and not config.data.lakehouse_script.exists():
            raise RuntimeError(f"Python script not found: {config.data.lakehouse_script}")

    # Route to serverless or cluster mode
    if config.use_serverless:
        _run_serverless_setup(client, config, cluster_only)
    else:
        _run_cluster_setup(client, config, cluster_only, volume)


def _run_serverless_setup(
    client: WorkspaceClient,
    config: Config,
    cluster_only: bool,
) -> None:
    """Run setup using serverless SQL warehouse."""

    # Print configuration summary
    _print_serverless_summary(config)

    if cluster_only:
        console.print("[yellow]--cluster-only has no effect in serverless mode[/yellow]")

    # Step 1: Find warehouse
    warehouse_id = get_or_start_warehouse(client, config.warehouse)

    # Step 2: Upload data files
    upload_data_files(client, config.data, config.volume)
    verify_upload(client, config.volume)

    # Step 3: Create lakehouse tables via SQL warehouse
    success = create_lakehouse_tables_serverless(
        client,
        warehouse_id,
        config.volume,
        config.warehouse.timeout_seconds,
    )

    # Final summary
    _print_serverless_final_summary(warehouse_id, config, success)


def _run_cluster_setup(
    client: WorkspaceClient,
    config: Config,
    cluster_only: bool,
    volume: str,
) -> None:
    """Run setup using dedicated cluster."""
    # Print configuration summary
    print_config_summary(
        volume_path=config.volume.full_path if not cluster_only else None,
        cluster_name=config.cluster.name,
        spark_version=config.cluster.spark_version,
        runtime_engine=config.cluster.runtime_engine,
        node_type=config.cluster.get_node_type(),
        user_email=config.user_email or "",
        timeout_minutes=config.cluster.autotermination_minutes,
        cluster_only=cluster_only,
    )

    # Step 1: Get or create cluster
    cluster_id = get_or_create_cluster(client, config.cluster, config.user_email or "")

    # Step 2: Wait for cluster to be running
    wait_for_cluster_running(client, cluster_id)

    # Step 3: Install libraries
    ensure_libraries_installed(client, cluster_id, config.library)

    if cluster_only:
        # Print cluster-only summary and exit
        _print_cluster_only_summary(cluster_id, config, volume)
        return

    # Step 4: Upload data files
    upload_data_files(client, config.data, config.volume)
    verify_upload(client, config.volume)

    # Step 5: Create lakehouse tables
    success = create_lakehouse_tables(client, cluster_id, config.data, config.volume)

    # Final summary
    _print_final_summary(cluster_id, config, success)


def _print_cluster_only_summary(
    cluster_id: str,
    config: Config,
    volume: str,
) -> None:
    """Print summary for cluster-only mode."""
    print_header("Cluster Setup Complete")
    console.print(f"Cluster ID:   {cluster_id}")
    console.print(f"Cluster Name: {config.cluster.name}")
    console.print(f"User:         {config.user_email}")
    console.print("Access Mode:  Dedicated (Single User)")
    console.print()
    console.print("[yellow]Skipped: data upload and lakehouse table creation (--cluster-only)[/yellow]")
    console.print()
    console.print("To check status later:")
    console.print(f"  databricks clusters get {cluster_id}")
    console.print()
    console.print("To run the full setup later:")
    console.print(f"  databricks-setup {volume}")


def _print_final_summary(
    cluster_id: str,
    config: Config,
    success: bool,
) -> None:
    """Print final setup summary."""
    print_header("Setup Complete" if success else "Setup Completed with Errors")
    console.print(f"Cluster ID:   {cluster_id}")
    console.print(f"Cluster Name: {config.cluster.name}")
    console.print(f"User:         {config.user_email}")
    console.print("Access Mode:  Dedicated (Single User)")
    console.print(f"Volume:       {config.volume.full_path}")
    console.print(f"Lakehouse:    {config.volume.catalog}.lakehouse")
    console.print()
    console.print("To check status later:")
    console.print(f"  databricks clusters get {cluster_id}")


def _print_serverless_summary(config: Config) -> None:
    """Print configuration summary for serverless mode."""
    print_header("Databricks Environment Setup (Serverless)")
    console.print("[cyan]Mode:      Serverless (SQL Warehouse)[/cyan]")
    console.print(f"Warehouse: {config.warehouse.name}")
    console.print(f"Volume:    {config.volume.full_path}")
    console.print()


def _print_serverless_final_summary(
    warehouse_id: str,
    config: Config,
    success: bool,
) -> None:
    """Print final summary for serverless mode."""
    print_header("Setup Complete" if success else "Setup Completed with Errors")
    console.print(f"Warehouse:  {config.warehouse.name} ({warehouse_id})")
    console.print(f"Volume:     {config.volume.full_path}")
    console.print(f"Lakehouse:  {config.volume.catalog}.{config.volume.lakehouse_schema}")
    console.print()
    console.print("[green]No cluster required - using serverless SQL warehouse[/green]")


if __name__ == "__main__":
    app()
