# Lab Admin Setup Guide

**Purpose:** Instructions for workshop administrators to prepare the Databricks environment before participants arrive.

**Participant Materials:** To create the zip file for participants to upload to Databricks, run:

```bash
./lab_setup/prepare_material.sh
```

---


## Pre-Workshop Checklist

Complete these steps before the workshop begins:

- [ ] Create Unity Catalog, Schema, and Volume (Step 1 — UI required)
- [ ] Create `aircraft_workshop_group` at the account level and add it to the workspace (Step 1.5)
- [ ] Run `databricks-setup setup` to upload data, create tables, and lock down permissions (Step 2)
- [ ] Add participant emails to `lab_setup/users.csv` and run `databricks-setup add-users` (Step 3)
- [ ] Configure Databricks Genie Space (Lab 7)
- [ ] Test the complete workflow
- [ ] Document connection details for participants

---

## Prerequisites

### Databricks CLI Authentication

Before running any CLI commands, authenticate the Databricks CLI with your user account:

```bash
databricks auth login --host <your-workspace-url>
```

This opens a browser for OAuth login. After authenticating, verify you are logged in as your user (not a service principal):

```bash
databricks current-user me
```

You should see your email address in the output.

#### Using a Named Profile

If you have multiple Databricks profiles configured, set `DATABRICKS_PROFILE` in `.env` (see Step 2.1), or export for ad-hoc CLI commands:

```bash
export DATABRICKS_CONFIG_PROFILE=<your-profile-name>
```

### Python and uv

