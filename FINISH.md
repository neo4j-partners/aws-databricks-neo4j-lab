# Proposal: Complete Permissions Automation for Genie, Agents, and Foundation Models

## Background

Track C of `databricks-setup` currently handles four things:

1. **Entitlement lockdown** — strips `allow-cluster-create` and `allow-instance-pool-create` from the built-in `users` group so participants cannot create compute resources.
2. **Personal Compute policy lockdown** — sets `node_type_id: forbidden` on the Personal Compute policy so it cannot bypass the entitlement removal.
3. **Workshop group verification** — confirms the `aircraft_workshop_group` account-level group exists in the workspace.
4. **Unity Catalog grants** — grants `USE_CATALOG`, `USE_SCHEMA`, `SELECT`, `READ_VOLUME`, and `BROWSE` at the catalog level.

This covers Labs 5 and 6. Labs 7A (Genie Space) and 7B (AgentBricks) require three additional categories of permissions that are not yet automated. The PERMS.md guide documents them in Sections 5, 6, and 7. This proposal describes what needs to be added and why, without prescribing code.

---

## Gap 1: SQL Warehouse Access for the Workshop Group

**PERMS.md reference:** Section 4 (SQL Warehouse Permissions)

**Current state:** The automation creates or discovers a `Starter Warehouse` (serverless) during Track B for running lakehouse table creation SQL. However, it never grants the workshop group permission to use that warehouse. Only admins can currently run queries against it.

**What is needed:** Grant `CAN_USE` on the Starter Warehouse to `aircraft_workshop_group`. This is the minimum permission level — it lets participants start the warehouse, see its details, and run queries, but they cannot stop, edit, or delete it.

**Why it matters:** Both Genie Spaces and general SQL access require a warehouse. Without `CAN_USE`, participants cannot execute any SQL queries, which blocks Lab 7A entirely.

**Where it fits in Track C:** After the UC grants step (current Step 3). The warehouse must already exist before this step runs, so it depends on Track B completing first, which is already the case in the normal `setup` flow.

**Cleanup consideration:** The cleanup flow should remove the `CAN_USE` grant from the workshop group on the warehouse, or at minimum this is a no-op if the warehouse is deleted.

---

## Gap 2: Unity Catalog Connection Grant for Neo4j MCP

**PERMS.md reference:** Section 2 (Unity Catalog Grants — MCP Connection Grant)

**Current state:** The catalog-level UC grants cover tables, schemas, and volumes. They do not cover UC Connections, which are separate securables. The `neo4j_mcp` connection is used by the AgentBricks Neo4j sub-agent in Lab 7B.

**What is needed:** Grant `USE_CONNECTION` on the connection named `neo4j_mcp` to `aircraft_workshop_group`. This allows participants to reference the connection when configuring the MCP sub-agent in AgentBricks.

**Precondition:** The `neo4j_mcp` connection must already exist in Unity Catalog. This connection is created manually by the admin as part of workspace preparation (it contains the Neo4j server URL and is not something the automation currently creates). The new step should handle the case where the connection does not yet exist — log a warning and continue rather than failing the entire lockdown.

**Where it fits in Track C:** Alongside or immediately after the catalog grants step. It is a separate `grants.update` call because the securable type is `CONNECTION`, not `CATALOG`.

**Cleanup consideration:** Revoke `USE_CONNECTION` from the workshop group during cleanup. Like the catalog grant revocation, this should be a no-op if the connection has already been deleted.

---

## Gap 3: Foundation Model API Access Verification

**PERMS.md reference:** Section 5 (Foundation Model API Access)

**Current state:** Foundation Model endpoints (`databricks-bge-large-en` and `databricks-meta-llama-3-3-70b-instruct`) are system-level serving endpoints available to all workspace users by default. The automation does not verify this.

**What is needed:** A verification step — not a grant — that checks whether the workshop group (or all workspace users) can query these two endpoints. The step should:

- List serving endpoints and confirm the two Foundation Model endpoints exist.
- Check their permission ACLs to verify there are no restrictive AI Gateway policies blocking access.
- If restrictions are found, log a warning telling the admin to grant `CAN_QUERY` on the affected endpoint(s) to `aircraft_workshop_group`.

**Why verification instead of a grant:** These are system endpoints managed by Databricks. In most workspaces they just work. Proactively granting `CAN_QUERY` on them is unnecessary and could fail if the endpoints have non-standard configurations. A verification-and-warn approach is more robust.

