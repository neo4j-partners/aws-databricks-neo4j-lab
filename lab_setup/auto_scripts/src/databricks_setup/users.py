"""CSV parsing, workspace user lookup, and per-user naming helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import User

from .log import log


def parse_csv(path: Path) -> list[str]:
    """Read emails from a CSV file and return a deduplicated list.

    The CSV must have an ``email`` column header.  Duplicate emails are
    silently removed.  Leading/trailing whitespace is stripped and emails
    are lowercased for consistent matching.

    Raises:
        RuntimeError: If the file is missing or lacks an ``email`` column.
    """
    if not path.exists():
        raise RuntimeError(f"CSV file not found: {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "email" not in [
            n.strip().lower() for n in reader.fieldnames
        ]:
            raise RuntimeError("CSV file must have an 'email' column header.")

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


def preview_csv(path: Path, max_rows: int = 2) -> list[dict[str, str]]:
    """Return the first *max_rows* rows from the CSV as dicts for preview."""
    if not path.exists():
        raise RuntimeError(f"CSV file not found: {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append({k: v.strip() for k, v in row.items()})
    return rows


def find_workspace_user(client: WorkspaceClient, email: str) -> User | None:
    """Look up a workspace user by email address."""
    results = list(client.users.list(filter=f'userName eq "{email}"'))
    if results:
        return results[0]
    return None


def create_workspace_user(client: WorkspaceClient, email: str) -> User:
    """Create (invite) a user in the workspace via SCIM."""
    user = client.users.create(user_name=email)
    log(f"  Created workspace user: {email}")
    return user


def email_prefix(email: str) -> str:
    """Extract the part before ``@`` and replace dots with hyphens.

    >>> email_prefix("retroryan@gmail.com")
    'retroryan'
    >>> email_prefix("jane.doe@company.com")
    'jane-doe'
    """
    local = email.split("@")[0]
    return local.replace(".", "-")


def cluster_name_for_user(email: str) -> str:
    """Return the per-user cluster name: ``lab-<prefix>``.

    >>> cluster_name_for_user("retroryan@gmail.com")
    'lab-retroryan'
    """
    return f"lab-{email_prefix(email)}"
