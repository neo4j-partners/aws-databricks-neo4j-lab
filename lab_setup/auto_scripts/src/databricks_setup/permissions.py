"""Workshop permissions lockdown.

Track C of the setup process:

1.  Remove compute-creation entitlements from the built-in ``users`` group.
1b. Disable the Personal Compute cluster policy (node_type_id forbidden).
2.  Verify that the ``aircraft_workshop_group`` account-level group exists.
3.  Grant read-only Unity Catalog privileges on the lab catalog.
4.  Grant ``CAN_READ`` on the shared notebook folder.
5.  Grant ``CAN_USE`` on the SQL warehouse (required for Genie + SQL).
6.  Grant ``USE_CONNECTION`` on the Neo4j MCP connection (for AgentBricks).
7.  Verify Foundation Model API endpoints are accessible.
8.  Verify AgentBricks prerequisites (preview flags, budget policy).

Note: Cluster CAN_ATTACH_TO is no longer needed — per-user SINGLE_USER
clusters give the assigned user implicit access.

Limitation — Lakebase and serverless compute:
    Lakebase (managed serverless Postgres) and other serverless resources
    cannot be restricted at the user or group level.  All workspace users
    automatically inherit ``CAN CREATE`` on database instances, and this
    permission cannot be removed via ACLs, entitlements, or cluster policies.
    The only way to block Lakebase creation is to disable serverless compute
    at the workspace level (Account Console > Settings > Feature Enablement),
    which also disables serverless SQL warehouses, notebooks, and DLT.
"""

from __future__ import annotations

import json

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.catalog import (
    Privilege,
    PermissionsChange,
    SecurableType,
)
from databricks.sdk.service.compute import (
    ClusterPolicyAccessControlRequest,
    ClusterPolicyPermissionLevel,
    Policy,
)
from databricks.sdk.service.iam import (
    AccessControlRequest,
    Group,
    Patch,
    PatchOp,
    PatchSchema,
    PermissionLevel,
)

from .config import NotebookConfig, VolumeConfig, WarehouseConfig
from .groups import WORKSHOP_GROUP, find_group
from .log import log
from .notebooks import get_workspace_folder_id
from .utils import print_header
from .warehouse import find_warehouse

# Policy family ID for the built-in Personal Compute cluster policy.
_PERSONAL_COMPUTE_POLICY_FAMILY = "personal-vm"

# Override applied to the Personal Compute policy to make it unusable.
# Setting node_type_id to "forbidden" prevents any node type from being
# selected, so no cluster can be created with this policy.
_PERSONAL_COMPUTE_LOCKDOWN_OVERRIDES = {
    "node_type_id": {
        "type": "forbidden",
        "hidden": True,
    },
}

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

# Name of the Unity Catalog connection for the Neo4j MCP server (Lab 7B).
_MCP_CONNECTION_NAME = "neo4j_mcp"

# Foundation Model API endpoints used by Labs 6.3–6.5.
_FOUNDATION_MODEL_ENDPOINTS = (
    "databricks-bge-large-en",
    "databricks-meta-llama-3-3-70b-instruct",
)


# ---------------------------------------------------------------------------
# Entitlement helpers
# ---------------------------------------------------------------------------

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
    users_group = find_group(client, "users")
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
# Step 1b: Personal Compute policy lockdown
# ---------------------------------------------------------------------------

def _find_personal_compute_policy(client: WorkspaceClient) -> Policy | None:
    """Find the built-in Personal Compute cluster policy.

    Matches on ``policy_family_id`` first, falling back to a name match
    on ``"Personal Compute"`` for older workspaces.

    Args:
        client: Databricks workspace client.

    Returns:
        The Policy object if found, else None.
    """
    policies = list(client.cluster_policies.list())

    # Prefer the canonical policy_family_id match.
    for policy in policies:
        if getattr(policy, "policy_family_id", None) == _PERSONAL_COMPUTE_POLICY_FAMILY:
            return policy

    # Fall back to name match for older workspaces.
    for policy in policies:
        if policy.name == "Personal Compute":
            return policy

    return None


def _policy_edit_kwargs(policy: Policy) -> dict:
    """Build base kwargs for ``cluster_policies.edit()`` preserving existing fields.

    The edit API is a full replacement — omitted fields are cleared.
    This helper captures the fields that must be preserved so callers
    only need to add/override what they want to change.
    """
    kwargs: dict = {
        "policy_id": policy.policy_id,
        "name": policy.name,
    }
    if policy.description:
        kwargs["description"] = policy.description
    if policy.policy_family_id:
        kwargs["policy_family_id"] = policy.policy_family_id
        if policy.policy_family_definition_overrides:
            kwargs["policy_family_definition_overrides"] = (
                policy.policy_family_definition_overrides
            )
    elif policy.definition:
        kwargs["definition"] = policy.definition
    return kwargs