**Where it fits in Track C:** As a non-fatal verification step after the main grants. It should never cause the lockdown to fail — only warn.

---

## Gap 4: Genie Space Creation Prerequisites

**PERMS.md reference:** Section 6 (Genie Space Permissions)

**Current state:** Two of the three prerequisites for creating a Genie Space are already handled:

| Prerequisite | Status |
|---|---|
| `databricks-sql-access` entitlement on `users` group | Already preserved — the entitlement lockdown only removes `allow-cluster-create` and `allow-instance-pool-create` |
| `SELECT` on lakehouse tables | Already granted via catalog-level UC grants |
| `CAN_USE` on a serverless SQL warehouse | **Not yet granted** (see Gap 1) |

**What is needed:** Once Gap 1 (warehouse `CAN_USE`) is addressed, all Genie Space creation prerequisites are satisfied. No additional Genie-specific automation is needed.

**Genie Space ACLs are participant-managed:** When a participant creates a Genie Space, they become its owner with `CAN_MANAGE`. Sharing with other users is up to them. The automation does not need to manage Genie Space ACLs.

**Where it fits:** This is fully covered by Gap 1. No separate step required.

---

## Gap 5: AgentBricks Creation Prerequisites

**PERMS.md reference:** Section 7 (AgentBricks Permissions)

**Current state:** AgentBricks has two categories of prerequisites: admin-level workspace settings (previews that must be enabled) and user-level permissions. The automation handles neither.

### Admin-Level Workspace Settings (Verification Only)

These are workspace-level preview flags that must be enabled before the workshop. They are toggled in the Databricks admin UI and cannot be set via the SDK:

| Setting | UI Path |
|---|---|
| Mosaic AI Agent Bricks Preview | Settings > Previews > Agent Bricks |
| Production monitoring for MLflow | Settings > Previews |
| Agent Framework: On-Behalf-Of-User Authorization | Settings > Previews |

**What is needed:** A verification step that checks whether these preview features are enabled. The Databricks SDK may or may not expose these settings via API. If it does, the step should read and verify them. If not, the step should log a reminder to the admin to check them manually. Either way, this step should be non-fatal — a warning, not a blocker.

### User-Level Permissions

| Prerequisite | Status |
|---|---|
| `workspace-access` entitlement | Already preserved on `users` group |
| Access to Mosaic AI Model Serving | Enabled by `workspace-access` |
| `SELECT` on Unity Catalog tables | Already granted via catalog-level UC grants |
| `USE_CONNECTION` on `neo4j_mcp` | **Not yet granted** (see Gap 2) |
| Serverless budget policy with nonzero budget | **Not yet assigned** |

**Serverless budget policy:** AgentBricks runs on serverless compute and requires a budget policy. Budget policies are created and assigned in the admin UI (Settings > Compute > Budget policies). The SDK may support creating or assigning budget policies, but this is a cost-control decision that admins should make deliberately. The automation should verify that a budget policy exists and is assigned to the workshop group, and warn if not — rather than creating one automatically.

**Where it fits in Track C:** The connection grant is covered by Gap 2. The preview verification and budget policy check should be a new non-fatal verification step at the end of the lockdown, after all grants are applied.

---

## Proposed New Track C Steps

The updated `run_permissions_lockdown` orchestrator would look like this:

| Step | Action | Fatal? | New? |
|---|---|---|---|
| 1 | Remove entitlements from `users` group | Yes | Existing |
| 1b | Disable Personal Compute policy | Yes | Existing |
| 2 | Verify workshop group exists | Yes | Existing |
| 3 | Grant catalog-level UC privileges | Yes | Existing |
| 4 | Grant workspace folder read access | Yes | Existing |
| **5** | **Grant `CAN_USE` on Starter Warehouse** | **Yes** | **New** |
| **6** | **Grant `USE_CONNECTION` on `neo4j_mcp`** | **No** | **New** |
| **7** | **Verify Foundation Model endpoint access** | **No** | **New** |
| **8** | **Verify AgentBricks prerequisites (previews, budget policy)** | **No** | **New** |

Steps 5 is fatal because without warehouse access participants cannot do Lab 7 at all. Steps 6, 7, and 8 are non-fatal because their targets (connection, endpoints, previews) may not exist yet at the time the lockdown runs, and the admin can address them later.

---

## Cleanup Considerations

