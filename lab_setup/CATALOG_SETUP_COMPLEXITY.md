# Unity Catalog Setup: Default Storage Limitation

When Databricks accounts have **Default Storage** enabled (the default for newer workspaces), catalog creation is **UI-only**. The CLI, REST API, and SQL Statement Execution API all fail with the same error:

```
Metastore storage root URL does not exist. Default Storage is enabled in your account.
Please use the UI to create a catalog with Default Storage.
```

We tested all three approaches and confirmed they all fail:

| Method | Command | Result |
|--------|---------|--------|
| CLI | `databricks catalogs create "my-catalog"` | FAILED |
| REST API | `POST /api/2.1/unity-catalog/catalogs` | FAILED |
| SQL via Statement Execution API | `CREATE CATALOG IF NOT EXISTS ...` | FAILED |

Databricks explicitly blocks programmatic catalog creation against the managed Default Storage location. Only the UI has the special handling to assign Default Storage to a new catalog.

---

## What Works: Create the Catalog via UI

1. Go to **Databricks UI** > **Data** > **Catalogs** > **Create Catalog**
2. Name it `aws-databricks-neo4j-lab`
3. Click **Create**

Once the catalog exists, `setup_databricks.sh` handles everything else (schema, volume, file uploads) programmatically.

---

## Alternative: Explicit Storage Root (Bypasses Default Storage)

If you provide your own cloud storage location, you bypass Default Storage entirely and catalog creation works from the CLI. This requires setting up a storage credential and external location first.

### AWS: S3

#### Prerequisites

1. **S3 Bucket** for managed storage (e.g., `s3://my-databricks-managed/catalogs`)
2. **IAM Role** with access to the bucket:
   - `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`
   - `s3:ListBucket`, `s3:GetBucketLocation`

#### CLI Steps

```bash
# 1. Create storage credential (references an IAM role ARN)
databricks storage-credentials create "workshop-cred" \
    --json '{"aws_iam_role": {"role_arn": "arn:aws:iam::123456789012:role/databricks-storage-role"}}'

# 2. Create external location
databricks external-locations create "workshop-storage" \
    "s3://my-databricks-managed/catalogs" "workshop-cred"

# 3. Grant privilege
databricks grants update EXTERNAL_LOCATION "workshop-storage" \
    --json '{"changes": [{"principal": "your-user@example.com", "add": ["CREATE_MANAGED_STORAGE"]}]}'

# 4. Create catalog with explicit storage root
databricks catalogs create "aws-databricks-neo4j-lab" \
    --storage-root "s3://my-databricks-managed/catalogs"
```

### Azure: ADLS Gen2

#### Prerequisites

1. **ADLS Gen2 Storage Account** with a container
2. **Azure Access Connector** — created in the Azure portal with a system-assigned managed identity
3. **RBAC Role Assignment** — the Access Connector's managed identity needs **Storage Blob Data Contributor** role on the ADLS Gen2 container

#### CLI Steps

```bash
# 1. Create storage credential (references an Azure Access Connector resource ID)
databricks storage-credentials create "workshop-cred" \
    --json '{"azure_managed_identity": {"access_connector_id": "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Databricks/accessConnectors/<connector-name>"}}'

# 2. Create external location
databricks external-locations create "workshop-storage" \
    "abfss://managed@mystorageaccount.dfs.core.windows.net/catalogs" "workshop-cred"

# 3. Grant privilege
databricks grants update EXTERNAL_LOCATION "workshop-storage" \
    --json '{"changes": [{"principal": "your-user@example.com", "add": ["CREATE_MANAGED_STORAGE"]}]}'

# 4. Create catalog with explicit storage root
databricks catalogs create "aws-databricks-neo4j-lab" \
    --storage-root "abfss://managed@mystorageaccount.dfs.core.windows.net/catalogs"
```

---

## Comparison

| | UI (Default Storage) | Explicit Storage Root (AWS) | Explicit Storage Root (Azure) |
|---|---|---|---|
| **Cloud infra** | None | S3 bucket + IAM role + policy | ADLS Gen2 + Access Connector + RBAC |
| **Databricks setup** | None | Storage credential + external location + grants | Storage credential + external location + grants |
| **Automatable** | No (UI only) | Yes | Yes |
| **Complexity** | Trivial | High | High |

---

## Recommendation

Create the catalog once via the UI. It only needs to happen once per workshop environment. The `setup_databricks.sh` script checks for the catalog and gives a clear error if it's missing. Everything after catalog creation (schema, volume, file uploads) is fully automated.

---

## References

- [Specify a managed storage location (AWS)](https://docs.databricks.com/aws/en/connect/unity-catalog/cloud-storage/managed-storage)
- [Specify a managed storage location (Azure)](https://learn.microsoft.com/en-us/azure/databricks/connect/unity-catalog/cloud-storage/managed-storage)
- [Create catalogs (Azure)](https://learn.microsoft.com/en-us/azure/databricks/catalogs/create-catalog)
- [CREATE CATALOG SQL reference](https://learn.microsoft.com/en-us/azure/databricks/sql/language-manual/sql-ref-syntax-ddl-create-catalog)
- [Create external locations (Azure)](https://learn.microsoft.com/en-us/azure/databricks/connect/unity-catalog/cloud-storage/external-locations)
