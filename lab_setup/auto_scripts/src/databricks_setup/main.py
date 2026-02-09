"""Main entry point for Databricks environment setup and cleanup.

Provides CLI interface for setting up (and tearing down) Databricks
clusters, libraries, data files, and lakehouse tables for the Neo4j workshop.
"""

import time
import traceback

import typer

from .cleanup import run_cleanup
from .cluster import get_or_create_cluster, wait_for_cluster_running
from .config import Config, SetupResult
from .data_upload import upload_data_files, verify_upload
from .lakehouse_tables import create_lakehouse_tables
from .libraries import ensure_libraries_installed
from .log import Level, close_log_file, init_log_file, log, log_to_file
from .notebooks import upload_notebooks, verify_notebook_upload
from .permissions import run_permissions_lockdown
from .utils import print_header
from .warehouse import get_or_start_warehouse

app = typer.Typer(
    name="databricks-setup",
    help="Setup and cleanup Databricks environment for Neo4j workshop.",
    add_completion=False,
)


@app.command()
def setup() -> None:
    """Set up Databricks environment for the Neo4j workshop.

    Runs three tracks sequentially:

      Track A: Create (or reuse) a compute cluster and install libraries.

      Track B: Upload data files and create lakehouse tables via SQL Warehouse.

      Track C: Lock down permissions (entitlements, group, UC grants, cluster ACL).

    All configuration is loaded from lab_setup/.env.
    The Neo4j Spark Connector requires Dedicated (Single User) access mode.
    """
    log_path = init_log_file()
    log(f"[dim]Log file: {log_path}[/dim]")

    start = time.monotonic()
    try:
        _run_setup()
        elapsed = time.monotonic() - start
        log(f"[green]Total elapsed time: {_fmt_elapsed(elapsed)}[/green]")
    except Exception as e:
        elapsed = time.monotonic() - start
        log(f"[red]Error: {e}[/red]", level=Level.ERROR)
        log_to_file(traceback.format_exc(), level=Level.ERROR)
        log(f"[dim]Failed after {_fmt_elapsed(elapsed)}[/dim]")
        raise typer.Exit(code=1) from None
    finally:
        close_log_file()


@app.command()
def cleanup(
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Delete permissions, notebooks, lakehouse tables, volume, schemas, and catalog.

    Removes everything created by the setup command except the compute
    cluster and entitlement changes.  Each step is idempotent —
    already-deleted resources are skipped.

    All configuration is loaded from lab_setup/.env.
    """
    log_path = init_log_file()
    log(f"[dim]Log file: {log_path}[/dim]")
    start = time.monotonic()
    try:
        _run_cleanup(yes=yes)
        elapsed = time.monotonic() - start
        log(f"[green]Total elapsed time: {_fmt_elapsed(elapsed)}[/green]")
    except Exception as e:
        elapsed = time.monotonic() - start
        log(f"[red]Error: {e}[/red]", level=Level.ERROR)
        log_to_file(traceback.format_exc(), level=Level.ERROR)
        log(f"[dim]Failed after {_fmt_elapsed(elapsed)}[/dim]")
        raise typer.Exit(code=1) from None
    finally:
        close_log_file()


def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed seconds as a human-readable string."""
    m, s = divmod(int(seconds), 60)
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _run_cleanup(*, yes: bool) -> None:
    """Load config, confirm, and run cleanup."""
    config = Config.load()
    client = config.prepare()
    warehouse_id = get_or_start_warehouse(client, config.warehouse)

    _print_cleanup_target(config)

    if not yes:
        typer.confirm("Proceed with cleanup?", abort=True)

    run_cleanup(
        client, warehouse_id, config.volume, config.warehouse.timeout_seconds,
        notebook_config=config.notebook,
    )


def _print_cleanup_target(config: Config) -> None:
    """Print what will be deleted."""
    print_header("Cleanup Target")
    log(f"Catalog:    {config.volume.catalog}")
    log(f"Schema:     {config.volume.catalog}.{config.volume.schema}")
    log(f"Volume:     {config.volume.full_path}")
    log(f"Lakehouse:  {config.volume.catalog}.{config.volume.lakehouse_schema}")
    log(f"Notebooks:  {config.notebook.workspace_folder}")
    log()
    log("[yellow]This will permanently delete the catalog and all its contents.[/yellow]")
    log("[yellow]The compute cluster will NOT be affected.[/yellow]")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _run_setup() -> None:
    """Load config, run Tracks A, B, and C, and print results."""
    config = Config.load()
    client = config.prepare()

    _print_config_summary(config)

    result = SetupResult()

    # Track A: Cluster + Libraries
    print_header("Track A: Cluster + Libraries")
    result.cluster_id = get_or_create_cluster(client, config.cluster, config.user_email or "")
    wait_for_cluster_running(client, result.cluster_id)
    ensure_libraries_installed(client, result.cluster_id, config.library)

    # Track B: Data Upload + Lakehouse Tables
    print_header("Track B: Data Upload + Lakehouse Tables")
    warehouse_id = get_or_start_warehouse(client, config.warehouse)
    upload_data_files(client, config.data, config.volume)
    verify_upload(client, config.volume)

    try:
        upload_notebooks(client, config.notebook)
        verify_notebook_upload(client, config.notebook)
    except Exception as e:
        log(f"[red]Notebook upload failed: {e}[/red]")
        result.notebooks_ok = False

    result.tables_ok = create_lakehouse_tables(
        client,
        warehouse_id,
        config.volume,
        config.warehouse.timeout_seconds,
    )

    # Track C: Permissions Lockdown
    result.lockdown_ok = run_permissions_lockdown(
        client,
        cluster_config=config.cluster,
        volume_config=config.volume,
        notebook_config=config.notebook,
    )

    _print_summary(result, config)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _print_config_summary(config: Config) -> None:
    """Print configuration overview before running tracks."""
    print_header("Databricks Environment Setup")

    log(f"Cluster:    {config.cluster.name}")
    log(f"Runtime:    {config.cluster.spark_version}")
    log(f"Node:       {config.cluster.get_node_type()} (single node)")
    if config.user_email:
        log(f"User:       {config.user_email}")
    log(f"Warehouse:  {config.warehouse.name}")
    log(f"Volume:     {config.volume.full_path}")
    log(f"Lakehouse:  {config.volume.catalog}.{config.volume.lakehouse_schema}")
    log(f"Notebooks:  {config.notebook.workspace_folder}")

    log()


def _print_summary(result: SetupResult, config: Config) -> None:
    """Print final setup summary."""
    print_header("Setup Complete" if result.success else "Setup Completed with Errors")

    log(f"Cluster ID:   {result.cluster_id}")
    log(f"Cluster Name: {config.cluster.name}")
    log(f"User:         {config.user_email}")
    log("Access Mode:  Dedicated (Single User)")

    log(f"Volume:       {config.volume.full_path}")
    log(f"Lakehouse:    {config.volume.catalog}.{config.volume.lakehouse_schema}")
    log(f"Notebooks:    {config.notebook.workspace_folder}")
    if not result.tables_ok:
        log("[red]Lakehouse table creation had errors.[/red]")
    if not result.notebooks_ok:
        log("[red]Notebook upload had errors.[/red]")
    if result.lockdown_ok:
        log("Lockdown:     [green]Permissions locked down[/green]")
    else:
        log("Lockdown:     [red]Permissions lockdown had errors[/red]")

    log()
    log("To check cluster status:")
    log(f"  databricks clusters get {result.cluster_id}")


if __name__ == "__main__":
    app()