The cleanup flow (`cleanup_permissions`) should be updated to:

- **Revoke `CAN_USE`** on the Starter Warehouse for the workshop group (before the warehouse is deleted, if applicable).
- **Revoke `USE_CONNECTION`** on `neo4j_mcp` for the workshop group (non-fatal if the connection does not exist).
- Foundation Model endpoint access and AgentBricks previews do not need cleanup — they are workspace-level settings, not group-specific grants.

---

## Summary of Changes

| Gap | What to Add | Enables |
|---|---|---|
| Warehouse `CAN_USE` | Grant on Starter Warehouse for workshop group | Genie Space creation (Lab 7A), SQL queries |
| Connection `USE_CONNECTION` | Grant on `neo4j_mcp` for workshop group | AgentBricks Neo4j sub-agent (Lab 7B) |
| Foundation Model verification | Check endpoint accessibility, warn if blocked | Labs 6.3-6.5 confidence |
| AgentBricks verification | Check preview flags and budget policy, warn if missing | AgentBricks creation (Lab 7B) confidence |

The first two items are concrete permission grants that close real access gaps. The last two are verification-and-warn steps that give the admin confidence that the workspace is ready without making irreversible changes to workspace-level settings.

---

## Implementation Status

All five gaps have been implemented. Below is what was changed, where, and any design decisions made.

### Files Modified

| File | What Changed |
|---|---|
| `permissions.py` | Added 4 new step functions, updated module docstring, added constants and imports, updated orchestrator and cleanup signatures |
| `cleanup.py` | Added `warehouse_config` parameter to `run_cleanup`, passes it through to `cleanup_permissions` |
| `main.py` | Passes `warehouse_config=config.warehouse` to both `run_permissions_lockdown` and `run_cleanup` |

### New Functions in permissions.py

| Function | Step | Fatal? | Purpose |
|---|---|---|---|
| `grant_warehouse_access()` | 5 | Yes | Grants `CAN_USE` on the Starter Warehouse using the workspace permissions API (`sql/warehouses` object type). Verifies the ACL after granting. |
| `grant_connection_access()` | 6 | No | Grants `USE_CONNECTION` on `neo4j_mcp` via the UC grants API (`SecurableType.CONNECTION`). Handles `NotFound` gracefully if the connection doesn't exist yet, and prints the manual SQL grant as guidance. |
| `verify_foundation_model_access()` | 7 | No | Lists all serving endpoints and checks whether the two required Foundation Model endpoints exist. Warns if missing but never fails the lockdown. |
| `verify_agentbricks_prerequisites()` | 8 | No | Checks for serverless/budget cluster policies and logs the three admin preview flags that must be verified manually. |

### New Constants

| Constant | Value | Purpose |
|---|---|---|
| `_MCP_CONNECTION_NAME` | `"neo4j_mcp"` | Name of the UC connection for the Neo4j MCP server |
| `_FOUNDATION_MODEL_ENDPOINTS` | `("databricks-bge-large-en", "databricks-meta-llama-3-3-70b-instruct")` | Endpoint names to verify |

### Design Decisions

1. **Warehouse cleanup is a no-op.** The Databricks permissions API uses PATCH semantics for `update` but PUT semantics for `set_permissions`. Using `set_permissions` to remove the workshop group would overwrite all other ACLs. Since the warehouse is retained during cleanup (it's not deleted), the `CAN_USE` ACL is left in place with a log note. The group itself persists across cycles anyway.

2. **Connection grant uses `SecurableType.CONNECTION.value`.** Following the existing pattern for `SecurableType.CATALOG.value` (see MEMORY.md gotcha about enum not being a `str` enum).

3. **Foundation Model check is existence-only.** The step checks whether the endpoints appear in the serving endpoints list. It does not attempt to query them or inspect their ACLs, because system endpoints may not expose permission details the same way custom endpoints do. If they're missing from the list entirely, it warns about AI Gateway restrictions.

4. **AgentBricks preview flags are manual.** The Databricks SDK does not expose workspace preview toggles via API. The step logs a reminder listing all three flags. Budget policy detection uses a heuristic search over cluster policies (looking for `policy_family_id == "job-cluster"` or names containing "budget" or "serverless") since the budget policy API is separate from the standard cluster policies API.

5. **All new parameters are optional with defaults of `None`.** This preserves backward compatibility — existing callers that don't pass `warehouse_config` will simply skip the warehouse grant step.
