# Track C Implementation Plan: Workshop User Lockdown

A plan for adding a third track to the `lab_setup/auto_scripts/` CLI that creates a `workshop-users` group, locks down compute creation, grants read-only Unity Catalog access, and sets cluster attach permissions.

---

## Goal

After running `databricks-setup setup`, Track C should leave the workspace in a state where workshop participants can:

- Attach notebooks to the pre-created cluster and run code
- Read CSV/MD files from the lab volume
- Query lakehouse tables
- Browse the catalog in Catalog Explorer

And **cannot**:

- Create clusters, SQL warehouses, or instance pools
- Write to or modify any Unity Catalog objects
- Restart, terminate, or reconfigure the cluster

---

## Scope

Track C is implemented in five phases, ordered from highest-impact lockdown to optional convenience:

1. **Entitlement lockdown** — remove compute creation rights from the `users` group
2. **Group creation** — create `workshop-users` group (no members yet, test the group exists)
3. **Unity Catalog grants + Cluster permissions** — read-only data access, attach-only cluster access
4. **User enumeration and auto-add** — populate the group with non-admin users
5. **Warehouse, FMAPI, Genie, AgentBricks** — remaining permissions (future)

---

## How It Fits Into the Existing Architecture

### Current structure

The CLI runs two sequential tracks today:

- **Track A** — Create or reuse a cluster, install libraries (Neo4j Spark Connector + Python packages)
- **Track B** — Upload data files to the volume, create lakehouse tables via SQL warehouse

Each track is a module with a top-level function that takes `(client: WorkspaceClient, config: Config)` and returns a `bool` for success/failure. The `main.py` orchestrator calls them in sequence and prints a summary.

### Where Track C fits

Track C runs **after** Track A and Track B, because it needs the cluster ID from Track A and the catalog/schema names from the volume config.

The execution order becomes: Track A (cluster + libraries) → Track B (data + tables) → Track C (permissions lockdown).

### New module

Create a single new file: `src/databricks_setup/permissions.py`

This module will contain all Track C logic. No other existing files need to change except:

- `main.py` — add a call to the Track C function after Tracks A and B
- `config.py` — add a config dataclass for the group name (with a sensible default like `"workshop-users"`)
- `models.py` — add a field to `SetupResult` to track whether Track C succeeded

### SDK methods to use

All operations use the Databricks Python SDK (`databricks-sdk`), which the project already depends on. No new dependencies needed.

| Operation | SDK Method | Notes |
|---|---|---|
| Remove entitlements from group | `w.groups.patch()` with `PatchOp.REMOVE` | SCIM filter path syntax |
| Read group entitlements | `w.groups.get()` | Check current state before/after |
| Find or create group | `w.groups.list(filter=...)` then `w.groups.create()` | List first to avoid 409 conflict |
| Add users to group | `w.groups.patch()` with `PatchOp.ADD` | Idempotent — safe to re-run |
| Grant UC privileges | `w.grants.update()` | Additive — does not replace existing grants |
| Set cluster ACL | `w.clusters.update_permissions()` | Additive PATCH, not destructive PUT |
| Read current grants | `w.grants.get()` | For verification/logging |
| Read current cluster ACL | `w.clusters.get_permissions()` | For verification/logging |

---

## What Track C Does (Step by Step)

### Step 1: Lock down entitlements on the `users` group

Every Databricks workspace user is automatically a member of the built-in `users` group. Entitlements on this group apply to everyone. This step removes compute-creation rights at the broadest level before granting any targeted permissions.

Find the `users` group by listing groups with a SCIM display name filter. Then use `w.groups.patch()` with `PatchOp.REMOVE` to strip two entitlements:

| Entitlement | SCIM path filter | What it blocks |
|---|---|---|
| `allow-cluster-create` | `entitlements[value eq "allow-cluster-create"]` | All-purpose clusters, job clusters, and SQL warehouses |
| `allow-instance-pool-create` | `entitlements[value eq "allow-instance-pool-create"]` | Instance pools |

Removing an entitlement that is not currently set does not raise an error, so this is inherently idempotent.

Before removing, read the group with `w.groups.get()` and log the current entitlements so the admin sees what changed. After removing, read again and log the new state.

> **Impact:** This affects all non-admin users workspace-wide, not just workshop participants. Workspace admins always retain these entitlements — they cannot be removed from the `admins` group. For a dedicated workshop workspace this is the correct behavior.

### Step 2: Find or create the `workshop-users` group

Check if a group named `workshop-users` already exists by listing groups with a SCIM filter. If it exists, reuse it. If not, create it.

This follows the same idempotent pattern used elsewhere in the codebase (e.g., `get_or_create_cluster` checks for an existing cluster before creating one).

