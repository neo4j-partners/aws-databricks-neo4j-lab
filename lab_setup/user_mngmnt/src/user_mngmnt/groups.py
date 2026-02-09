"""Databricks group lookup and membership management.

Uses AccountClient for group membership (account-level groups cannot be
modified via the workspace API) and WorkspaceClient for group lookup.
"""

from __future__ import annotations

from databricks.sdk import AccountClient, WorkspaceClient
from databricks.sdk.service.iam import (
    Group,
    Patch,
    PatchOp,
    PatchSchema,
)
from rich.console import Console

console = Console()

_BATCH_SIZE = 50


def find_group(client: WorkspaceClient, group_name: str) -> Group | None:
    """Find a workspace group by display name."""
    results = list(client.groups.list(filter=f'displayName eq "{group_name}"'))
    if results:
        return results[0]
    return None


def require_group(client: WorkspaceClient, group_name: str) -> Group:
    """Look up a group and exit if it does not exist."""
    group = find_group(client, group_name)
    if group is None or group.id is None:
        console.print(
            f"[red]Error: Group '{group_name}' not found in this workspace.[/red]"
        )
        console.print(
            "[red]Create it at https://accounts.cloud.databricks.com > "
            "User management > Groups, then add it to the workspace.[/red]"
        )
        raise SystemExit(1)
    return group


def get_group_member_ids(acct: AccountClient, group_id: str) -> set[str]:
    """Return the set of user IDs currently in an account-level group."""
    group = acct.groups.get(id=group_id)
    if not group.members:
        return set()
    return {m.value for m in group.members if m.value}


def add_members_to_group(
    acct: AccountClient,
    group_id: str,
    user_ids: list[str],
) -> None:
    """Add users to an account-level group in batches."""
    for i in range(0, len(user_ids), _BATCH_SIZE):
        batch = user_ids[i : i + _BATCH_SIZE]
        acct.groups.patch(
            id=group_id,
            operations=[
                Patch(
                    op=PatchOp.ADD,
                    path="members",
                    value=[{"value": uid} for uid in batch],
                ),
            ],
            schemas=[PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        )


def remove_members_from_group(
    acct: AccountClient,
    group_id: str,
    user_ids: list[str],
) -> None:
    """Remove users from an account-level group one at a time."""
    for uid in user_ids:
        acct.groups.patch(
            id=group_id,
            operations=[
                Patch(
                    op=PatchOp.REMOVE,
                    path=f'members[value eq "{uid}"]',
                ),
            ],
            schemas=[PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        )