def _is_policy_locked_down(policy: Policy) -> bool:
    """Check whether lockdown overrides are already applied."""
    if not policy.policy_family_definition_overrides:
        return False
    try:
        overrides = json.loads(policy.policy_family_definition_overrides)
    except (json.JSONDecodeError, TypeError):
        return False
    return overrides.get("node_type_id", {}).get("type") == "forbidden"


def lockdown_personal_compute_policy(client: WorkspaceClient) -> bool:
    """Disable the Personal Compute cluster policy.

    Personal Compute is a built-in cluster policy
    (``policy_family_id="personal-vm"``) that allows users to create
    single-node clusters without needing the ``allow-cluster-create``
    entitlement.

    This function applies two complementary restrictions:

    1. Overrides ``node_type_id`` to ``"forbidden"`` in the policy
       definition, making it impossible to select a node type and
       therefore impossible to create a cluster.
    2. Clears non-admin ACLs so the policy is hidden from the UI.

    This operation is idempotent — if the override is already present
    the step is reported as already locked down.

    Args:
        client: Databricks workspace client.

    Returns:
        True on success, False on error.
    """
    log("Step 1b: Locking down Personal Compute policy...")

    found = _find_personal_compute_policy(client)
    if found is None:
        log("  [yellow]Personal Compute policy not found — may be disabled "
            "at account level. Skipping.[/yellow]")
        return True

    log(f"  Found Personal Compute policy (id={found.policy_id})")

    # --- Check current state ------------------------------------------------
    full = client.cluster_policies.get(policy_id=found.policy_id)

    if _is_policy_locked_down(full):
        log("  [dim]Already locked down (node_type_id forbidden).[/dim]")
        return True

    # --- Apply lockdown overrides -------------------------------------------
    try:
        kwargs = _policy_edit_kwargs(full)
        kwargs["policy_family_definition_overrides"] = json.dumps(
            _PERSONAL_COMPUTE_LOCKDOWN_OVERRIDES
        )
        client.cluster_policies.edit(**kwargs)
    except Exception as e:
        log(f"  [red]Failed to edit Personal Compute policy: {e}[/red]")
        return False

    # --- Also clear non-admin ACLs ------------------------------------------
    try:
        client.cluster_policies.set_permissions(
            cluster_policy_id=full.policy_id,
            access_control_list=[],
        )
    except Exception as e:
        log(f"  [yellow]Warning: Could not clear policy ACLs: {e}[/yellow]")

    # --- Verify -------------------------------------------------------------
    try:
        updated = client.cluster_policies.get(policy_id=full.policy_id)
        if _is_policy_locked_down(updated):
            log("  [green]Verified: node_type_id forbidden on Personal "
                "Compute policy.[/green]")
        else:
            log("  [yellow]Warning: lockdown overrides not found after "
                "edit.[/yellow]")
    except Exception as e:
        log(f"  [yellow]Warning: Could not verify policy: {e}[/yellow]")

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

    existing = find_group(client, group_name)
    if existing and existing.id:
        log(f"  Found group (id={existing.id}).")
        return existing.id

    log(f"  [red]Error: Group '{group_name}' not found in this workspace.[/red]")
    log("  [red]This group must be created at the account level:[/red]")
    log("  [red]  1. Go to https://accounts.cloud.databricks.com > User management > Groups[/red]")
    log(f"  [red]  2. Create a group named '{group_name}'[/red]")
    log("  [red]  3. In the workspace, go to Settings > Identity and access > Groups[/red]")
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
# Step 4: Workspace folder permissions
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
    log(f"Step 4: Granting CAN_READ on workspace folder to '{group_name}'...")
    log(f"  Folder: {workspace_folder}")

    folder_id = get_workspace_folder_id(client, workspace_folder)
    if folder_id is None:
        log("  [yellow]Workspace folder not found — skipping.[/yellow]")
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
            log("  [yellow]Warning: CAN_READ not found in folder ACL after grant.[/yellow]")
    except Exception as e:
        log(f"  [yellow]Warning: Could not verify folder permissions: {e}[/yellow]")

    return True


