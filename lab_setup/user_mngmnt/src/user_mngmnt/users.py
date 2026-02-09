"""CSV parsing and workspace user lookup."""

from __future__ import annotations

import csv
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import User
from rich.console import Console

console = Console()


def parse_csv(path: Path) -> list[str]:
    """Read emails from a CSV file and return deduplicated list.

    The CSV must have an ``email`` column header.  Duplicate emails are
    silently removed.  Leading/trailing whitespace is stripped and emails
    are lowercased for consistent matching.

    Args:
        path: Path to the CSV file.

    Returns:
        Deduplicated list of email strings (preserves first-seen order).

    Raises:
        SystemExit: If the file is missing or lacks an ``email`` column.
    """
    if not path.exists():
        console.print(f"[red]Error: CSV file not found: {path}[/red]")
        raise SystemExit(1)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "email" not in [n.strip().lower() for n in reader.fieldnames]:
            console.print("[red]Error: CSV file must have an 'email' column header.[/red]")
            raise SystemExit(1)

        # Find the actual column name (case-insensitive)
        email_col = next(n for n in reader.fieldnames if n.strip().lower() == "email")

        seen: set[str] = set()
        emails: list[str] = []
        for row in reader:
            email = row[email_col].strip().lower()
            if email and email not in seen:
                seen.add(email)
                emails.append(email)

    return emails


def find_workspace_user(client: WorkspaceClient, email: str) -> User | None:
    """Look up a workspace user by email address.

    Uses the SCIM ``userName eq`` filter which matches Databricks user
    email (the primary identifier).

    Args:
        client: Databricks workspace client.
        email: Email address to search for.

    Returns:
        The User object if found, else None.
    """
    results = list(client.users.list(filter=f'userName eq "{email}"'))
    if results:
        return results[0]
    return None
