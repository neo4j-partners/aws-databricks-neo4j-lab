"""Utility functions and helpers for Databricks setup."""

import time
from collections.abc import Callable
from typing import TypeVar

from databricks.sdk import WorkspaceClient
from rich.console import Console

console = Console()

T = TypeVar("T")


def get_workspace_client(profile: str | None = None) -> WorkspaceClient:
    """Create a Databricks WorkspaceClient with optional profile."""
    if profile:
        return WorkspaceClient(profile=profile)
    return WorkspaceClient()


def get_current_user(client: WorkspaceClient) -> str:
    """Get the current user's email from the workspace."""
    me = client.current_user.me()
    if not me.user_name:
        raise RuntimeError("Could not determine current user email")
    return me.user_name


def poll_until(
    check_fn: Callable[[], tuple[bool, T]],
    timeout_seconds: int = 600,
    interval_seconds: int = 15,
    description: str = "operation",
) -> T:
    """Poll until a condition is met or timeout occurs.

    Args:
        check_fn: Function that returns (is_done, result). Called repeatedly.
        timeout_seconds: Maximum time to wait.
        interval_seconds: Time between checks.
        description: Description for error messages.

    Returns:
        The result from check_fn when done.

    Raises:
        TimeoutError: If timeout is reached before condition is met.
    """
    elapsed = 0
    while elapsed < timeout_seconds:
        done, result = check_fn()
        if done:
            return result
        time.sleep(interval_seconds)
        elapsed += interval_seconds
        console.print(f"  Waiting... ({elapsed}s elapsed)")

    raise TimeoutError(f"Timed out waiting for {description} ({timeout_seconds}s)")


def print_header(title: str) -> None:
    """Print a formatted header."""
    console.print()
    console.print("=" * 42, style="bold blue")
    console.print(title, style="bold blue")
    console.print("=" * 42, style="bold blue")