# ---------------------------------------------------------------------------
# Step 5: SQL Warehouse access
# ---------------------------------------------------------------------------

def grant_warehouse_access(
    client: WorkspaceClient,
    warehouse_name: str,
    group_name: str,
) -> bool:
    """Grant CAN_USE on a SQL warehouse to a group.

    CAN_USE is the minimum permission level — users can start the warehouse,
    see its details, and run queries, but cannot stop, edit, or delete it.
    Required for Genie Space creation (Lab 7A) and general SQL access.

    Args:
        client: Databricks workspace client.
        warehouse_name: Name of the SQL warehouse to grant on.
        group_name: Group to receive the permission.

    Returns:
        True on success, False on error.
    """
    log(f"Step 5: Granting CAN_USE on warehouse '{warehouse_name}' to '{group_name}'...")

    warehouse_id = find_warehouse(client, warehouse_name)
    if not warehouse_id:
        log(f"  [red]Error: Warehouse '{warehouse_name}' not found.[/red]")
        return False

    log(f"  Found warehouse (id={warehouse_id})")

    try:
        client.permissions.update(
            request_object_type="sql/warehouses",
            request_object_id=warehouse_id,
            access_control_list=[
                AccessControlRequest(
                    group_name=group_name,
                    permission_level=PermissionLevel.CAN_USE,
                ),
            ],
        )
        log("  Done.")
    except Exception as e:
        log(f"  [red]Failed to grant warehouse permissions: {e}[/red]")
        return False

    # --- Verify ---
    try:
        perms = client.permissions.get(
            request_object_type="sql/warehouses",
            request_object_id=warehouse_id,
        )
        found = False
        for acl in perms.access_control_list or []:
            if acl.group_name == group_name:
                for p in acl.all_permissions or []:
                    if p.permission_level == PermissionLevel.CAN_USE:
                        found = True
                        break

        if found:
            log(f"  [green]Verified: CAN_USE present for '{group_name}'.[/green]")
        else:
            log("  [yellow]Warning: CAN_USE not found in warehouse ACL after grant.[/yellow]")
    except Exception as e:
        log(f"  [yellow]Warning: Could not verify warehouse permissions: {e}[/yellow]")

    return True


# ---------------------------------------------------------------------------
# Step 6: Unity Catalog connection grant
# ---------------------------------------------------------------------------

def grant_connection_access(
    client: WorkspaceClient,
    connection_name: str,
    group_name: str,
) -> bool:
    """Grant USE_CONNECTION on a Unity Catalog connection to a group.

    Required for the AgentBricks Neo4j MCP sub-agent (Lab 7B).  Non-fatal
    if the connection does not yet exist — the admin can create it later.

    Args:
        client: Databricks workspace client.
        connection_name: Name of the UC connection.
        group_name: Group to receive the privilege.

    Returns:
        True on success or if the connection does not exist (non-fatal).
    """
    log(f"Step 6: Granting USE_CONNECTION on '{connection_name}' to '{group_name}'...")

    try:
        client.grants.update(
            securable_type=SecurableType.CONNECTION.value,
            full_name=connection_name,
            changes=[
                PermissionsChange(
                    add=[Privilege.USE_CONNECTION],
                    principal=group_name,
                ),
            ],
        )
        log("  Done.")
    except NotFound:
        log(f"  [yellow]Connection '{connection_name}' not found — skipping.[/yellow]")
        log("  [yellow]Create the connection in Unity Catalog and re-run, or grant manually:[/yellow]")
        log(f"  [yellow]  GRANT USE CONNECTION ON CONNECTION `{connection_name}` TO `{group_name}`;[/yellow]")
        return True  # Non-fatal
    except Exception as e:
        log(f"  [yellow]Warning: Could not grant connection privilege: {e}[/yellow]")
        return True  # Non-fatal

    # --- Verify ---
    try:
        effective = client.grants.get(
            securable_type=SecurableType.CONNECTION.value,
            full_name=connection_name,
        )
        found = False
        for pa in effective.privilege_assignments or []:
            if pa.principal == group_name:
                granted = {p.value for p in (pa.privileges or [])}
                if Privilege.USE_CONNECTION.value in granted:
                    found = True
                break

        if found:
            log(f"  [green]Verified: USE_CONNECTION present for '{group_name}'.[/green]")
        else:
            log("  [yellow]Warning: USE_CONNECTION not found after grant.[/yellow]")
    except Exception as e:
        log(f"  [yellow]Warning: Could not verify connection grants: {e}[/yellow]")

    return True