The CLI requires Python 3.11+ and [uv](https://docs.astral.sh/uv/):

```bash
cd lab_setup/auto_scripts && uv sync
```

### Databricks Resources

The following resources must exist before running `databricks-setup`. See details below for setup instructions.

| Resource | Name | Created In |
|----------|------|------------|
| Unity Catalog | `aws-databricks-neo4j-lab` | [Step 1.1](#11-create-a-catalog) |
| Schema | `lab-schema` | [Step 1.2](#12-create-a-schema) |
| Volume | `lab-volume` | [Step 1.3](#13-create-the-volume) |
| Account-level group | `aircraft_workshop_group` | [Step 1.5](#step-15-create-account-level-group) |

---


## Why Catalog Creation Is Manual

Newer Databricks workspaces use **Default Storage**, which blocks programmatic catalog creation via CLI, REST API, and SQL — all return the same error. Only the UI has the special handling to assign Default Storage to a new catalog. Once the catalog exists, everything else (schema, volume, compute, data upload, and table creation) is automated by `databricks-setup`. See [CATALOG_SETUP_COMPLEXITY.md](CATALOG_SETUP_COMPLEXITY.md) for details.

---

## Step 1: Create Unity Catalog and Volume (UI)

Create the catalog, schema, and volume through the Databricks UI.

### 1.1 Create a Catalog

1. Navigate to **Data** > **Catalogs** in the Databricks workspace
2. Click **Create Catalog**
3. Name it `aws-databricks-neo4j-lab` (or similar)
4. Select the appropriate metastore
5. Click **Create**

### 1.2 Create a Schema

1. Within the catalog, click **Create Schema**
2. Name it `lab-schema`
3. Click **Create**

### 1.3 Create the Volume

1. Navigate to the schema created above
2. Click **Create** > **Volume**
3. Configure:
   - **Name:** `lab-volume`
   - **Volume type:** Managed
4. Click **Create**

**Resulting path:** `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/`

### 1.4 Verify Creation (CLI)

Confirm the catalog, schema, and volume exist with one command:

```bash
databricks volumes read aws-databricks-neo4j-lab.lab-schema.lab-volume
```

This returns volume metadata if successful, or an error if any component is missing.

---

## Step 1.5: Create Account-Level Group

Unity Catalog grants only work with **account-level** groups. Workspace-local groups (created via the SDK or workspace UI) are invisible to UC and will cause `Could not find principal` errors. This group must be created once at the account level.

### 1.5.1 Create the Group in Account Admin

1. Go to [https://accounts.cloud.databricks.com](https://accounts.cloud.databricks.com) > **User management** > **Groups**
2. Click **Create group**
3. Name it `aircraft_workshop_group`
4. Click **Create**

### 1.5.2 Add the Group to the Workspace

1. In the Databricks workspace, go to **Settings** > **Identity and access** > **Groups**
2. Click **Add group**
3. Search for `aircraft_workshop_group` and add it from the account
4. Verify the group shows with **Source = "Account"**

> **Note:** This is a one-time step. The group persists across setup/cleanup cycles and is NOT deleted by `databricks-setup cleanup`.

---

## Step 2: Automated Setup

The `databricks-setup` CLI (in `auto_scripts/`) handles everything after catalog creation. It runs three sequential tracks:

- **Track A:** Creates/starts an admin cluster and installs libraries (Neo4j Spark Connector + Python packages)
- **Track B:** Uploads data files, notebooks, and creates Delta Lake tables via SQL Warehouse
- **Track C:** Locks down permissions — removes compute-creation entitlements, verifies the `aircraft_workshop_group` account-level group exists, grants read-only catalog access, and sets workspace folder read permissions

Per-user clusters are created separately in Step 3 via `databricks-setup add-users`.

### 2.1 Configure Environment

Copy the example environment file and customize:

```bash
cp lab_setup/.env.example lab_setup/.env
```

Edit `.env` and set at minimum:

```bash
# Cloud provider: "aws" or "azure"
CLOUD_PROVIDER="aws"

# Databricks CLI profile (optional - uses default if empty)
DATABRICKS_PROFILE=""

# Account ID (required for user management — found at https://accounts.cloud.databricks.com)
DATABRICKS_ACCOUNT_ID=""
```

For the full list of configuration options, see the [auto_scripts README](auto_scripts/README.md#configuration).

### 2.2 Run Setup

```bash
cd lab_setup/auto_scripts
uv run databricks-setup setup
```

All configuration is loaded from `lab_setup/.env` — there are no CLI arguments.

### What it does

Runs three tracks sequentially:

**Track A — Admin Cluster + Libraries:**
1. Creates or reuses a dedicated admin Spark cluster
2. Waits for the cluster to reach RUNNING state
3. Installs Neo4j Spark Connector and Python packages

**Track B — Data Upload + Lakehouse Tables:**
1. Finds the configured SQL Warehouse
2. Uploads CSV and Markdown data files to the volume
3. Uploads workshop notebooks to the shared workspace folder
4. Creates Delta Lake tables via the Statement Execution API

**Track C — Permissions Lockdown:**
1. Removes `allow-cluster-create` and `allow-instance-pool-create` entitlements from the built-in `users` group (blocks all non-admin users from creating compute)
2. Removes non-admin access from the Personal Compute cluster policy
3. Verifies the `aircraft_workshop_group` account-level group exists in the workspace (see Step 1.5)
4. Grants read-only Unity Catalog privileges on the lab catalog (`USE_CATALOG`, `USE_SCHEMA`, `SELECT`, `READ_VOLUME`, `BROWSE`)
5. Grants `CAN_READ` on the shared notebook folder to the `aircraft_workshop_group` group

All operations are idempotent — safe to re-run.

For configuration details (environment variables, cluster defaults, cloud provider options), see the [auto_scripts README](auto_scripts/README.md#configuration).

---

### Manual Setup (UI Alternative)

If you prefer to set up the data and permissions through the Databricks UI instead of using `databricks-setup`, see the complete step-by-step guide in **[MANUAL_SETUP.md](docs/MANUAL_SETUP.md)**.

## Step 3: Add Workshop Participants

The `databricks-setup add-users` command manages participant onboarding. It reads emails from a CSV file and for each participant:

1. Creates a workspace account if they don't already exist
2. Adds them to the `aircraft_workshop_group` group
3. Creates a dedicated per-user cluster (`lab-<email_prefix>`)
4. Waits for the cluster to start and installs all required libraries

Each participant gets their own SINGLE_USER cluster, which gives them implicit compute access without needing shared cluster ACLs. The Neo4j Spark Connector requires Dedicated (Single User) access mode.

### 3.1 Configure Account ID

Ensure `DATABRICKS_ACCOUNT_ID` is set in `lab_setup/.env`. This is required for account-level group management. Find your account ID at [https://accounts.cloud.databricks.com](https://accounts.cloud.databricks.com).

### 3.2 Prepare the CSV

Edit `lab_setup/users.csv` with participant email addresses:

```csv
email,name
alice@example.com,Alice Johnson
bob@example.com,Bob Smith
carol@example.com,Carol Williams
```

The `email` column is required. The `name` column is optional and ignored by the tool — it exists for human readability. Users that don't already exist in the workspace will be automatically created (invited via SCIM).

### 3.3 Add Users

```bash
cd lab_setup/auto_scripts
uv run databricks-setup add-users
```

This reads `lab_setup/users.csv`, creates workspace accounts, adds users to the group, creates per-user clusters (e.g., `lab-alice`, `lab-bob`), and installs libraries on each.

To add users to the group without creating clusters (e.g., if you'll create clusters later):

```bash
uv run databricks-setup add-users --skip-clusters
```

### 3.4 List Users

```bash
uv run databricks-setup list-users
```

Shows all group members with their email, display name, cluster name, and cluster state.

### 3.5 Remove Users

```bash
uv run databricks-setup remove-users
```

Removes users listed in `lab_setup/users.csv` from the group and permanently deletes their per-user clusters. To remove from the group while keeping clusters:

```bash
uv run databricks-setup remove-users --keep-clusters
```

All commands read from `lab_setup/users.csv` and use the `DATABRICKS_PROFILE` from `lab_setup/.env`.

---

## Step 4: Prepare Participant Instructions

Create a handout or slide with:

### Connection Information

| Resource | Value |
|----------|-------|
| Databricks Workspace URL | `https://your-workspace.cloud.databricks.com` |
| Data Volume Path | `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/` |
| Genie Space ID | `{your-genie-space-id}` (for Lab 7) |

### Quick Start Instructions

1. Sign in to Databricks with your workshop credentials
2. Navigate to Compute — your dedicated cluster (`lab-<your-name>`) should be running
3. Download the `aircraft_etl_to_neo4j.dbc` file
4. Go to Workspace > your personal folder
5. Right-click > Import > upload the DBC file
6. Open the imported notebook
7. Enter your Neo4j credentials from Lab 1
8. Run all cells (Shift+Enter or Run All)
9. Verify the counts in the output cells

---

## Troubleshooting

### Authentication

If you see a UUID instead of your email when running `databricks current-user me`, your CLI may be configured with a service principal. Check for overriding environment variables:

```bash
env | grep -i DATABRICKS
```

If present, unset them for interactive use:

```bash
unset DATABRICKS_TOKEN
unset DATABRICKS_CLIENT_ID
unset DATABRICKS_CLIENT_SECRET
```

Then re-run `databricks auth login`.

### Common Issues

**"Spark Connector not found" error**
- Verify the participant's cluster is in Dedicated (Single User) mode
- Check library installation status on the cluster
- Restart the cluster after adding the library

**"Connection refused" to Neo4j**
- Verify URI format: `neo4j+s://` for Aura
- Check participant's Neo4j instance is running
- Verify credentials are correct

**"Path does not exist" for Volume**
- Verify Volume path matches notebook configuration
- Check files were uploaded successfully
- Confirm participant has access to the catalog

**Duplicate nodes on re-run**
- The notebook uses Overwrite mode which should handle this
- If issues persist, have participants run cleanup query:
  ```cypher
  MATCH (n) DETACH DELETE n
  ```

**Genie not generating correct SQL**
- Ensure table comments are added (handled by `databricks-setup` CLI)
- Verify table relationships are configured in the Genie Space
- Add more sample questions to guide the model

**Lakehouse table creation fails**
- Ensure CSV files are uploaded to the Volume first
- Check file paths match exactly
- Verify the SQL Warehouse has access to the Volume

**Participant cannot create a cluster or SQL warehouse**
- This is expected — Track C removes compute-creation entitlements from all non-admin users
- Participants should use their dedicated per-user cluster (created by `add-users`)
- Admins always retain these entitlements and are not affected

**Participant cannot see the catalog or query tables**
- Verify the user is a member of the `aircraft_workshop_group` group: `uv run databricks-setup list-users`
- If not listed, add their email to `lab_setup/users.csv` and re-run `uv run databricks-setup add-users`
- Check that `databricks-setup setup` completed Track C successfully (look for "Permissions lockdown complete" in the output)
- Verify `aircraft_workshop_group` has **Source = "Account"** in Settings > Identity and access > Groups (workspace-local groups are invisible to Unity Catalog)

**Participant's cluster is not running**
- Run `uv run databricks-setup list-users` to check cluster states
- If terminated, the participant can start it from the Compute page
- Re-running `databricks-setup add-users` will restart any terminated clusters

---

## CLI Command Reference

```
databricks-setup setup                         # Create admin cluster, upload data, create tables, lock down permissions
databricks-setup cleanup [--yes]               # Delete data, tables, catalog, and revert permissions
databricks-setup add-users [--skip-clusters]   # Create users, add to group, create per-user clusters
databricks-setup remove-users [--keep-clusters] # Remove from group, delete per-user clusters
databricks-setup list-users                    # Show group members and cluster status
```

| Flag | Command | Effect |
|------|---------|--------|
| `--skip-clusters` | `add-users` | Only create accounts and add to group — skip per-user cluster creation |
| `--keep-clusters` | `remove-users` | Remove from group but keep per-user clusters running |

All user commands read from `lab_setup/users.csv`.

---

## File Inventory

For the full file inventory with sizes, record counts, and sensor data details, see **[MANUAL_SETUP.md](docs/MANUAL_SETUP.md#file-inventory)**.

The setup CLI uploads **25 files** to the Volume:
- **22 CSV files** from `aircraft_digital_twin_data/` (nodes and relationships for Labs 5 and 7)
- **3 Markdown files** (maintenance manuals for Lab 6: A320, A321neo, B737)

---

## Cost Considerations

- **Clusters:** Each participant gets a single-node cluster; plan for one m5.xlarge per user
- **Auto-termination:** Set to 30 minutes by default to avoid idle costs
- **Storage:** Volume storage for CSV files is negligible (~25 MB total)
- **Delta Lake:** The lakehouse tables add minimal storage overhead
- **Genie:** Genie queries consume compute resources; monitor usage during workshop

---

## Cleanup

To tear down data and permissions (lakehouse tables, volume, schemas, catalog, and notebook folder):

```bash
cd lab_setup/auto_scripts

# Interactive confirmation
uv run databricks-setup cleanup

# Skip confirmation
uv run databricks-setup cleanup --yes
```

To remove per-user clusters:

```bash
uv run databricks-setup remove-users
```

Cleanup revokes catalog grants for `aircraft_workshop_group` but does **not** delete the group (it is account-level and persists across setup/cleanup cycles). It also does **not** restore compute-creation entitlements on the `users` group — that is a deliberate admin action. A reminder is printed with instructions to re-add them manually if needed.

Each step is idempotent — safe to re-run if partially completed.

---

## Contact

For issues during workshop setup, contact the workshop organizers or refer to:
- [Neo4j Spark Connector Documentation](https://neo4j.com/docs/spark/current/)
- [Databricks Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Databricks Genie Documentation](https://docs.databricks.com/en/genie/index.html)
