"""CLI entry point for workshop user management.

Provides add, remove, and list commands for managing membership of the
``aircraft_workshop_group`` in a Databricks workspace.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .groups import (
    add_members_to_group,
    get_group_member_ids,
    remove_members_from_group,
    require_group,
)
from .users import create_workspace_user, find_workspace_user, parse_csv

app = typer.Typer(
    name="user-mngmnt",
    help="Manage workshop group membership in Databricks.",
    add_completion=False,
)

console = Console()

GROUP_NAME = "aircraft_workshop_group"

# Resolve paths relative to the package: …/user_mngmnt/src/user_mngmnt/main.py
# -> lab_setup/
_LAB_SETUP_DIR = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_CSV = _LAB_SETUP_DIR / "users.csv"
_ENV_FILE = _LAB_SETUP_DIR / ".env"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> WorkspaceClient:
    """Create a WorkspaceClient using the profile from lab_setup/.env."""
    if not _ENV_FILE.exists():
        console.print(f"[red]Error: .env file not found at {_ENV_FILE}[/red]")
        console.print("[red]Copy .env.example to .env and fill in DATABRICKS_PROFILE.[/red]")
        raise SystemExit(1)

    load_dotenv(_ENV_FILE)
    profile = os.getenv("DATABRICKS_PROFILE")
    if profile:
        return WorkspaceClient(profile=profile)
    return WorkspaceClient()


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

@app.command()
def add(
    file: Path = typer.Option(
        _DEFAULT_CSV,
        "--file", "-f",
        help="Path to CSV file with an 'email' column.",
    ),
) -> None:
    """Add users from a CSV file to the workshop group."""
    client = _get_client()
    emails = parse_csv(file)
    console.print(f"Read {len(emails)} unique email(s) from {file}")

    grp = require_group(client, GROUP_NAME)
    group_id: str = grp.id  # type: ignore[assignment]
    existing_members = get_group_member_ids(client, group_id)

    added = 0
    already = 0
    created = 0
    failed_create = 0
    to_add: list[str] = []

    for email in emails:
        user = find_workspace_user(client, email)
        if user is None or user.id is None:
            # User doesn't exist — create them
            try:
                user = create_workspace_user(client, email)
                console.print(f"  [cyan]Created workspace user: {email}[/cyan]")
                created += 1
            except Exception as exc:
                console.print(f"  [red]Failed to create user {email}: {exc}[/red]")
                failed_create += 1
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
        ("Added to group", added, "green"),
        ("Created in workspace", created, "cyan"),
        ("Already member", already, "dim"),
        ("Failed to create", failed_create, "red"),
        ("Total in CSV", len(emails), "bold"),
    ])


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

@app.command()
def remove(
    file: Path = typer.Option(
        _DEFAULT_CSV,
        "--file", "-f",
        help="Path to CSV file with an 'email' column.",
    ),
) -> None:
    """Remove users listed in a CSV file from the workshop group."""
    client = _get_client()
    emails = parse_csv(file)
    console.print(f"Read {len(emails)} unique email(s) from {file}")

    grp = require_group(client, GROUP_NAME)
    group_id: str = grp.id  # type: ignore[assignment]
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
def list_members() -> None:
    """List current members of the workshop group."""
    client = _get_client()
    grp = require_group(client, GROUP_NAME)
    group_id: str = grp.id  # type: ignore[assignment]

    member_ids = get_group_member_ids(client, group_id)

    if not member_ids:
        console.print(f"Group '{GROUP_NAME}' has no members.")
        return

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

    table = Table(title=f"Members of '{GROUP_NAME}' ({len(rows)})")
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
