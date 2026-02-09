"""Workshop permissions lockdown.

Track C of the setup process:

1. Remove compute-creation entitlements from the built-in ``users`` group.
2. Verify that the ``aircraft_workshop_group`` account-level group exists.
3. Grant read-only Unity Catalog privileges on the lab catalog.
4. Grant ``CAN_ATTACH_TO`` on the workshop cluster.
5. Grant ``CAN_READ`` on the shared notebook folder.
"""

from __future__ import annotations

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.catalog import (
    Privilege,
    PermissionsChange,
    SecurableType,
)
from databricks.sdk.service.compute import (
    ClusterAccessControlRequest,
    ClusterPermissionLevel,
)
from databricks.sdk.service.iam import (
    AccessControlRequest,
    Group,
    Patch,
    PatchOp,
    PatchSchema,
    PermissionLevel,
)

from .cluster import find_cluster
from .config import ClusterConfig, NotebookConfig, VolumeConfig
from .log import log
from .notebooks import get_workspace_folder_id
from .utils import print_header

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Account-level group name — must be created manually in the Databricks
# Account Admin console before running Track C.
WORKSHOP_GROUP = "aircraft_workshop_group"

# Entitlements to strip from the built-in 'users' group.
_ENTITLEMENTS_TO_REMOVE = (
    "allow-cluster-create",
    "allow-instance-pool-create",
)

# Read-only privileges granted at the catalog level so they cascade to all
# current and future schemas, tables, and volumes.
_CATALOG_PRIVILEGES = (
    Privilege.USE_CATALOG,
    Privilege.USE_SCHEMA,
    Privilege.SELECT,
    Privilege.READ_VOLUME,
    Privilege.BROWSE,
)


# ---------------------------------------------------------------------------
# Group helpers
# ---------------------------------------------------------------------------

def _find_group_by_name(client: WorkspaceClient, display_name: str) -> Group | None:
    """Find a workspace group by display name.

    Args:
        client: Databricks workspace client.
        display_name: Exact group name to search for.

    Returns:
        The Group object if found, else None.
    """
    results = list(client.groups.list(filter=f'displayName eq "{display_name}"'))
    if results:
        return results[0]
    return None


def _get_entitlement_values(group: Group) -> set[str]:
    """Extract current entitlement values from a group.

    Args:
        group: A Group object (must include entitlements).

    Returns:
        Set of entitlement value strings.
    """
    if not group.entitlements:
        return set()
    return {e.value for e in group.entitlements if e.value}


# ---------------------------------------------------------------------------
# Step 1: Entitlement lockdown
# ---------------------------------------------------------------------------

