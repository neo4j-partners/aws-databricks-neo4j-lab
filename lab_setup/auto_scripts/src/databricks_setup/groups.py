"""Databricks group lookup and membership management.

Uses AccountClient for group membership (account-level groups cannot be
modified via the workspace API) and WorkspaceClient for group lookup.
"""

from __future__ import annotations

import os

from databricks.sdk import AccountClient, WorkspaceClient
from databricks.sdk.service.iam import (
    Group,
    Patch,
    PatchOp,
    PatchSchema,
)

from .log import log

# Account-level group name — must be created manually in the Databricks
# Account Admin console before running Track C.
WORKSHOP_GROUP = "aircraft_workshop_group"

_BATCH_SIZE = 50


def find_group(client: WorkspaceClient, group_name: str) -> Group | None:
    """Find a workspace group by display name."""
    results = list(client.groups.list(filter=f'displayName eq "{group_name}"'))
    if results:
        return results[0]
    return None


def require_group(client: WorkspaceClient, group_name: str) -> Group:
    """Look up a group and raise if it does not exist."""
    group = find_group(client, group_name)
    if group is None or group.id is None:
        raise RuntimeError(
            f"Group '{group_name}' not found in this workspace. "
            "Create it at https://accounts.cloud.databricks.com > "
            "User management > Groups, then add it to the workspace."
        )
    return group


def get_account_client() -> AccountClient:
    """Create an AccountClient for account-level group management.

    Requires ``DATABRICKS_ACCOUNT_ID`` in the environment.
    """
    account_id = os.getenv("DATABRICKS_ACCOUNT_ID")
    if not account_id:
        raise RuntimeError("DATABRICKS_ACCOUNT_ID not set in environment")
    return AccountClient(
        host="https://accounts.cloud.databricks.com",
        account_id=account_id,
    )


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
        log(f"  Added batch of {len(batch)} member(s) to group.")


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
