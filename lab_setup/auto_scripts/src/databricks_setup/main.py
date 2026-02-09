"""Main entry point for Databricks environment setup, cleanup, and user management.

Provides CLI interface for setting up data/permissions, managing per-user
clusters, and tearing down workshop resources.
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import typer
from rich.table import Table

from .cleanup import run_cleanup
from .cluster import (
    create_user_cluster,
    delete_cluster,
    find_user_clusters,
    wait_for_cluster_running,
)
from .config import Config, SetupResult
from .data_upload import upload_data_files, verify_upload
from .groups import (
    WORKSHOP_GROUP,
    add_members_to_group,
    get_account_client,
    get_group_member_ids,
    remove_members_from_group,
    require_group,
)
from .lakehouse_tables import create_lakehouse_tables
from .libraries import ensure_libraries_installed
from .log import Level, close_log_file, init_log_file, log, log_to_file
from .notebooks import upload_notebooks, verify_notebook_upload
from .permissions import run_permissions_lockdown
from .users import (
    cluster_name_for_user,
    create_workspace_user,
    find_workspace_user,
    parse_csv,
)
from .utils import print_header
from .warehouse import get_or_start_warehouse

# Resolve default CSV path relative to lab_setup/
_LAB_SETUP_DIR = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_CSV = _LAB_SETUP_DIR / "users.csv"

app = typer.Typer(
    name="databricks-setup",
    help="Setup and cleanup Databricks environment for Neo4j workshop.",
    add_completion=False,
)


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

@app.command()
def setup() -> None:
    """Set up Databricks environment for the Neo4j workshop.

    Runs two tracks sequentially:

      Track B: Upload data files and create lakehouse tables via SQL Warehouse.

      Track C: Lock down permissions (entitlements, group, UC grants, folder ACL).

    Per-user clusters are created separately via ``add-users``.
    All configuration is loaded from lab_setup/.env.
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


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

