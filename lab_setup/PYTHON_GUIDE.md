# Python Guide: Databricks User, Group & Permission Management

Automate workshop participant onboarding using the Databricks SCIM API and Permissions API from Python. This guide uses the `requests` library for direct API calls — the same operations shown in [PERMS.md](../PERMS.md) but wrapped in reusable Python functions.

---

## Prerequisites

```bash
pip install requests python-dotenv
```

Set environment variables (or use a `.env` file):

```bash
DATABRICKS_HOST="https://<workspace>.cloud.databricks.com"
DATABRICKS_TOKEN="dapi..."
```

## Setup

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ["DATABRICKS_HOST"].rstrip("/")
TOKEN = os.environ["DATABRICKS_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/scim+json",
}

JSON_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

SCIM_BASE = f"{HOST}/api/2.0/preview/scim/v2"
```

---

## 1. Create Users

### Single user

```python
def create_user(email: str, display_name: str | None = None) -> dict:
    """Create a workspace user. Returns the SCIM user object."""
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": email,
    }
    if display_name:
        payload["displayName"] = display_name

    resp = requests.post(f"{SCIM_BASE}/Users", headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()
```

### Bulk create from a list

```python
def create_users_bulk(emails: list[str]) -> dict[str, str]:
    """Create multiple users. Returns {email: user_id} mapping.

    Skips users that already exist (HTTP 409).
    """
    results = {}
    for email in emails:
        resp = requests.post(
            f"{SCIM_BASE}/Users",
            headers=HEADERS,
            json={
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": email,
            },
        )
        if resp.status_code == 409:
            # User already exists — look them up
            existing = get_user_by_email(email)
            if existing:
                results[email] = existing["id"]
                print(f"  EXISTS  {email} (id={existing['id']})")
            continue

        resp.raise_for_status()
        user = resp.json()
        results[email] = user["id"]
        print(f"  CREATED {email} (id={user['id']})")

    return results
```

### Look up an existing user

```python
def get_user_by_email(email: str) -> dict | None:
    """Find a user by email. Returns the SCIM user object or None."""
    resp = requests.get(
        f"{SCIM_BASE}/Users",
        headers=HEADERS,
        params={"filter": f'userName eq "{email}"'},
    )
    resp.raise_for_status()
    resources = resp.json().get("Resources", [])
    return resources[0] if resources else None
```

---

## 2. Create and Manage Groups

### Create a group

```python
def create_group(name: str, entitlements: list[str] | None = None) -> dict:
    """Create a workspace group with optional entitlements.

    Common entitlements:
        - "workspace-access"
        - "databricks-sql-access"
        - "allow-cluster-create"
        - "allow-instance-pool-create"
    """
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": name,
    }
    if entitlements:
        payload["entitlements"] = [{"value": e} for e in entitlements]

    resp = requests.post(f"{SCIM_BASE}/Groups", headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()
```

### Look up a group by name

```python
def get_group_by_name(name: str) -> dict | None:
    """Find a group by display name. Returns the SCIM group object or None."""
    resp = requests.get(
        f"{SCIM_BASE}/Groups",
        headers=HEADERS,
        params={"filter": f'displayName eq "{name}"'},
    )
    resp.raise_for_status()
    resources = resp.json().get("Resources", [])
    return resources[0] if resources else None
```

### Add users to a group

```python
def add_users_to_group(group_id: str, user_ids: list[str]) -> None:
    """Add multiple users to a group in a single PATCH request."""
    resp = requests.patch(
        f"{SCIM_BASE}/Groups/{group_id}",
        headers=HEADERS,
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "add",
                    "path": "members",
                    "value": [{"value": uid} for uid in user_ids],
                }
            ],
        },
    )
    resp.raise_for_status()
```

### Remove users from a group

```python
def remove_user_from_group(group_id: str, user_id: str) -> None:
    """Remove a single user from a group."""
    resp = requests.patch(
        f"{SCIM_BASE}/Groups/{group_id}",
        headers=HEADERS,
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "remove",
                    "path": f'members[value eq "{user_id}"]',
                }
            ],
        },
    )
    resp.raise_for_status()