Do **not** add any members in this step. Group membership is handled in a later phase after the group and its permissions are tested.

Log the group name and ID either way.

### Step 3: Grant read-only Unity Catalog privileges

Use `w.grants.update()` to grant five privileges on the catalog to `workshop-users`. Granting at the catalog level means all current and future schemas, tables, and volumes within the catalog inherit the privileges automatically. This avoids having to grant on each individual object.

The five grants are:

| Privilege | Securable | Purpose |
|---|---|---|
| `USE_CATALOG` | Catalog `aws-databricks-neo4j-lab` | Required to interact with anything in the catalog |
| `USE_SCHEMA` | Catalog `aws-databricks-neo4j-lab` | Required to access objects within schemas |
| `SELECT` | Catalog `aws-databricks-neo4j-lab` | Read table data (lakehouse tables in Lab 7) |
| `READ_VOLUME` | Catalog `aws-databricks-neo4j-lab` | Read volume files (CSVs + manuals in Labs 5-6) |
| `BROWSE` | Catalog `aws-databricks-neo4j-lab` | View metadata in Catalog Explorer |

All five can be granted in a single `w.grants.update()` call by passing multiple privileges in one `PermissionsChange` object.

The `w.grants.update()` method is additive — it does not remove existing grants for other principals. Re-running it with the same privileges is a no-op.

The catalog name comes from the existing `VolumeConfig.catalog` field, so no new config is needed.

### Step 4: Grant `CAN_ATTACH_TO` on the workshop cluster

Use `w.clusters.update_permissions()` (the PATCH variant, not `set_permissions` which is a destructive PUT) to grant `CAN_ATTACH_TO` to the `workshop-users` group on the cluster created by Track A.

The cluster ID is already available from Track A's return value (`SetupResult.cluster_id`).

`update_permissions` merges with existing ACLs — it will not remove the admin's `CAN_MANAGE` or any other existing permissions.

Re-running this with the same permission level is a no-op.

### Step 5: Verify and log results

After all operations, read back the current state and log it:

- Read the `users` group entitlements — confirm `allow-cluster-create` and `allow-instance-pool-create` are absent
- Confirm the `workshop-users` group exists and log its ID
- Call `w.grants.get()` on the catalog — confirm the five privileges are present for `workshop-users`
- Call `w.clusters.get_permissions()` on the cluster — confirm `CAN_ATTACH_TO` for `workshop-users`

Display a summary table (using Rich, matching the style of the library status table in Track A).

---

## Configuration

### New config fields

Add a `PermissionsConfig` dataclass with one field:

- `group_name` — defaults to `"workshop-users"`, overridable via `GROUP_NAME` environment variable

This keeps the pattern consistent with `ClusterConfig`, `WarehouseConfig`, etc.

### No new CLI arguments needed

The group name default is sufficient for most workshops. The `.env` file override handles edge cases.

---

## Cleanup

Update the existing `cleanup` command to reverse Track C in order:

1. Remove all UC grants for `workshop-users` on the catalog (using `w.grants.update()` with the `remove` list)
2. Remove cluster ACL for `workshop-users` (using `w.clusters.update_permissions()` to remove the entry)
3. Delete the `workshop-users` group (using `w.groups.delete()`)

Add these steps **before** the existing catalog/schema deletion steps, since you cannot revoke grants on a catalog that no longer exists.

**Entitlement restore decision:** Cleanup should **not** automatically re-add `allow-cluster-create` and `allow-instance-pool-create` to the `users` group. Restoring compute creation rights is a deliberate admin action, not something that should happen accidentally during cleanup. Log a reminder that entitlements were not restored, with instructions to re-add them manually if needed.

Follow the same idempotent pattern as existing cleanup — catch `NotFound` errors and log "Already deleted."

---

## Phased Implementation Plan

### Phase 1: Entitlement lockdown — IMPLEMENTED

The highest-impact change and the one most likely to surface issues. Implements Step 1 only.

Strip `allow-cluster-create` and `allow-instance-pool-create` from the built-in `users` group. This immediately prevents all non-admin users from creating any compute resources.

**Files created/modified:**
- `src/databricks_setup/permissions.py` — new module with `lockdown_entitlements(client)` function
- `src/databricks_setup/config.py` — added `PermissionsConfig` dataclass (group_name, `GROUP_NAME` env var), `lockdown_ok` field on `SetupResult`
- `src/databricks_setup/main.py` — wired Track C after Tracks A and B, updated summary output