# ---------------------------------------------------------------------------
# Step 7: Foundation Model API verification
# ---------------------------------------------------------------------------

def verify_foundation_model_access(client: WorkspaceClient) -> None:
    """Verify that Foundation Model API endpoints are accessible.

    Foundation Model endpoints are system endpoints available to all workspace
    users by default.  This step checks they exist and warns if any are
    missing or have restrictive permissions.

    This is a non-fatal verification step — it only logs warnings.
    """
    log("Step 7: Verifying Foundation Model API endpoints...")

    try:
        endpoints = {ep.name: ep for ep in client.serving_endpoints.list()}
    except Exception as e:
        log(f"  [yellow]Warning: Could not list serving endpoints: {e}[/yellow]")
        return

    all_ok = True
    for name in _FOUNDATION_MODEL_ENDPOINTS:
        if name in endpoints:
            log(f"  {name} — [green]found[/green]")
        else:
            log(f"  {name} — [yellow]not found[/yellow]")
            all_ok = False

    if all_ok:
        log("  [green]All Foundation Model endpoints are available.[/green]")
    else:
        log("  [yellow]Missing endpoints may not be provisioned in this workspace,[/yellow]")
        log("  [yellow]or may be restricted by an AI Gateway policy.[/yellow]")
        log("  [yellow]If participants cannot access them, grant CAN_QUERY[/yellow]")
        log("  [yellow]via Serving > endpoint > Permissions.[/yellow]")


# ---------------------------------------------------------------------------
# Step 8: AgentBricks prerequisites verification
# ---------------------------------------------------------------------------