```

---

## 3. Manage Entitlements

Entitlements are workspace-level flags on groups that control resource creation rights.

### Add an entitlement to a group

```python
def add_entitlement(group_id: str, entitlement: str) -> None:
    """Add an entitlement to a group.

    Args:
        entitlement: One of "workspace-access", "databricks-sql-access",
                     "allow-cluster-create", "allow-instance-pool-create".
    """
    resp = requests.patch(
        f"{SCIM_BASE}/Groups/{group_id}",
        headers=HEADERS,
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "add",
                    "path": "entitlements",
                    "value": [{"value": entitlement}],
                }
            ],
        },
    )
    resp.raise_for_status()
```

### Remove an entitlement from a group

```python
def remove_entitlement(group_id: str, entitlement: str) -> None:
    """Remove an entitlement from a group."""
    resp = requests.patch(
        f"{SCIM_BASE}/Groups/{group_id}",
        headers=HEADERS,
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "remove",
                    "path": f'entitlements[value eq "{entitlement}"]',
                }
            ],
        },
    )
    resp.raise_for_status()
```

---

## 4. Object-Level Permissions

These APIs control access to specific resources (clusters, warehouses, directories). They use the standard Permissions API, not SCIM.

### Cluster permissions

```python
def grant_cluster_permission(
    cluster_id: str,
    group_name: str,
    permission: str = "CAN_ATTACH_TO",
) -> None:
    """Grant a group permission on a cluster.

    Permission levels: CAN_ATTACH_TO, CAN_RESTART, CAN_MANAGE.
    """
    resp = requests.patch(
        f"{HOST}/api/2.0/permissions/clusters/{cluster_id}",
        headers=JSON_HEADERS,
        json={
            "access_control_list": [
                {"group_name": group_name, "permission_level": permission}
            ]
        },
    )
    resp.raise_for_status()
```

### SQL warehouse permissions

```python
def grant_warehouse_permission(
    warehouse_id: str,
    group_name: str,
    permission: str = "CAN_USE",
) -> None:
    """Grant a group permission on a SQL warehouse.

    Permission levels: CAN_USE, CAN_MONITOR, CAN_MANAGE, IS_OWNER.
    """
    resp = requests.patch(
        f"{HOST}/api/2.0/permissions/sql/warehouses/{warehouse_id}",
        headers=JSON_HEADERS,
        json={
            "access_control_list": [
                {"group_name": group_name, "permission_level": permission}
            ]
        },
    )
    resp.raise_for_status()
```

### Directory / folder permissions

```python
def grant_directory_permission(
    directory_id: str,
    group_name: str,
    permission: str = "CAN_RUN",
) -> None:
    """Grant a group permission on a workspace directory.

    Permission levels: CAN_READ, CAN_RUN, CAN_EDIT, CAN_MANAGE.
    """
    resp = requests.patch(
        f"{HOST}/api/2.0/permissions/directories/{directory_id}",
        headers=JSON_HEADERS,
        json={
            "access_control_list": [
                {"group_name": group_name, "permission_level": permission}
            ]
        },
    )
    resp.raise_for_status()
```

### Serving endpoint permissions (Foundation Model APIs)

```python
def grant_serving_endpoint_permission(
    endpoint_id: str,
    group_name: str,
    permission: str = "CAN_QUERY",
) -> None:
    """Grant a group permission on a model serving endpoint.

    Permission levels: CAN_QUERY, CAN_MANAGE.
    """
    resp = requests.patch(
        f"{HOST}/api/2.0/permissions/serving-endpoints/{endpoint_id}",
        headers=JSON_HEADERS,
        json={
            "access_control_list": [
                {"group_name": group_name, "permission_level": permission}
            ]
        },
    )
    resp.raise_for_status()
