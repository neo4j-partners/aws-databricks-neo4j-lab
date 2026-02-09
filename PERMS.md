# Databricks Workshop Permissions Guide

Permissions configuration for the AWS + Databricks + Neo4j workshop. The goal is to give participants **read-only data access**, **attach-only compute access**, and the ability to **create Genie Spaces and Agents** — while **blocking all compute resource creation**.

---

## Table of Contents

- [Quick Setup Checklist](#quick-setup-checklist)
- [1. Workspace Entitlements](#1-workspace-entitlements)
- [2. Unity Catalog Grants](#2-unity-catalog-grants)
- [3. Cluster Permissions](#3-cluster-permissions)
- [4. SQL Warehouse Permissions](#4-sql-warehouse-permissions)
- [5. Foundation Model API Access](#5-foundation-model-api-access)
- [6. Genie Space Permissions](#6-genie-space-permissions)
- [7. AgentBricks Permissions](#7-agentbricks-permissions)
- [8. Serverless Compute](#8-serverless-compute)
- [9. Admin Verification](#9-admin-verification)

---

## Quick Setup Checklist

Run these steps **as a workspace admin** after the automated `databricks-setup` provisioning completes.

### Step 1: Create a `workshop-users` group

Add all participant accounts to this group. All positive grants (UC privileges, compute ACLs) target this group.

### Step 2: Lock down entitlements on the `users` group

> **Why `users` and not `workshop-users`?** Every Databricks workspace user is **automatically** a member of the built-in `users` group — this membership cannot be removed. Entitlements on `users` apply to everyone. If you only remove entitlements from `workshop-users`, participants still inherit them through `users`. The lockdown **must** happen on `users`.
>
> **Impact:** This affects all non-admin users in the workspace, not just workshop participants. For a dedicated workshop workspace this is fine. If you share the workspace with other teams who need cluster creation, add those teams to a separate group and grant `allow-cluster-create` to that group instead.

| Entitlement (UI Name) | API Name | Action | Effect |
|---|---|---|---|
| Allow unrestricted cluster creation | `allow-cluster-create` | **REMOVE** from `users` group | Blocks cluster AND SQL warehouse creation |
| Allow pool creation | `allow-instance-pool-create` | **Verify NOT assigned** to `users` group | Blocks instance pool creation |
| Workspace access | `workspace-access` | **KEEP** on `users` group | Required for notebooks and Mosaic AI |
| Databricks SQL access | `databricks-sql-access` | **KEEP** on `users` group | Required for Genie and SQL features |

### Step 3: Grant Unity Catalog privileges

```sql
-- Read-only access to all lab data
GRANT USE CATALOG ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;
GRANT USE SCHEMA ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;
GRANT SELECT ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;
GRANT READ VOLUME ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;
GRANT BROWSE ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;

-- MCP connection for AgentBricks (Lab 7)
GRANT USE CONNECTION ON CONNECTION `neo4j_mcp` TO `workshop-users`;
```

### Step 4: Grant compute ACLs

| Resource | Permission | How |
|---|---|---|
| Workshop cluster (`Small Spark 4.0`) | `CAN ATTACH TO` | Compute > kebab menu > Edit permissions |
| Starter Warehouse (serverless) | `CAN USE` | SQL Warehouses > kebab menu > Permissions |

### Step 5: Verify Foundation Model API access

Foundation Model endpoints (`databricks-bge-large-en`, `databricks-meta-llama-3-3-70b-instruct`) are system endpoints accessible to all workspace users by default. Verify no AI Gateway restrictions are blocking `workshop-users`.

---

## 1. Workspace Entitlements

Entitlements are workspace-level flags that control what categories of resources a user can create. They are assigned to **groups** (not individual users).

### Why entitlement lockdowns target `users`, not `workshop-users`

Databricks automatically adds every workspace user to the built-in **`users`** group. This membership is immutable — you cannot remove a user from it. Because entitlements are **inherited from all groups a user belongs to**, a user who is in both `users` and `workshop-users` gets the **union** of entitlements from both groups.

This means:
- Removing `allow-cluster-create` from `workshop-users` has **no effect** if `users` still has it
- The lockdown **must** happen on `users` to actually restrict participants
- The `workshop-users` group is used only for **positive grants** (UC privileges, compute ACLs, etc.)

> **Shared workspace note:** Removing entitlements from `users` affects all non-admin users workspace-wide. If other teams share this workspace and need cluster creation rights, grant `allow-cluster-create` to a dedicated group for those teams.

### Entitlements to REMOVE from the `users` group

#### `allow-cluster-create`

This single entitlement controls creation of **both** clusters and SQL warehouses. Removing it prevents participants from:

- Creating all-purpose clusters
- Creating job clusters
- Creating SQL warehouses (classic, pro, or serverless)

**UI path:** Settings > Identity and access > Groups > `users` > Entitlements > uncheck "Allow unrestricted cluster creation"

**API (SCIM PATCH):**

```bash
# Get the group ID for 'users' first
USERS_GROUP_ID=$(databricks groups list --output json | jq -r '.Resources[] | select(.displayName=="users") | .id')

# Remove the entitlement
curl -X PATCH \
  "https://${DATABRICKS_HOST}/api/2.0/preview/scim/v2/Groups/${USERS_GROUP_ID}" \
  -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
  -H "Content-type: application/scim+json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [
      {
        "op": "remove",
        "path": "entitlements[value eq \"allow-cluster-create\"]"
      }
    ]
  }'
```

#### `allow-instance-pool-create` — Verify not assigned

By default, non-admin users do NOT have this. Verify it is not on the `users` group.

**UI path:** Settings > Identity and access > Groups > `users` > Entitlements > confirm "Allow pool creation" is unchecked

**API (same SCIM PATCH pattern):**

```bash
curl -X PATCH \
  "https://${DATABRICKS_HOST}/api/2.0/preview/scim/v2/Groups/${USERS_GROUP_ID}" \
  -H "Content-type: application/scim+json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [
      {
        "op": "remove",
        "path": "entitlements[value eq \"allow-instance-pool-create\"]"
      }
    ]
  }'
```

### Entitlements to KEEP

| Entitlement | API Name | Why Needed |
|---|---|---|
| Workspace access | `workspace-access` | Labs 5-6: run notebooks, use Mosaic AI features |
| Databricks SQL access | `databricks-sql-access` | Lab 7: create Genie Spaces, run SQL queries |

> **Note:** Workspace admins always retain `allow-cluster-create` and `allow-instance-pool-create` — these cannot be removed from the `admins` group. Do not make workshop participants workspace admins.

### Two-group model summary

| Group | Purpose | Entitlements | UC Grants | Compute ACLs |
|---|---|---|---|---|
| `users` (built-in) | Lockdown target | `workspace-access`, `databricks-sql-access` only — remove `allow-cluster-create` and `allow-instance-pool-create` | None | None |
| `workshop-users` (custom) | Positive grants | Inherits from `users` | `USE CATALOG`, `SELECT`, `READ VOLUME`, `USE CONNECTION`, etc. | `CAN ATTACH TO` cluster, `CAN USE` warehouse |

---

## 2. Unity Catalog Grants

All data access is read-only. Users read CSV files from volumes and query lakehouse tables — they never write to Unity Catalog.

### Catalog-Level Grants (recommended — covers all schemas)

```sql
-- Required: navigate the catalog
GRANT USE CATALOG ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;

-- Required: navigate all schemas (lab-schema + lakehouse)
GRANT USE SCHEMA ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;

-- Required: read tables in lakehouse schema (Labs 5, 7)
GRANT SELECT ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;

-- Required: read CSV/MD files from volume (Labs 5, 6)
GRANT READ VOLUME ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;

-- Optional: lets users browse metadata in Catalog Explorer
GRANT BROWSE ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;
```

### Schema-Level Grants (alternative — finer control)

If you prefer granting at the schema level instead of the catalog level:

```sql
-- Navigate the catalog
GRANT USE CATALOG ON CATALOG `aws-databricks-neo4j-lab` TO `workshop-users`;

-- Lab data volume (Labs 5, 6): CSV files + maintenance manuals
GRANT USE SCHEMA ON SCHEMA `aws-databricks-neo4j-lab`.`lab-schema` TO `workshop-users`;
GRANT READ VOLUME ON VOLUME `aws-databricks-neo4j-lab`.`lab-schema`.`lab-volume` TO `workshop-users`;

-- Lakehouse tables (Lab 7 Genie): aircraft, systems, sensors, sensor_readings
GRANT USE SCHEMA ON SCHEMA `aws-databricks-neo4j-lab`.`lakehouse` TO `workshop-users`;
GRANT SELECT ON SCHEMA `aws-databricks-neo4j-lab`.`lakehouse` TO `workshop-users`;
```

### MCP Connection Grant (Lab 7B)

```sql
-- Required for AgentBricks Neo4j sub-agent
GRANT USE CONNECTION ON CONNECTION `neo4j_mcp` TO `workshop-users`;
```

### Resources Accessed by Lab

| Lab | Resource | Type | Privilege |
|---|---|---|---|
| Lab 5.1 | `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/*.csv` | Volume files | `READ VOLUME` |
| Lab 5.2 | `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/*.csv` | Volume files | `READ VOLUME` |
| Lab 6.3 | `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/MAINTENANCE_A320.md` | Volume file | `READ VOLUME` |
| Lab 6.4 | (no UC data — queries Neo4j only) | — | — |
| Lab 6.5 | (no UC data — queries Neo4j only) | — | — |
| Lab 7A | `lakehouse.aircraft`, `.systems`, `.sensors`, `.sensor_readings` | Tables | `SELECT` |
| Lab 7B | `neo4j_mcp` connection | UC Connection | `USE CONNECTION` |

> **Important:** Do NOT grant `WRITE VOLUME`, `CREATE TABLE`, `CREATE SCHEMA`, or `ALL PRIVILEGES`. Users should have strictly read-only data access.

---

## 3. Cluster Permissions

The workshop uses a single pre-created cluster: `Small Spark 4.0` (single-node, Dedicated access mode, with Neo4j Spark Connector pre-installed).

### Grant `CAN ATTACH TO`

This is the **minimum** permission level. Users can attach notebooks and run code but cannot restart, terminate, resize, or modify the cluster.

| Permission Level | Attach Notebook | View Spark UI | Terminate | Restart | Edit | Manage |
|---|---|---|---|---|---|---|
| **CAN ATTACH TO** | Yes | Yes | No | No | No | No |
| CAN RESTART | Yes | Yes | Yes | Yes | No | No |
| CAN MANAGE | Yes | Yes | Yes | Yes | Yes | Yes |

**UI path:** Compute > click kebab menu on `Small Spark 4.0` > Edit permissions > Add `workshop-users` with `Can Attach To`

**API:**

```bash
# Get cluster ID
CLUSTER_ID=$(databricks clusters list --output json | jq -r '.clusters[] | select(.cluster_name=="Small Spark 4.0") | .cluster_id')

# Grant CAN_ATTACH_TO
curl -X PATCH \
  "https://${DATABRICKS_HOST}/api/2.0/permissions/clusters/${CLUSTER_ID}" \
  -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "access_control_list": [
      {
        "group_name": "workshop-users",
        "permission_level": "CAN_ATTACH_TO"
      }
    ]
  }'
```

### Cluster Access Mode Caveat

The cluster uses **Dedicated (Single User)** access mode, which is required by the Neo4j Spark Connector. In Dedicated mode, only one user can use the cluster at a time. For a multi-user workshop, you have two options:

1. **One cluster per user** — Admin pre-creates clusters, grants `CAN ATTACH TO` per user
2. **Shared cluster** — Use `Shared` access mode (but Neo4j Spark Connector in Lab 5.1 won't work; Lab 5.2 Python driver will still work)

> **Recommendation:** For workshops with many users, consider creating one cluster per user via the setup automation, or skip Lab 5.1 (Spark Connector) and only run Lab 5.2 (Python neo4j driver, which works on Shared clusters).

---

## 4. SQL Warehouse Permissions

Genie Spaces and lakehouse queries require a SQL warehouse. The setup creates/uses a `Starter Warehouse` (serverless).

### Grant `CAN USE`

| Permission Level | Start | View Details | Run Queries | Stop | Edit | Manage |
|---|---|---|---|---|---|---|
| **CAN USE** | Yes | Yes | Yes | No | No | No |
| CAN MONITOR | Yes | Yes | Yes (view only) | No | No | No |
| CAN MANAGE | Yes | Yes | Yes | Yes | Yes | Yes |

**UI path:** SQL Warehouses > click kebab menu on `Starter Warehouse` > Permissions > Add `workshop-users` with `Can use`

**API:**

```bash
# Get warehouse ID
WAREHOUSE_ID=$(databricks warehouses list --output json | jq -r '.warehouses[] | select(.name=="Starter Warehouse") | .id')

# Grant CAN_USE
curl -X PATCH \
  "https://${DATABRICKS_HOST}/api/2.0/permissions/sql/warehouses/${WAREHOUSE_ID}" \
  -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "access_control_list": [
      {
        "group_name": "workshop-users",
        "permission_level": "CAN_USE"
      }
    ]
  }'
```

### Creation Prevention

SQL warehouse creation is blocked by the same `allow-cluster-create` entitlement removed in [Section 1](#1-workspace-entitlements). No separate entitlement exists for SQL warehouses. Non-admin users without `allow-cluster-create` cannot create any SQL warehouses.

---

## 5. Foundation Model API Access

Labs 6.3–6.5 use Databricks Foundation Model APIs (pay-per-token) via the MLflow deployments client:

| Endpoint | Purpose | Labs |
|---|---|---|
| `databricks-bge-large-en` | Text embeddings (1024 dims) | 6.3, 6.4, 6.5 |
| `databricks-meta-llama-3-3-70b-instruct` | LLM responses | 6.4, 6.5 |

### Default Access

Foundation Model API endpoints are **system endpoints** available to all workspace users by default. No explicit grants are needed unless an AI Gateway policy restricts access.

### If Restrictions Are Applied

If AI Gateway rate limits or permissions have been configured on these endpoints, grant `CAN QUERY`:

**UI path:** Serving > click endpoint > Permissions > Add `workshop-users` with `Can query`

**API:**

```bash
# Grant CAN_QUERY on a serving endpoint
curl -X PATCH \
  "https://${DATABRICKS_HOST}/api/2.0/permissions/serving-endpoints/<endpoint-id>" \
  -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "access_control_list": [
      {
        "group_name": "workshop-users",
        "permission_level": "CAN_QUERY"
      }
    ]
  }'
```

### Authentication

When running inside Databricks notebooks, authentication to Foundation Model APIs is automatic — no tokens or API keys needed.

---

## 6. Genie Space Permissions

Lab 7A has participants **create** their own Genie Space over the lakehouse tables.

### Requirements to Create a Genie Space

| Requirement | How to Grant |
|---|---|
| `databricks-sql-access` entitlement | Keep on `users` group (default) |
| `CAN USE` on a pro or serverless SQL warehouse | Grant on `Starter Warehouse` ([Section 4](#4-sql-warehouse-permissions)) |
| `SELECT` on target tables | Grant via Unity Catalog ([Section 2](#2-unity-catalog-grants)) |

### Genie Space ACLs

Once a participant creates a Genie Space, they are its owner (`CAN MANAGE`). To share with other users:

| Permission | Ask Questions | Edit Instructions | Manage/Delete |
|---|---|---|---|
| CAN VIEW / CAN RUN | Yes | No | No |
| CAN EDIT | Yes | Yes | No |
| CAN MANAGE | Yes | Yes | Yes |

### End-User Data Access

Genie Space queries run using the author's embedded warehouse credentials. However, end users must still have `SELECT` on the underlying tables — Genie enforces row/column-level security based on the querying user's privileges.

---

## 7. AgentBricks Permissions

Lab 7B has participants **create** a Multi-Agent Supervisor with a Genie sub-agent and a Neo4j MCP sub-agent.

### Workspace Prerequisites (Admin)

These must be enabled before the workshop:

| Setting | UI Path |
|---|---|
| Mosaic AI Agent Bricks Preview | Settings > Previews > Agent Bricks |
| Production monitoring for MLflow | Settings > Previews |
| Agent Framework: On-Behalf-Of-User Authorization | Settings > Previews |
| Serverless compute | Already enabled if using serverless warehouses |
| `system.ai` schema access | Available by default in Unity Catalog |

### User Permissions for Creating Agents

| Requirement | How to Grant |
|---|---|
| `workspace-access` entitlement | Keep on `users` group (default) |
| Access to Mosaic AI Model Serving | Enabled by `workspace-access` |
| `SELECT` on Unity Catalog tables | Granted in [Section 2](#2-unity-catalog-grants) |
| `USE CONNECTION` on MCP connection | Granted in [Section 2](#2-unity-catalog-grants) |
| Serverless budget policy with nonzero budget | Admin assigns a budget policy |

### Sub-Agent Permission Requirements

| Sub-Agent Type | Required User Permission |
|---|---|
| Genie Space (Sensor Analyst) | User has `SELECT` on lakehouse tables + Genie space access |
| External MCP Server (Neo4j) | `USE CONNECTION` on the UC connection |
| Agent endpoint (other agents) | `CAN QUERY` on the serving endpoint |
| Unity Catalog function | `EXECUTE` on the function |

### Sharing Agents

After a participant creates a supervisor agent, they can share it:

| Permission | Description |
|---|---|
| CAN MANAGE | Full control: edit config, set permissions, improve quality |
| CAN QUERY | Query the agent via Playground and API only |

---

## 8. Serverless Compute

Genie and AgentBricks both use serverless compute under the hood. There is no separate entitlement for serverless access — it is controlled indirectly.

### Serverless SQL (Genie)

Users with `CAN USE` on a serverless SQL warehouse can run queries. The Genie space author's warehouse credentials handle execution for Genie consumers.

### Serverless Notebooks

Any user with the `workspace-access` entitlement can attach to serverless notebook compute. There is **no way to selectively disable** serverless notebooks for specific users. To control costs, use **serverless budget policies**.

### Serverless Budget Policies

AgentBricks requires a serverless budget policy with a nonzero budget. Admins should:

1. Create a budget policy (Settings > Compute > Budget policies)
2. Assign it to the `workshop-users` group
3. Set an appropriate spending limit for the workshop duration

> **Cost Caveat:** Serverless notebook compute is available to all users with `workspace-access`. If you want to prevent uncontrolled serverless usage, set tight budget policies or communicate expectations to participants.

---

## 9. Admin Verification

After applying all permissions, verify the setup by impersonating a workshop user (or having a test user try these steps):

### Verification Checklist

| Check | Expected Result |
|---|---|
| Navigate to Compute page | Can see `Small Spark 4.0`, no "Create" button works |
| Attach a notebook to cluster | Succeeds with `CAN ATTACH TO` |
| Try to create a new cluster | **Blocked** — no permission |
| Try to create a SQL warehouse | **Blocked** — no permission |
| Try to create an instance pool | **Blocked** — no permission |
| Browse `aws-databricks-neo4j-lab` catalog | Can see schemas and tables |
| `SELECT * FROM lakehouse.aircraft LIMIT 5` | Returns 5 rows |
| `CREATE TABLE lakehouse.test (id INT)` | **Denied** — no `CREATE TABLE` privilege |
| Read files from lab-volume | Can read CSVs and markdown files |
| Query `databricks-bge-large-en` endpoint | Returns embeddings |
| Query `databricks-meta-llama-3-3-70b-instruct` | Returns LLM response |
| Create a Genie Space over lakehouse tables | Succeeds |
| Create an AgentBricks supervisor | Succeeds |
| `USE CONNECTION neo4j_mcp` | Succeeds |

### Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| User can't see the catalog | Missing `USE CATALOG` grant | Run `GRANT USE CATALOG ON CATALOG ...` |
| User can't read volume files | Missing `READ VOLUME` grant | Run `GRANT READ VOLUME ON VOLUME ...` |
| User can't query tables | Missing `SELECT` or `USE SCHEMA` | Run grants at schema or catalog level |
| User can still create clusters | `allow-cluster-create` still on `users` group | Remove the entitlement |
| Foundation Model API returns 403 | AI Gateway restriction | Grant `CAN QUERY` on the serving endpoint |
| AgentBricks creation fails | Missing serverless budget policy or preview not enabled | Check admin settings and budget policies |
| Genie Space creation fails | Missing `databricks-sql-access` or warehouse access | Verify entitlement and `CAN USE` on warehouse |

---

## Permission Summary Matrix

| Resource | Permission Granted | Prevents |
|---|---|---|
| **Entitlements** | | |
| `allow-cluster-create` | REMOVED | Cluster + SQL warehouse creation |
| `allow-instance-pool-create` | NOT ASSIGNED | Pool creation |
| `workspace-access` | KEPT | — |
| `databricks-sql-access` | KEPT | — |
| **Unity Catalog** | | |
| Catalog `aws-databricks-neo4j-lab` | `USE CATALOG`, `USE SCHEMA`, `SELECT`, `READ VOLUME`, `BROWSE` | No `CREATE`, `MODIFY`, `WRITE VOLUME` |
| Connection `neo4j_mcp` | `USE CONNECTION` | No `CREATE CONNECTION` |
| **Compute** | | |
| Cluster `Small Spark 4.0` | `CAN ATTACH TO` | No restart, terminate, edit |
| SQL Warehouse `Starter Warehouse` | `CAN USE` | No stop, edit, delete |
| **AI/ML** | | |
| Foundation Model endpoints | Default access (or `CAN QUERY`) | — |
| Genie Spaces | Users create their own | — |
| AgentBricks supervisors | Users create their own | — |
