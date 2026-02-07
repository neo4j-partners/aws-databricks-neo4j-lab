"""Main entry point for Databricks environment setup and cleanup.

Provides CLI interface for setting up (and tearing down) Databricks
clusters, libraries, data files, and lakehouse tables for the Neo4j workshop.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

import typer
from databricks.sdk import WorkspaceClient
from rich.console import Console

from .cleanup import run_cleanup
from .cluster import get_or_create_cluster, wait_for_cluster_running
from .config import Config, SetupResult
from .data_upload import upload_data_files, verify_upload
from .lakehouse_tables import create_lakehouse_tables
from .libraries import ensure_libraries_installed
from .utils import print_header
from .warehouse import get_or_start_warehouse

app = typer.Typer(
    name="databricks-setup",
    help="Setup and cleanup Databricks environment for Neo4j workshop.",
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


@app.command()
def cleanup(
    volume: Annotated[
        str,
        typer.Argument(
            help="Target volume in format 'catalog.schema.volume'",
        ),
    ] = "aws-databricks-neo4j-lab.lab-schema.lab-volume",
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile", "-p",
            help="Databricks CLI profile to use",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes", "-y",
            help="Skip confirmation prompt",
        ),
    ] = False,
) -> None:
    """Delete lakehouse tables, volume, schemas, and catalog.

    Removes everything created by the setup command except the compute
    cluster.  Each step is idempotent — already-deleted resources are
    skipped.

    Examples:

        # Interactive confirmation
        databricks-setup cleanup

        # Skip confirmation
        databricks-setup cleanup --yes

        # Explicit volume
        databricks-setup cleanup my-catalog.my-schema.my-volume --yes
    """
    try:
        _run_cleanup(volume=volume, profile=profile, yes=yes)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None


def _run_cleanup(volume: str, profile: str | None, yes: bool) -> None:
    """Load config, confirm, and run cleanup."""
    config = Config.load()
    client = config.prepare(volume=volume, profile=profile)
    warehouse_id = get_or_start_warehouse(client, config.warehouse)

    _print_cleanup_target(config)

    if not yes:
        typer.confirm("Proceed with cleanup?", abort=True)

    run_cleanup(client, warehouse_id, config.volume, config.warehouse.timeout_seconds)


def _print_cleanup_target(config: Config) -> None:
    """Print what will be deleted."""
    print_header("Cleanup Target")
    console.print(f"Catalog:    {config.volume.catalog}")
    console.print(f"Schema:     {config.volume.catalog}.{config.volume.schema}")
    console.print(f"Volume:     {config.volume.full_path}")
    console.print(f"Lakehouse:  {config.volume.catalog}.{config.volume.lakehouse_schema}")
    console.print()
    console.print("[yellow]This will permanently delete the catalog and all its contents.[/yellow]")
    console.print("[yellow]The compute cluster will NOT be affected.[/yellow]")


# ---------------------------------------------------------------------------
# Track runners
# ---------------------------------------------------------------------------

def _run_cluster_track(
    client: WorkspaceClient,
    config: Config,
) -> str:
    """Track A: create/reuse cluster and install libraries.

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


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _run_setup(
    volume: str,
    cluster_only: bool,
    tables_only: bool,
    profile: str | None,
) -> None:
    """Load config, run parallel tracks, and print results."""
    run_cluster = not tables_only
    run_tables = not cluster_only

    config = Config.load()
    client = config.prepare(
        volume=volume if run_tables else None,
        profile=profile,
        resolve_user=run_cluster,
        require_data_dir=run_tables,
    )

    _print_config_summary(config, run_cluster=run_cluster, run_tables=run_tables)

    result = _run_tracks(client, config, run_cluster=run_cluster, run_tables=run_tables)

    _print_summary(result, config)


def _run_tracks(
    client: WorkspaceClient,
    config: Config,
    *,
    run_cluster: bool,
    run_tables: bool,
) -> SetupResult:
    """Execute Track A and/or Track B in parallel threads."""
    result = SetupResult()

    with ThreadPoolExecutor(max_workers=2) as executor:
        cluster_future = (
            executor.submit(_run_cluster_track, client, config)
            if run_cluster else None
        )
        tables_future = (
            executor.submit(_run_tables_track, client, config)
            if run_tables else None
        )

        if cluster_future is not None:
            result.cluster_id = cluster_future.result()
        if tables_future is not None:
            result.tables_ok = tables_future.result()

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _print_config_summary(
    config: Config,
    *,
    run_cluster: bool,
    run_tables: bool,
) -> None:
    """Print configuration overview before running tracks."""
    print_header("Databricks Environment Setup")

    if run_tables and not run_cluster:
        console.print("[cyan]Mode: Tables only (SQL Warehouse)[/cyan]")
    elif run_cluster and not run_tables:
        console.print("[cyan]Mode: Cluster only[/cyan]")
    else:
        console.print("[cyan]Mode: Full setup (parallel tracks)[/cyan]")

    if run_cluster:
        console.print(f"Cluster:    {config.cluster.name}")
        console.print(f"Runtime:    {config.cluster.spark_version}")
        console.print(f"Node:       {config.cluster.get_node_type()} (single node)")
        if config.user_email:
            console.print(f"User:       {config.user_email}")

    if run_tables:
        console.print(f"Warehouse:  {config.warehouse.name}")
        console.print(f"Volume:     {config.volume.full_path}")
        console.print(f"Lakehouse:  {config.volume.catalog}.{config.volume.lakehouse_schema}")

    console.print()


def _print_summary(result: SetupResult, config: Config) -> None:
    """Print final setup summary."""
    print_header("Setup Complete" if result.success else "Setup Completed with Errors")

    if result.cluster_id is not None:
        console.print(f"Cluster ID:   {result.cluster_id}")
        console.print(f"Cluster Name: {config.cluster.name}")
        console.print(f"User:         {config.user_email}")
        console.print("Access Mode:  Dedicated (Single User)")

    if result.tables_ok is not None:
        console.print(f"Volume:       {config.volume.full_path}")
        console.print(f"Lakehouse:    {config.volume.catalog}.{config.volume.lakehouse_schema}")
        if not result.tables_ok:
            console.print("[red]Lakehouse table creation had errors.[/red]")

    console.print()
    if result.cluster_id is not None:
        console.print("To check cluster status:")
        console.print(f"  databricks clusters get {result.cluster_id}")


if __name__ == "__main__":
    app()