```

---

## 5. Unity Catalog Grants (SQL)

UC privileges are granted via SQL statements executed against a SQL warehouse.

```python
def execute_sql(warehouse_id: str, statement: str) -> dict:
    """Execute a SQL statement on a warehouse and wait for the result."""
    resp = requests.post(
        f"{HOST}/api/2.0/sql/statements",
        headers=JSON_HEADERS,
        json={
            "warehouse_id": warehouse_id,
            "statement": statement,
            "wait_timeout": "30s",
        },
    )
    resp.raise_for_status()
    return resp.json()


def grant_uc_privileges(warehouse_id: str, group_name: str) -> None:
    """Grant all workshop Unity Catalog privileges to a group."""
    grants = [
        f"GRANT USE CATALOG ON CATALOG `aws-databricks-neo4j-lab` TO `{group_name}`",
        f"GRANT USE SCHEMA ON CATALOG `aws-databricks-neo4j-lab` TO `{group_name}`",
        f"GRANT SELECT ON CATALOG `aws-databricks-neo4j-lab` TO `{group_name}`",
        f"GRANT READ VOLUME ON CATALOG `aws-databricks-neo4j-lab` TO `{group_name}`",
        f"GRANT BROWSE ON CATALOG `aws-databricks-neo4j-lab` TO `{group_name}`",
        f"GRANT USE CONNECTION ON CONNECTION `neo4j_mcp` TO `{group_name}`",
    ]
    for sql in grants:
        result = execute_sql(warehouse_id, sql)
        status = result.get("status", {}).get("state", "UNKNOWN")
        print(f"  {status}: {sql}")
```

---

## 6. Helper: List Resources

Useful for finding cluster IDs, warehouse IDs, etc.

```python
def list_clusters() -> list[dict]:
    """List all clusters. Returns list of cluster dicts."""
    resp = requests.get(f"{HOST}/api/2.0/clusters/list", headers=JSON_HEADERS)
    resp.raise_for_status()
    return resp.json().get("clusters", [])


def find_cluster_id(name: str) -> str | None:
    """Find a cluster ID by name."""
    for c in list_clusters():
        if c["cluster_name"] == name:
            return c["cluster_id"]
    return None


def list_warehouses() -> list[dict]:
    """List all SQL warehouses."""
    resp = requests.get(f"{HOST}/api/2.0/sql/warehouses", headers=JSON_HEADERS)
    resp.raise_for_status()
    return resp.json().get("warehouses", [])


def find_warehouse_id(name: str) -> str | None:
    """Find a warehouse ID by name."""
    for w in list_warehouses():
        if w["name"] == name:
            return w["id"]
    return None