@app.command()
def cleanup(
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Delete permissions, notebooks, lakehouse tables, volume, schemas, and catalog.

    Removes everything created by the setup command.  Per-user clusters
    are removed via ``remove-users``.  Each step is idempotent.

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


# ---------------------------------------------------------------------------
# add-users
# ---------------------------------------------------------------------------

@app.command("add-users")
def add_users(
    file: Path = typer.Option(
        _DEFAULT_CSV,
        "--file", "-f",
        help="Path to CSV file with an 'email' column.",
    ),
    skip_clusters: bool = typer.Option(
        False,
        "--skip-clusters",
        help="Only add users to group, skip cluster creation.",
    ),
) -> None:
    """Add users from a CSV → create workspace accounts → add to group → create per-user clusters."""
    log_path = init_log_file()
    log(f"[dim]Log file: {log_path}[/dim]")

    start = time.monotonic()
    try:
        _run_add_users(file, skip_clusters=skip_clusters)
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


# ---------------------------------------------------------------------------
# remove-users
# ---------------------------------------------------------------------------

@app.command("remove-users")
def remove_users(
    file: Path = typer.Option(
        _DEFAULT_CSV,
        "--file", "-f",
        help="Path to CSV file with an 'email' column.",
    ),
    keep_clusters: bool = typer.Option(
        False,
        "--keep-clusters",
        help="Skip cluster deletion.",
    ),
) -> None:
    """Remove users from the workshop group and delete their per-user clusters."""
    log_path = init_log_file()
    log(f"[dim]Log file: {log_path}[/dim]")

    start = time.monotonic()
    try:
        _run_remove_users(file, keep_clusters=keep_clusters)
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


# ---------------------------------------------------------------------------
# list-users
# ---------------------------------------------------------------------------

@app.command("list-users")
def list_users() -> None:
    """List members of the workshop group and their cluster status."""
    log_path = init_log_file()
    log(f"[dim]Log file: {log_path}[/dim]")

    try:
        _run_list_users()
    except Exception as e:
        log(f"[red]Error: {e}[/red]", level=Level.ERROR)
        log_to_file(traceback.format_exc(), level=Level.ERROR)
        raise typer.Exit(code=1) from None
    finally:
        close_log_file()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed seconds as a human-readable string."""
    m, s = divmod(int(seconds), 60)
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# setup orchestration
# ---------------------------------------------------------------------------

def _run_setup() -> None:
    """Load config, run Tracks B and C, and print results."""
    config = Config.load()
    client = config.prepare()

    _print_config_summary(config)

    result = SetupResult()

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
        volume_config=config.volume,
        notebook_config=config.notebook,
    )

    _print_summary(result, config)


# ---------------------------------------------------------------------------
# cleanup orchestration
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# add-users orchestration
# ---------------------------------------------------------------------------

def _run_add_users(csv_path: Path, *, skip_clusters: bool) -> None:
    """Parse CSV, find/create users, add to group, create per-user clusters."""
    config = Config.load()
    client = config.prepare()
    acct = get_account_client()

    emails = parse_csv(csv_path)
    log(f"Read {len(emails)} unique email(s) from {csv_path}")

    print_header("Adding Users")

    grp = require_group(client, WORKSHOP_GROUP)
    group_id: str = grp.id  # type: ignore[assignment]
    existing_members = get_group_member_ids(acct, group_id)

    added = 0
    already = 0
    created = 0
    failed_create = 0
    to_add: list[str] = []
    user_emails_added: list[str] = []

    for email in emails:
        user = find_workspace_user(client, email)
        if user is None or user.id is None:
            try:
                user = create_workspace_user(client, email)
                created += 1
            except Exception as exc:
                log(f"  [red]Failed to create user {email}: {exc}[/red]")
                failed_create += 1
                continue

        if user.id in existing_members:
            already += 1
            log(f"  {email} — already a member")
        else:
            to_add.append(user.id)

        user_emails_added.append(email)

    if to_add:
        add_members_to_group(acct, group_id, to_add)
        added = len(to_add)

    log()
    log(f"  Added to group: {added}")
    log(f"  Created in workspace: {created}")
    log(f"  Already member: {already}")
    if failed_create:
        log(f"  [red]Failed to create: {failed_create}[/red]")

    # --- Per-user clusters ------------------------------------------------
    if skip_clusters:
        log()
        log("[dim]Skipping cluster creation (--skip-clusters).[/dim]")
        return

    if not user_emails_added:
        log()
        log("[yellow]No users to create clusters for.[/yellow]")
        return

    print_header("Creating Per-User Clusters")

    # Phase 1: create/find all clusters (fast API calls)
    cluster_ids: list[tuple[str, str]] = []  # (email, cluster_id)
    for email in user_emails_added:
        try:
            cid = create_user_cluster(client, config.cluster, email)
            cluster_ids.append((email, cid))
        except Exception as exc:
            log(f"  [red]Failed to create cluster for {email}: {exc}[/red]")

    # Phase 2: wait for all clusters to reach RUNNING
    log()
    log(f"Waiting for {len(cluster_ids)} cluster(s) to start...")
    for email, cid in cluster_ids:
        try:
            wait_for_cluster_running(client, cid)
        except (RuntimeError, TimeoutError) as exc:
            log(f"  [red]Cluster for {email} did not reach RUNNING: {exc}[/red]")

    # Phase 3: install libraries on each
    print_header("Installing Libraries")
    for email, cid in cluster_ids:
        log(f"  {email} ({cid})...")
        try:
            ensure_libraries_installed(client, cid, config.library)
        except Exception as exc:
            log(f"  [red]Library install failed for {email}: {exc}[/red]")

    log()
    log("[green]add-users complete.[/green]")


# ---------------------------------------------------------------------------
# remove-users orchestration
# ---------------------------------------------------------------------------

def _run_remove_users(csv_path: Path, *, keep_clusters: bool) -> None:
    """Parse CSV, remove from group, delete per-user clusters."""
    config = Config.load()
    client = config.prepare()
    acct = get_account_client()

    emails = parse_csv(csv_path)
    log(f"Read {len(emails)} unique email(s) from {csv_path}")

    print_header("Removing Users")

    grp = require_group(client, WORKSHOP_GROUP)
    group_id: str = grp.id  # type: ignore[assignment]
    existing_members = get_group_member_ids(acct, group_id)

    removed = 0
    not_found = 0
    not_member = 0
    to_remove: list[str] = []

    for email in emails:
        user = find_workspace_user(client, email)
        if user is None or user.id is None:
            log(f"  [yellow]Not found in workspace: {email}[/yellow]")
            not_found += 1
            continue

        if user.id not in existing_members:
            not_member += 1
            log(f"  {email} — not a member")
        else:
            to_remove.append(user.id)

    if to_remove:
        remove_members_from_group(acct, group_id, to_remove)
        removed = len(to_remove)

    log()
    log(f"  Removed from group: {removed}")
    log(f"  Not a member: {not_member}")
    if not_found:
        log(f"  [yellow]Not found in workspace: {not_found}[/yellow]")

    # --- Delete per-user clusters -----------------------------------------
    if keep_clusters:
        log()
        log("[dim]Skipping cluster deletion (--keep-clusters).[/dim]")
        return

    print_header("Deleting Per-User Clusters")

    # Build a set of expected cluster names from the CSV
    expected_names = {cluster_name_for_user(e) for e in emails}

    user_clusters = find_user_clusters(client)
    deleted = 0
    for uc in user_clusters:
        if uc.cluster_name in expected_names:
            try:
                delete_cluster(client, uc.cluster_id)
                deleted += 1
            except Exception as exc:
                log(f"  [red]Failed to delete {uc.cluster_name}: {exc}[/red]")

    log()
    log(f"  Deleted {deleted} cluster(s).")
    log()
    log("[green]remove-users complete.[/green]")


# ---------------------------------------------------------------------------
# list-users orchestration
# ---------------------------------------------------------------------------

def _run_list_users() -> None:
    """List group members with email, display name, cluster name, cluster state."""
    config = Config.load()
    client = config.prepare()
    acct = get_account_client()

    grp = require_group(client, WORKSHOP_GROUP)
    group_id: str = grp.id  # type: ignore[assignment]

    member_ids = get_group_member_ids(acct, group_id)

    if not member_ids:
        log(f"Group '{WORKSHOP_GROUP}' has no members.")
        return

    # Build cluster lookup: cluster_name -> UserClusterInfo
    user_clusters = find_user_clusters(client)
    cluster_map = {uc.cluster_name: uc for uc in user_clusters}

    rows: list[tuple[str, str, str, str]] = []
    for uid in member_ids:
        try:
            user = client.users.get(id=uid)
            email = user.user_name or "(no email)"
            display = user.display_name or ""
        except Exception:
            email = f"(id={uid})"
            display = "(could not fetch)"

        cname = cluster_name_for_user(email) if "@" in email else ""
        uc = cluster_map.get(cname)
        cstate = str(uc.state.value) if uc else "(none)"

        rows.append((email, display, cname, cstate))

    rows.sort(key=lambda r: r[0].lower())

    table = Table(title=f"Members of '{WORKSHOP_GROUP}' ({len(rows)})")
    table.add_column("Email", style="bold")
    table.add_column("Display Name")
    table.add_column("Cluster")
    table.add_column("State")
    for email, name, cname, cstate in rows:
        table.add_row(email, name, cname, cstate)

    log()
    log(table)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _print_config_summary(config: Config) -> None:
    """Print configuration overview before running tracks."""
    print_header("Databricks Environment Setup")

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
    log("Next: run 'databricks-setup add-users -f users.csv' to create per-user clusters.")


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
    log("[yellow]Per-user clusters are NOT affected — use 'remove-users' for that.[/yellow]")


if __name__ == "__main__":
    app()