**Implementation details:**
- `lockdown_entitlements()` finds the built-in `users` group via SCIM filter, snapshots current entitlements, removes targets, then verifies the final state
- Uses `w.groups.patch()` with `PatchOp.REMOVE` and SCIM filter path syntax
- Idempotent: checks which entitlements are present before removing, skips those already absent
- Verification: reads back the group after removal and confirms target entitlements are gone
- Returns `bool` (True/False) following the `create_lakehouse_tables()` pattern
- Logs before/after entitlement state, counts removed vs skipped

**What to test:**
- Run `databricks-setup setup` — entitlements should be removed, logged
- Run it again — idempotent, no errors, same end state
- Log in as a non-admin user:
  - Try to create a cluster — **blocked**
  - Try to create a SQL warehouse — **blocked**
  - Try to create an instance pool — **blocked**
- Confirm workspace admin can still create all of the above
- Run `databricks-setup cleanup` — entitlements are NOT auto-restored (see Cleanup section)

### Phase 2: Group creation — IMPLEMENTED

Implements Step 2 only. Creates the `workshop-users` group with no members. This is intentionally separated from user-add so you can verify the group exists and test granting permissions to it before populating it.

**Files modified:**
- `src/databricks_setup/permissions.py` — added `get_or_create_group(client, group_name)` function and `_find_group_by_name()` helper

**Implementation details:**
- `_find_group_by_name()` lists groups with a SCIM `displayName eq` filter and returns the first match or `None`
- `get_or_create_group()` checks for an existing group first (idempotent), creates if absent, returns the group ID
- Uses the `WORKSHOP_GROUP` constant (`"workshop-users"`) — no config dataclass needed since only one group is locked down
- Follows the same check-then-create pattern as `get_or_create_cluster()` in Track A
- Returns `str | None` — `None` signals failure and aborts Track C
- Cleanup: `cleanup_permissions()` finds and deletes the group; `NotFound` is caught for idempotency

**What to test:**
- Run setup — group is created, ID is logged
- Run again — group is reused, not duplicated
- Check the group in Settings > Identity and access > Groups — exists, zero members
- Run cleanup — group is deleted
- Run cleanup again — no error (idempotent)

### Phase 3: UC grants and cluster permissions — IMPLEMENTED

Implements Steps 3, 4, and 5. Depends on Phase 2 (group must exist) and Track A (cluster must exist).

**Files modified:**
- `src/databricks_setup/permissions.py` — added `grant_catalog_read_only()`, `grant_cluster_attach()`, `run_permissions_lockdown()` orchestrator, and `cleanup_permissions()`
- `src/databricks_setup/main.py` — updated Track C call to pass `cluster_id` and `catalog_name` to `run_permissions_lockdown()`
- `src/databricks_setup/cleanup.py` — added `cleanup_permissions()` call before catalog deletion

**Implementation details:**
- `grant_catalog_read_only(client, catalog_name, group_name)`:
  - Grants five privileges (`USE_CATALOG`, `USE_SCHEMA`, `SELECT`, `READ_VOLUME`, `BROWSE`) in a single `w.grants.update()` call
  - Uses `SecurableType.CATALOG` so privileges cascade to all schemas, tables, and volumes
  - Verification: reads back grants with `w.grants.get()` and confirms all five are present for the group
  - Returns `bool` for success/failure

- `grant_cluster_attach(client, cluster_id, group_name)`:
  - Uses `w.clusters.update_permissions()` (PATCH, not PUT) to grant `CAN_ATTACH_TO`
  - Additive — preserves admin's `CAN_MANAGE` and all other existing ACLs
  - Verification: reads back cluster permissions and confirms the grant is present
  - Returns `bool` for success/failure

- `run_permissions_lockdown(client, cluster_id, catalog_name)`:
  - Orchestrator function that calls all four steps in sequence: lockdown → group → UC grants → cluster ACL
  - Short-circuits on first failure (each step returns `bool`)
  - Called from `_run_setup()` in `main.py` after Tracks A and B

- `cleanup_permissions(client, catalog_name)`:
  - Revokes all five catalog privileges for `workshop-users` (before catalog is deleted)
  - Deletes the `workshop-users` group (which automatically removes cluster ACL entries)
  - Does NOT restore entitlements on the `users` group — logs a reminder for manual action
  - Called from `run_cleanup()` in `cleanup.py` before `_drop_lakehouse_schema()`
  - Each step catches `NotFound` for idempotency

**What to test:**
- Run setup — grants applied, verification passes
- Run again — idempotent, same grants, no errors
- Manually add a test user to `workshop-users` in the UI
- Log in as that user:
  - Browse `aws-databricks-neo4j-lab` in Catalog Explorer — **works**
  - Run `SELECT * FROM lakehouse.aircraft LIMIT 5` — **returns rows**
  - Run `CREATE TABLE lakehouse.test (id INT)` — **denied**
  - Try to upload a file to the volume — **denied**
  - Attach a notebook to the workshop cluster — **works**
  - Try to restart the cluster — **blocked**
  - Try to create a new cluster — **blocked** (from Phase 1)