def _remove_entitlement(
    client: WorkspaceClient,
    group_id: str,
    entitlement_value: str,
) -> None:
    """Remove a single entitlement from a group via SCIM PATCH.

    Removing an entitlement that is not currently set is a no-op
    and will not raise an error.

    Args:
        client: Databricks workspace client.
        group_id: The group ID to patch.
        entitlement_value: Entitlement to remove (e.g. "allow-cluster-create").
    """
    client.groups.patch(
        id=group_id,
        operations=[
            Patch(
                op=PatchOp.REMOVE,
                path=f'entitlements[value eq "{entitlement_value}"]',
            ),
        ],
        schemas=[PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
    )


def lockdown_entitlements(client: WorkspaceClient) -> bool:
    """Remove compute-creation entitlements from the built-in ``users`` group.

    Every workspace user is automatically a member of ``users``.  Removing
    ``allow-cluster-create`` blocks creation of clusters *and* SQL warehouses.
    Removing ``allow-instance-pool-create`` blocks pool creation.

    This operation is idempotent — removing an entitlement that is already
    absent does not raise an error.

    Args:
        client: Databricks workspace client.

    Returns:
        True on success, False on error.
    """
    log("Step 1: Locking down entitlements on 'users' group...")

    # --- Find the built-in 'users' group --------------------------------
    users_group = _find_group_by_name(client, "users")
    if users_group is None or users_group.id is None:
        log("[red]Error: Could not find the built-in 'users' group.[/red]")
        return False

    log(f"  Found group: users (id={users_group.id})")

    # --- Snapshot current entitlements -----------------------------------
    full_group = client.groups.get(id=users_group.id)
    before = _get_entitlement_values(full_group)

    if before:
        log(f"  Current entitlements: {', '.join(sorted(before))}")
    else:
        log("  Current entitlements: (none)")

    # --- Remove target entitlements --------------------------------------
    removed = []
    skipped = []

    for entitlement in _ENTITLEMENTS_TO_REMOVE:
        if entitlement in before:
            log(f"  Removing '{entitlement}'...")
            try:
                _remove_entitlement(client, users_group.id, entitlement)
                removed.append(entitlement)
                log("    Done.")
            except Exception as e:
                log(f"    [red]Failed to remove '{entitlement}': {e}[/red]")
                return False
        else:
            skipped.append(entitlement)
            log(f"  '{entitlement}' already absent — skipping.")

    # --- Verify ----------------------------------------------------------
    full_group = client.groups.get(id=users_group.id)
    after = _get_entitlement_values(full_group)

    remaining = {e for e in _ENTITLEMENTS_TO_REMOVE if e in after}
    if remaining:
        log(f"[red]Error: Entitlements still present after removal: {', '.join(sorted(remaining))}[/red]")
        return False

    if removed:
        log(f"  [green]Removed: {', '.join(removed)}[/green]")
    if skipped:
        log(f"  [dim]Already absent: {', '.join(skipped)}[/dim]")

    return True


# ---------------------------------------------------------------------------
# Step 2: Require account-level group
# ---------------------------------------------------------------------------

def require_workshop_group(client: WorkspaceClient, group_name: str) -> str | None:
    """Verify that the account-level workshop group exists in the workspace.

    This group must be created manually in the Databricks Account Admin
    console and then added to the workspace.  Unity Catalog grants only
    work with account-level groups — workspace-local groups are invisible
    to UC and will cause "Could not find principal" errors.

    Args:
        client: Databricks workspace client.
        group_name: Display name of the account-level group.

    Returns:
        The group ID on success, None if the group is not found.
    """
    log(f"Step 2: Verifying account-level group '{group_name}' exists...")

    existing = _find_group_by_name(client, group_name)
    if existing and existing.id:
        log(f"  Found group (id={existing.id}).")
        return existing.id

    log(f"  [red]Error: Group '{group_name}' not found in this workspace.[/red]")
    log(f"  [red]This group must be created at the account level:[/red]")
    log(f"  [red]  1. Go to https://accounts.cloud.databricks.com > User management > Groups[/red]")
    log(f"  [red]  2. Create a group named '{group_name}'[/red]")
    log(f"  [red]  3. In the workspace, go to Settings > Identity and access > Groups[/red]")
    log(f"  [red]  4. Click 'Add group' and add '{group_name}' from the account[/red]")
    return None


# ---------------------------------------------------------------------------
# Step 3: Unity Catalog grants
# ---------------------------------------------------------------------------

def grant_catalog_read_only(
    client: WorkspaceClient,
    catalog_name: str,
    group_name: str,
) -> bool:
    """Grant read-only Unity Catalog privileges on a catalog.

    Grants are applied at the catalog level so they cascade automatically
    to all schemas, tables, and volumes within it.

    The ``w.grants.update()`` call is additive — it will not remove
    existing grants for other principals.  Re-running with the same
    privileges is a no-op.

    Args:
        client: Databricks workspace client.
        catalog_name: Name of the catalog to grant on.
        group_name: Group to receive the privileges.

    Returns:
        True on success, False on error.
    """
    log(f"Step 3: Granting read-only catalog access to '{group_name}'...")

    privilege_names = [p.value for p in _CATALOG_PRIVILEGES]
    log(f"  Privileges: {', '.join(privilege_names)}")
    log(f"  Catalog:    {catalog_name}")

    try:
        client.grants.update(
            securable_type=SecurableType.CATALOG.value,
            full_name=catalog_name,
            changes=[
                PermissionsChange(
                    add=list(_CATALOG_PRIVILEGES),
                    principal=group_name,
                ),
            ],
        )
        log("  Done.")
    except Exception as e:
        log(f"  [red]Failed to grant catalog privileges: {e}[/red]")
        return False

    # --- Verify ---
    try:
        effective = client.grants.get(
            securable_type=SecurableType.CATALOG.value,
            full_name=catalog_name,
        )
        granted: set[str] = set()
        for pa in effective.privilege_assignments or []:
            if pa.principal == group_name:
                granted = {p.value for p in (pa.privileges or [])}
                break

        missing = {p.value for p in _CATALOG_PRIVILEGES} - granted
        if missing:
            log(f"  [yellow]Warning: Expected privileges not found after grant: {', '.join(sorted(missing))}[/yellow]")
        else:
            log(f"  [green]Verified: all {len(_CATALOG_PRIVILEGES)} privileges present.[/green]")
    except Exception as e:
        log(f"  [yellow]Warning: Could not verify grants: {e}[/yellow]")

    return True


# ---------------------------------------------------------------------------
# Step 4: Cluster permissions
# ---------------------------------------------------------------------------

def grant_cluster_attach(
    client: WorkspaceClient,
    cluster_id: str,
    group_name: str,
) -> bool:
    """Grant CAN_ATTACH_TO on a cluster to a group.

    Uses ``update_permissions`` (PATCH) which merges with existing ACLs.
    The admin's ``CAN_MANAGE`` and other principals are left untouched.
    Re-running with the same permission is a no-op.

    Args:
        client: Databricks workspace client.
        cluster_id: ID of the cluster.
        group_name: Group to receive the permission.

    Returns:
        True on success, False on error.
    """
    log(f"Step 4: Granting CAN_ATTACH_TO on cluster to '{group_name}'...")
    log(f"  Cluster: {cluster_id}")

    try:
        client.clusters.update_permissions(
            cluster_id=cluster_id,
            access_control_list=[
                ClusterAccessControlRequest(
                    group_name=group_name,
                    permission_level=ClusterPermissionLevel.CAN_ATTACH_TO,
                ),
            ],
        )
        log("  Done.")
    except Exception as e:
        log(f"  [red]Failed to set cluster permissions: {e}[/red]")
        return False

    # --- Verify ---
    try:
        perms = client.clusters.get_permissions(cluster_id=cluster_id)
        found = False
        for acl in perms.access_control_list or []:
            if acl.group_name == group_name:
                for p in acl.all_permissions or []:
                    if p.permission_level == ClusterPermissionLevel.CAN_ATTACH_TO:
                        found = True
                        break

        if found:
            log(f"  [green]Verified: CAN_ATTACH_TO present for '{group_name}'.[/green]")
        else:
            log(f"  [yellow]Warning: CAN_ATTACH_TO not found in cluster ACL after grant.[/yellow]")
    except Exception as e:
        log(f"  [yellow]Warning: Could not verify cluster permissions: {e}[/yellow]")

    return True


# ---------------------------------------------------------------------------
# Step 5: Workspace folder permissions
# ---------------------------------------------------------------------------

def grant_workspace_folder_read(
    client: WorkspaceClient,
    workspace_folder: str,
    group_name: str,
) -> bool:
    """Grant CAN_READ on a workspace folder to a group.

    Uses ``update_permissions`` (PATCH) which merges with existing ACLs.

    Args:
        client: Databricks workspace client.
        workspace_folder: Absolute workspace path (e.g. "/Shared/my-folder").
        group_name: Group to receive the permission.

    Returns:
        True on success, False on error.
    """
    log(f"Step 5: Granting CAN_READ on workspace folder to '{group_name}'...")
    log(f"  Folder: {workspace_folder}")

    folder_id = get_workspace_folder_id(client, workspace_folder)
    if folder_id is None:
        log(f"  [yellow]Workspace folder not found — skipping.[/yellow]")
        return True  # Non-fatal: notebooks may not have been uploaded

    try:
        client.permissions.update(
            request_object_type="directories",
            request_object_id=str(folder_id),
            access_control_list=[
                AccessControlRequest(
                    group_name=group_name,
                    permission_level=PermissionLevel.CAN_READ,
                ),
            ],
        )
        log("  Done.")
    except Exception as e:
        log(f"  [red]Failed to set folder permissions: {e}[/red]")
        return False

    # --- Verify ---
    try:
        perms = client.permissions.get(
            request_object_type="directories",
            request_object_id=str(folder_id),
        )
        found = False
        for acl in perms.access_control_list or []:
            if acl.group_name == group_name:
                for p in acl.all_permissions or []:
                    if p.permission_level == PermissionLevel.CAN_READ:
                        found = True
                        break

        if found:
            log(f"  [green]Verified: CAN_READ present for '{group_name}'.[/green]")
        else:
            log(f"  [yellow]Warning: CAN_READ not found in folder ACL after grant.[/yellow]")
    except Exception as e:
        log(f"  [yellow]Warning: Could not verify folder permissions: {e}[/yellow]")

    return True


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_permissions_lockdown(
    client: WorkspaceClient,
    cluster_config: ClusterConfig,
    volume_config: VolumeConfig,
    notebook_config: NotebookConfig | None = None,
) -> bool:
    """Run all Track C steps: lockdown, group, grants, cluster ACL, folder ACL.

    Args:
        client: Databricks workspace client.
        cluster_config: Cluster configuration (name loaded from .env).
        volume_config: Volume configuration identifying the catalog to lock down.
        notebook_config: Notebook configuration (for workspace folder permissions).

    Returns:
        True if all steps succeeded, False otherwise.
    """
    print_header("Track C: Permissions Lockdown")

    # Step 1: Entitlement lockdown
    if not lockdown_entitlements(client):
        return False

    log()

    # Step 2: Require account-level group
    group_id = require_workshop_group(client, WORKSHOP_GROUP)
    if group_id is None:
        return False

    log()

    # Step 3: UC grants
    if not grant_catalog_read_only(client, volume_config.catalog, WORKSHOP_GROUP):
        return False

    log()

    # Step 4: Cluster permissions
    info = find_cluster(client, cluster_config.name)
    if info is None:
        log(f"[red]Error: Cluster '{cluster_config.name}' not found.[/red]")
        return False

    if not grant_cluster_attach(client, info.cluster_id, WORKSHOP_GROUP):
        return False

    log()

    # Step 5: Workspace folder permissions
    if notebook_config is not None:
        if not grant_workspace_folder_read(client, notebook_config.workspace_folder, WORKSHOP_GROUP):
            return False
        log()

    log("[green]Permissions lockdown complete.[/green]")
    return True


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_permissions(client: WorkspaceClient, volume_config: VolumeConfig) -> None:
    """Revoke catalog grants for the workshop group.

    Does NOT delete the account-level group — it persists across
    setup/cleanup cycles.  Does NOT restore entitlements — that is a
    deliberate admin action.  Each step is idempotent.

    Args:
        client: Databricks workspace client.
        volume_config: Volume configuration identifying the catalog to clean up.
    """
    print_header("Cleaning Up Permissions")

    # Revoke catalog grants (before the catalog itself is deleted)
    log(f"  Revoking catalog grants for '{WORKSHOP_GROUP}'...")
    try:
        client.grants.update(
            securable_type=SecurableType.CATALOG.value,
            full_name=volume_config.catalog,
            changes=[
                PermissionsChange(
                    remove=list(_CATALOG_PRIVILEGES),
                    principal=WORKSHOP_GROUP,
                ),
            ],
        )
        log("    Done.")
    except NotFound:
        log("    Catalog already deleted — skipping.")
    except Exception as e:
        log(f"    [yellow]Skipped: {e}[/yellow]")

    # Note: the account-level group is NOT deleted — it is managed in the
    # Databricks Account Admin console and should persist across runs.
    log(f"  [dim]Account-level group '{WORKSHOP_GROUP}' is preserved (not deleted).[/dim]")

    # Note: cluster ACL cleanup is not strictly needed — the cluster is
    # typically deleted separately, and re-running setup re-applies the ACL.

    log()
    log("[yellow]Note: Entitlements on 'users' group were NOT restored.[/yellow]")
    log("[yellow]To re-enable compute creation, manually add 'allow-cluster-create'[/yellow]")
    log("[yellow]to the 'users' group in Settings > Identity and access > Groups.[/yellow]")