```

---

## 7. Full Workshop Onboarding Script

Ties everything together. Creates users, creates a group, assigns permissions, and grants UC privileges.

```python
def onboard_workshop(emails: list[str]) -> None:
    """Full workshop onboarding: users, group, permissions, UC grants."""

    GROUP_NAME = "workshop-users"
    CLUSTER_NAME = "Small Spark 4.0"
    WAREHOUSE_NAME = "Starter Warehouse"

    # --- Step 1: Create users ---
    print("Creating users...")
    user_map = create_users_bulk(emails)
    print(f"  {len(user_map)} users ready\n")

    # --- Step 2: Create or get the workshop group ---
    print(f"Setting up group '{GROUP_NAME}'...")
    group = get_group_by_name(GROUP_NAME)
    if group:
        group_id = group["id"]
        print(f"  Group already exists (id={group_id})")
    else:
        group = create_group(GROUP_NAME)
        group_id = group["id"]
        print(f"  Created group (id={group_id})")

    # --- Step 3: Add users to group ---
    print("Adding users to group...")
    add_users_to_group(group_id, list(user_map.values()))
    print(f"  Added {len(user_map)} users\n")

    # --- Step 4: Lock down the built-in 'users' group ---
    print("Locking down 'users' group entitlements...")
    users_group = get_group_by_name("users")
    if users_group:
        remove_entitlement(users_group["id"], "allow-cluster-create")
        print("  Removed 'allow-cluster-create' from 'users'")
        remove_entitlement(users_group["id"], "allow-instance-pool-create")
        print("  Removed 'allow-instance-pool-create' from 'users'\n")

    # --- Step 5: Grant compute permissions ---
    print("Granting compute permissions...")

    cluster_id = find_cluster_id(CLUSTER_NAME)
    if cluster_id:
        grant_cluster_permission(cluster_id, GROUP_NAME, "CAN_ATTACH_TO")
        print(f"  Cluster '{CLUSTER_NAME}': CAN_ATTACH_TO")
    else:
        print(f"  WARNING: Cluster '{CLUSTER_NAME}' not found")

    warehouse_id = find_warehouse_id(WAREHOUSE_NAME)
    if warehouse_id:
        grant_warehouse_permission(warehouse_id, GROUP_NAME, "CAN_USE")
        print(f"  Warehouse '{WAREHOUSE_NAME}': CAN_USE")
    else:
        print(f"  WARNING: Warehouse '{WAREHOUSE_NAME}' not found")

    print()

    # --- Step 6: Grant Unity Catalog privileges ---
    if warehouse_id:
        print("Granting Unity Catalog privileges...")
        grant_uc_privileges(warehouse_id, GROUP_NAME)
        print()

    # --- Done ---
    print("Onboarding complete!")
    print(f"  Users: {len(user_map)}")
    print(f"  Group: {GROUP_NAME}")
    print(f"  Cluster: {CLUSTER_NAME} (CAN_ATTACH_TO)")
    print(f"  Warehouse: {WAREHOUSE_NAME} (CAN_USE)")


# --- Run ---
if __name__ == "__main__":
    participants = [
        "participant1@example.com",
        "participant2@example.com",
        "participant3@example.com",
    ]
    onboard_workshop(participants)
```

---

## 8. Cleanup: Remove Users

```python
def delete_user(user_id: str) -> None:
    """Delete a user from the workspace."""
    resp = requests.delete(f"{SCIM_BASE}/Users/{user_id}", headers=HEADERS)
    resp.raise_for_status()


def offboard_workshop(emails: list[str]) -> None:
    """Remove workshop participants from the workspace."""
    for email in emails:
        user = get_user_by_email(email)
        if user:
            delete_user(user["id"])
            print(f"  DELETED {email}")
        else:
            print(f"  NOT FOUND {email}")
```

---

## API Reference

| Area | API | Base URL |
|---|---|---|
| Users | SCIM 2.0 | `/api/2.0/preview/scim/v2/Users` |
| Groups | SCIM 2.0 | `/api/2.0/preview/scim/v2/Groups` |
| Cluster ACLs | Permissions | `/api/2.0/permissions/clusters/{id}` |
| Warehouse ACLs | Permissions | `/api/2.0/permissions/sql/warehouses/{id}` |
| Directory ACLs | Permissions | `/api/2.0/permissions/directories/{id}` |
| Serving endpoints | Permissions | `/api/2.0/permissions/serving-endpoints/{id}` |
| UC Grants | SQL Statements | `/api/2.0/sql/statements` |

## Entitlements Reference

| Entitlement | API Value | Controls |
|---|---|---|
| Workspace access | `workspace-access` | Basic workspace and notebook access |
| Databricks SQL access | `databricks-sql-access` | SQL editor, Genie Spaces |
| Unrestricted cluster creation | `allow-cluster-create` | Cluster **and** SQL warehouse creation |
| Pool creation | `allow-instance-pool-create` | Instance pool creation |

## Permissions Levels Reference

| Resource Type | Levels (least to most) |
|---|---|
| Cluster | `CAN_ATTACH_TO` < `CAN_RESTART` < `CAN_MANAGE` |
| SQL Warehouse | `CAN_USE` < `CAN_MONITOR` < `CAN_MANAGE` < `IS_OWNER` |
| Directory | `CAN_READ` < `CAN_RUN` < `CAN_EDIT` < `CAN_MANAGE` |
| Serving Endpoint | `CAN_QUERY` < `CAN_MANAGE` |
