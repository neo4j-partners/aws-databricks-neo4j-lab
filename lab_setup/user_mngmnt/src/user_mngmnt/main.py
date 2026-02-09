"""CLI entry point for workshop user management.

Provides add, remove, and list commands for managing membership of the
``aircraft_workshop_group`` in a Databricks workspace.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .groups import (
    DEFAULT_GROUP,
    add_members_to_group,
    get_group_member_ids,
    remove_members_from_group,
    require_group,
)
from .users import find_workspace_user, parse_csv

app = typer.Typer(
    name="user-mngmnt",
    help="Manage workshop group membership in Databricks.",
    add_completion=False,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env() -> None:
    """Load the shared lab_setup/.env file."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _get_client(profile: str | None) -> WorkspaceClient:
    """Create a WorkspaceClient with optional profile."""
    _load_env()
    resolved = profile or os.getenv("DATABRICKS_PROFILE")
    if resolved:
        return WorkspaceClient(profile=resolved)
    return WorkspaceClient()


def _resolve_group(group_flag: str) -> str:
    """Resolve group name from CLI flag or GROUP_NAME env var."""
    if group_flag != DEFAULT_GROUP:
        return group_flag
    return os.getenv("GROUP_NAME", DEFAULT_GROUP)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

@app.command()
def add(
    file: Path = typer.Option(
        Path("users.csv"),
        "--file", "-f",
        help="Path to CSV file with an 'email' column.",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile", "-p",
        help="Databricks CLI profile name.",
    ),
    group: str = typer.Option(
        DEFAULT_GROUP,
        "--group", "-g",
        help="Target group name (or set GROUP_NAME env var).",
    ),
) -> None:
    """Add users from a CSV file to the workshop group."""
    group_name = _resolve_group(group)
    client = _get_client(profile)
    emails = parse_csv(file)
    console.print(f"Read {len(emails)} unique email(s) from {file}")

    grp = require_group(client, group_name)
    group_id: str = grp.id  # type: ignore[assignment]  # require_group guarantees non-None
    existing_members = get_group_member_ids(client, group_id)

    added = 0
    already = 0
    not_found = 0
    to_add: list[str] = []

    for email in emails:
        user = find_workspace_user(client, email)
        if user is None or user.id is None:
            console.print(f"  [yellow]Not found in workspace: {email}[/yellow]")
            not_found += 1
            continue

        if user.id in existing_members:
            already += 1
            continue

        to_add.append(user.id)

    if to_add:
        try:
            add_members_to_group(client, group_id, to_add)
            added = len(to_add)
        except Exception as exc:
            console.print(f"[red]Error adding members: {exc}[/red]")

    _print_summary("Add Summary", [
        ("Added", added, "green"),
        ("Already member", already, "dim"),
        ("Not found in workspace", not_found, "yellow"),
        ("Total in CSV", len(emails), "bold"),
    ])


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

@app.command()
def remove(
    file: Path = typer.Option(
        Path("users.csv"),
        "--file", "-f",
        help="Path to CSV file with an 'email' column.",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile", "-p",
        help="Databricks CLI profile name.",
    ),
    group: str = typer.Option(
        DEFAULT_GROUP,
        "--group", "-g",
        help="Target group name (or set GROUP_NAME env var).",
    ),
) -> None:
    """Remove users listed in a CSV file from the workshop group."""
    group_name = _resolve_group(group)
    client = _get_client(profile)
    emails = parse_csv(file)
    console.print(f"Read {len(emails)} unique email(s) from {file}")

    grp = require_group(client, group_name)
    group_id: str = grp.id  # type: ignore[assignment]  # require_group guarantees non-None
    existing_members = get_group_member_ids(client, group_id)

    removed = 0
    not_found = 0
    not_member = 0
    to_remove: list[str] = []

    for email in emails:
        user = find_workspace_user(client, email)
        if user is None or user.id is None:
            console.print(f"  [yellow]Not found in workspace: {email}[/yellow]")
            not_found += 1
            continue

        if user.id not in existing_members:
            not_member += 1
            continue

        to_remove.append(user.id)

    if to_remove:
        try:
            remove_members_from_group(client, group_id, to_remove)
            removed = len(to_remove)
        except Exception as exc:
            console.print(f"[red]Error removing members: {exc}[/red]")

    _print_summary("Remove Summary", [
        ("Removed", removed, "green"),
        ("Not a member", not_member, "dim"),
        ("Not found in workspace", not_found, "yellow"),
        ("Total in CSV", len(emails), "bold"),
    ])


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@app.command(name="list")
def list_members(
    profile: Optional[str] = typer.Option(
        None,
        "--profile", "-p",
        help="Databricks CLI profile name.",
    ),
    group: str = typer.Option(
        DEFAULT_GROUP,
        "--group", "-g",
        help="Target group name (or set GROUP_NAME env var).",
    ),
) -> None:
    """List current members of the workshop group."""
    group_name = _resolve_group(group)
    client = _get_client(profile)
    grp = require_group(client, group_name)
    group_id: str = grp.id  # type: ignore[assignment]  # require_group guarantees non-None

    member_ids = get_group_member_ids(client, group_id)

    if not member_ids:
        console.print(f"Group '{group_name}' has no members.")
        return

    # Fetch user details and sort by email for stable, readable output
    rows: list[tuple[str, str]] = []
    for uid in member_ids:
        try:
            user = client.users.get(id=uid)
            rows.append((
                user.user_name or "(no email)",
                user.display_name or "",
            ))
        except Exception:
            rows.append((f"(id={uid})", "(could not fetch)"))

    rows.sort(key=lambda r: r[0].lower())

    table = Table(title=f"Members of '{group_name}' ({len(rows)})")
    table.add_column("Email", style="bold")
    table.add_column("Display Name")
    for email, name in rows:
        table.add_row(email, name)

    console.print()
    console.print(table)


# ---------------------------------------------------------------------------
# Shared output
# ---------------------------------------------------------------------------

def _print_summary(title: str, rows: list[tuple[str, int, str]]) -> None:
    """Print a Rich summary table with label/count/style rows."""
    table = Table(title=title)
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    for label, count, style in rows:
        table.add_row(label, str(count), style=style)
    console.print()
    console.print(table)


if __name__ == "__main__":
    app()