### Phase 4: User enumeration and auto-add (future)

Populate the `workshop-users` group with all non-admin workspace users. This is deferred because:

- It requires deciding the filtering logic (exclude admins, service principals, etc.)
- Admins may prefer to control group membership manually
- The lockdown and grants are fully functional without it — you just add users to the group by hand

**What to build:**
- Add `add_users_to_group(client, group_id)` function
- Add a `--skip-user-add` CLI flag to opt out
- Filter: list all users, exclude members of the `admins` group and service principals
- Batch all user IDs into a single SCIM PATCH operation

**What to test:**
- Run setup with 3+ users in workspace — all non-admins appear in the group
- Run again — no duplicates
- Add a new user to workspace, run again — new user gets added

### Phase 5: Warehouse, FMAPI, Genie, AgentBricks (future)

Add `CAN_USE` on the SQL warehouse, `CAN_QUERY` on Foundation Model endpoints, `USE_CONNECTION` on the MCP connection, and any AgentBricks-specific setup. See PERMS.md for the full list.

---

## Testing Checklist

### Automated checks (run in the tool itself, Step 5)

After all operations, the tool should read back state and verify:

- [ ] `users` group entitlements do NOT include `allow-cluster-create` or `allow-instance-pool-create`
- [ ] Group `workshop-users` exists and has the expected ID
- [ ] `w.grants.get()` on the catalog shows all five privileges for `workshop-users`
- [ ] `w.clusters.get_permissions()` shows `CAN_ATTACH_TO` for `workshop-users`

Log PASS/FAIL for each check in the summary table.

### Manual checks — entitlement lockdown (Phase 1)

- [ ] Log in as a non-admin user
- [ ] Try "Create Cluster" — **blocked**
- [ ] Try to create a SQL warehouse — **blocked**
- [ ] Try to create an instance pool — **blocked**
- [ ] Log in as workspace admin — confirm all three still work

### Manual checks — data access and cluster (Phases 2-3)

After manually adding a test user to `workshop-users`:

- [ ] Open Catalog Explorer — can see `aws-databricks-neo4j-lab` catalog
- [ ] Run `SELECT * FROM aws-databricks-neo4j-lab.lakehouse.aircraft LIMIT 5` — returns rows
- [ ] Run `CREATE TABLE aws-databricks-neo4j-lab.lakehouse.test (id INT)` — **denied**
- [ ] Read a file from the volume path — succeeds
- [ ] Try to upload a file to the volume — **denied**
- [ ] Attach a notebook to the workshop cluster — succeeds
- [ ] Try to restart the cluster — **blocked**
- [ ] Try to terminate the cluster — **blocked**

### Idempotency checks

- [ ] Run `databricks-setup setup` twice in a row — no errors, same end state
- [ ] Run `databricks-setup cleanup` then `setup` — clean slate, everything recreated
- [ ] Run `databricks-setup cleanup` twice — no errors on second run

---

## Reference Links

### Databricks Python SDK

| Topic | URL |
|---|---|
| SDK Groups API (create, list, patch, delete) | https://databricks-sdk-py.readthedocs.io/en/stable/workspace/iam/groups.html |
| SDK Users API (list, get) | https://databricks-sdk-py.readthedocs.io/en/stable/workspace/iam/users.html |
| SDK Grants API (update, get) | https://databricks-sdk-py.readthedocs.io/en/stable/workspace/catalog/grants.html |
| SDK Clusters API (update_permissions, get_permissions) | https://databricks-sdk-py.readthedocs.io/en/stable/workspace/compute/clusters.html |

### Databricks REST API

| Topic | URL |
|---|---|
| SCIM Groups (create, patch, list) | https://docs.databricks.com/api/workspace/groups |
| SCIM Users (list, get) | https://docs.databricks.com/api/workspace/users |
| Unity Catalog Grants (update, get) | https://docs.databricks.com/api/workspace/grants/update |
| Cluster Permissions (set, update, get) | https://docs.databricks.com/api/workspace/clusters/setpermissions |

### Databricks Documentation

| Topic | URL |
|---|---|
| Manage privileges in Unity Catalog | https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/ |
| Compute ACLs (cluster permission levels) | https://docs.databricks.com/aws/en/security/auth/access-control/ |
| Workspace entitlements | https://docs.databricks.com/aws/en/admin/users-groups/ |
| Identity and access management | https://docs.databricks.com/aws/en/admin/users-groups/ |