def verify_agentbricks_prerequisites(client: WorkspaceClient) -> None:
    """Verify workspace prerequisites for AgentBricks (Lab 7B).

    Reminds the admin to check preview flags and serverless budget
    policies.  These are workspace/account-level settings that must be
    configured in the Databricks UI — they cannot be verified via the
    workspace SDK.

    This is a non-fatal verification step — it only logs reminders.
    """
    log("Step 8: Verifying AgentBricks prerequisites...")
    log()
    log("  [yellow]The following must be verified manually by a workspace admin:[/yellow]")
    log()
    log("  [yellow]Preview flags (Settings > Previews):[/yellow]")
    log("  [yellow]  - Mosaic AI Agent Bricks Preview[/yellow]")
    log("  [yellow]  - Production monitoring for MLflow[/yellow]")
    log("  [yellow]  - Agent Framework: On-Behalf-Of-User Authorization[/yellow]")
    log()
    log("  [yellow]Serverless budget policy (Settings > Compute > Budget policies):[/yellow]")
    log("  [yellow]  - Create a budget policy with nonzero budget[/yellow]")
    log("  [yellow]  - Assign it to the workshop group[/yellow]")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_permissions_lockdown(
    client: WorkspaceClient,
    volume_config: VolumeConfig,
    warehouse_config: WarehouseConfig | None = None,
    notebook_config: NotebookConfig | None = None,
) -> bool:
    """Run all Track C steps: lockdown, group, grants, compute ACLs, verifications.

    Per-user SINGLE_USER clusters give the assigned user implicit access,
    so cluster ACL grants are no longer needed here.

    Args:
        client: Databricks workspace client.
        volume_config: Volume configuration identifying the catalog to lock down.
        warehouse_config: Warehouse configuration (for CAN_USE grant).
        notebook_config: Notebook configuration (for workspace folder permissions).

    Returns:
        True if all fatal steps succeeded, False otherwise.
    """
    print_header("Track C: Permissions Lockdown")

    # Step 1: Entitlement lockdown
    if not lockdown_entitlements(client):
        return False

    log()

    # Step 1b: Personal Compute policy lockdown
    if not lockdown_personal_compute_policy(client):
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

    # Step 4: Workspace folder permissions
    if notebook_config is not None:
        if not grant_workspace_folder_read(client, notebook_config.workspace_folder, WORKSHOP_GROUP):
            return False
        log()

    # Step 5: SQL Warehouse CAN_USE (fatal — required for Genie + SQL)
    if warehouse_config is not None:
        if not grant_warehouse_access(client, warehouse_config.name, WORKSHOP_GROUP):
            return False
        log()

    # Step 6: UC connection grant (non-fatal — connection may not exist yet)
    grant_connection_access(client, _MCP_CONNECTION_NAME, WORKSHOP_GROUP)
    log()

    # Step 7: Foundation Model API verification (non-fatal — warn only)
    verify_foundation_model_access(client)
    log()

    # Step 8: AgentBricks prerequisites verification (non-fatal — warn only)
    verify_agentbricks_prerequisites(client)
    log()

    log("[green]Permissions lockdown complete.[/green]")
    log()
    log("[yellow]Note: Lakebase (serverless Postgres) and other serverless[/yellow]")
    log("[yellow]resources cannot be restricted at the user/group level.[/yellow]")
    log("[yellow]All workspace users inherit CAN CREATE on database instances[/yellow]")
    log("[yellow]and this permission cannot be removed. To block Lakebase[/yellow]")
    log("[yellow]creation, disable serverless compute at the workspace level[/yellow]")
    log("[yellow](Account Console > Settings > Feature Enablement).[/yellow]")
    return True


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_permissions(
    client: WorkspaceClient,
    volume_config: VolumeConfig,
    warehouse_config: WarehouseConfig | None = None,
) -> None:
    """Revoke catalog/connection grants and restore Personal Compute policy.

    The warehouse CAN_USE ACL is intentionally retained — the workspace
    permissions API only supports full replacement (PUT), which would
    overwrite other principals' ACLs.

    Does NOT delete the account-level group — it persists across
    setup/cleanup cycles.  Does NOT restore entitlements — that is a
    deliberate admin action.  Each step is idempotent.

    Args:
        client: Databricks workspace client.
        volume_config: Volume configuration identifying the catalog to clean up.
        warehouse_config: Warehouse configuration (for logging retention note).
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

    # Restore Personal Compute policy
    log("  Restoring Personal Compute policy...")
    found = _find_personal_compute_policy(client)
    if found is not None:
        # Remove lockdown overrides
        try:
            full = client.cluster_policies.get(policy_id=found.policy_id)
            kwargs = _policy_edit_kwargs(full)
            # Reset overrides to empty — removes the node_type_id forbidden rule
            kwargs["policy_family_definition_overrides"] = "{}"
            client.cluster_policies.edit(**kwargs)
            log("    Removed lockdown overrides.")
        except Exception as e:
            log(f"    [yellow]Skipped policy edit: {e}[/yellow]")

        # Restore CAN_USE for 'users' group
        try:
            client.cluster_policies.set_permissions(
                cluster_policy_id=found.policy_id,
                access_control_list=[
                    ClusterPolicyAccessControlRequest(
                        group_name="users",
                        permission_level=ClusterPolicyPermissionLevel.CAN_USE,
                    ),
                ],
            )
            log("    Restored CAN_USE for 'users' group.")
        except Exception as e:
            log(f"    [yellow]Skipped ACL restore: {e}[/yellow]")
    else:
        log("    Personal Compute policy not found — skipping.")

    # Warehouse CAN_USE — intentionally left in place.
    # The permissions API only supports PATCH (additive) and PUT (full replace).
    # PUT would overwrite all other ACLs on the warehouse.  Since the warehouse
    # is retained during cleanup, leaving the workshop group's CAN_USE is safe.
    if warehouse_config is not None:
        log(f"  [dim]Warehouse '{warehouse_config.name}' CAN_USE ACL retained (warehouse is not deleted).[/dim]")

    # Revoke connection grant
    log(f"  Revoking USE_CONNECTION on '{_MCP_CONNECTION_NAME}' for '{WORKSHOP_GROUP}'...")
    try:
        client.grants.update(
            securable_type=SecurableType.CONNECTION.value,
            full_name=_MCP_CONNECTION_NAME,
            changes=[
                PermissionsChange(
                    remove=[Privilege.USE_CONNECTION],
                    principal=WORKSHOP_GROUP,
                ),
            ],
        )
        log("    Done.")
    except NotFound:
        log("    Connection not found — skipping.")
    except Exception as e:
        log(f"    [yellow]Skipped: {e}[/yellow]")

    # Note: the account-level group is NOT deleted — it is managed in the
    # Databricks Account Admin console and should persist across runs.
    log(f"  [dim]Account-level group '{WORKSHOP_GROUP}' is preserved (not deleted).[/dim]")

    log()
    log("[yellow]Note: Entitlements on 'users' group were NOT restored.[/yellow]")
    log("[yellow]To re-enable compute creation, manually add 'allow-cluster-create'[/yellow]")
    log("[yellow]to the 'users' group in Settings > Identity and access > Groups.[/yellow]")
