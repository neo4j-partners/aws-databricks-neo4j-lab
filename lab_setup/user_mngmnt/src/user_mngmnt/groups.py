"""Databricks group lookup and membership management."""

from __future__ import annotations

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import (
    ComplexValue,
    Group,
    Patch,
    PatchOp,
    PatchSchema,
)
from rich.console import Console

console = Console()

DEFAULT_GROUP = "aircraft_workshop_group"
_BATCH_SIZE = 50


def find_group(client: WorkspaceClient, group_name: str) -> Group | None:
    """Find a workspace group by display name.

    Args:
        client: Databricks workspace client.
        group_name: Exact display name to match.

    Returns:
        The Group object if found, else None.
    """
    results = list(client.groups.list(filter=f'displayName eq "{group_name}"'))
    if results:
        return results[0]
    return None


def require_group(client: WorkspaceClient, group_name: str) -> Group:
    """Look up a group and exit if it does not exist.

    The group must be created at the account level and added to the
    workspace before using any user-mngmnt commands.

    Args:
        client: Databricks workspace client.
        group_name: Display name of the group.

    Returns:
        The Group object.

    Raises:
        SystemExit: If the group does not exist.
    """
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


def get_group_member_ids(client: WorkspaceClient, group_id: str) -> set[str]:
    """Return the set of user IDs currently in a group.

    Args:
        client: Databricks workspace client.
        group_id: ID of the group.

    Returns:
        Set of member user ID strings.
    """
    group = client.groups.get(id=group_id)
    if not group.members:
        return set()
    return {m.value for m in group.members if m.value}


def add_members_to_group(
    client: WorkspaceClient,
    group_id: str,
    user_ids: list[str],
) -> None:
    """Add users to a group in batches.

    Uses SCIM PATCH with ``PatchOp.ADD``.  Adding a user who is already
    a member is a no-op on the server side.

    Args:
        client: Databricks workspace client.
        group_id: ID of the group to modify.
        user_ids: User IDs to add.
    """
    for i in range(0, len(user_ids), _BATCH_SIZE):
        batch = user_ids[i : i + _BATCH_SIZE]
        client.groups.patch(
            id=group_id,
            operations=[
                Patch(
                    op=PatchOp.ADD,
                    path="members",
                    value=[
                        ComplexValue(value=uid) for uid in batch
                    ],
                ),
            ],
            schemas=[PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        )


def remove_members_from_group(
    client: WorkspaceClient,
    group_id: str,
    user_ids: list[str],
) -> None:
    """Remove users from a group one at a time.

    SCIM PATCH REMOVE with a path filter targets individual members.

    Args:
        client: Databricks workspace client.
        group_id: ID of the group to modify.
        user_ids: User IDs to remove.
    """
    for uid in user_ids:
        client.groups.patch(
            id=group_id,
            operations=[
                Patch(
                    op=PatchOp.REMOVE,
                    path=f'members[value eq "{uid}"]',
                ),
            ],
            schemas=[PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        )
