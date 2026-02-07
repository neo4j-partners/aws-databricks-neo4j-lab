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
- [ ] Run `databricks-setup setup` to set up compute, upload data, and create tables (Step 2)
- [ ] Configure Databricks Genie Space (Lab 7)
- [ ] Provide DBC file to participants (or host for download)
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

#### Troubleshooting Authentication

If you see a UUID instead of your email, your CLI may be configured with a service principal. Check for overriding environment variables:

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

### Python and uv

The setup CLI requires Python 3.11+ and [uv](https://docs.astral.sh/uv/):

```bash
cd lab_setup/auto_scripts
uv sync
```

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

## Step 2: Automated Setup

The `databricks-setup` CLI (in `auto_scripts/`) handles everything after catalog creation. It runs two parallel tracks:

- **Track A:** Creates a dedicated Spark cluster with the Neo4j Spark Connector and all Python libraries
- **Track B:** Uploads data files and creates Delta Lake tables via SQL Warehouse

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
```

#### All configuration options

| Variable | Description | Default |
|----------|-------------|---------|
| `WAREHOUSE_NAME` | SQL Warehouse name (for lakehouse tables) | `Starter Warehouse` |
| `WAREHOUSE_TIMEOUT` | SQL statement timeout (seconds) | `600` |
| `DATABRICKS_PROFILE` | CLI profile from ~/.databrickscfg | Default |
| `CLUSTER_NAME` | Cluster name to create or reuse | `Small Spark 4.0` |
| `USER_EMAIL` | Cluster owner email | Auto-detected |
| `SPARK_VERSION` | Databricks Runtime version | `17.3.x-cpu-ml-scala2.13` |
| `AUTOTERMINATION_MINUTES` | Cluster auto-shutdown | `30` |
| `RUNTIME_ENGINE` | `STANDARD` or `PHOTON` | `STANDARD` |
| `CLOUD_PROVIDER` | `aws` or `azure` | `aws` |
| `NODE_TYPE` | Instance type (auto-detected per cloud) | See below |
| `INSTANCE_PROFILE_ARN` | AWS IAM instance profile for cluster nodes | None |

Cloud provider defaults:

| Provider | Default Node Type | Notes |
|----------|------------------|-------|
| AWS | `m5.xlarge` | 16 GB, 4 cores, EBS volume attached |
| Azure | `Standard_D4ds_v5` | 16 GB, 4 cores |

### 2.2 Run Setup

```bash
cd lab_setup/auto_scripts
uv run databricks-setup setup [VOLUME] [OPTIONS]
```

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `VOLUME` | | Target volume (`catalog.schema.volume`) | `aws-databricks-neo4j-lab.lab-schema.lab-volume` |
| `--cluster-only` | | Only create cluster and install libraries | `false` |
| `--tables-only` | | Only upload data and create lakehouse tables | `false` |
| `--profile` | `-p` | Databricks CLI profile | From `DATABRICKS_PROFILE` env var |

Examples:

```bash
# All defaults (both tracks run in parallel)
uv run databricks-setup setup

# Cluster + libraries only
uv run databricks-setup setup --cluster-only

# Data upload + lakehouse tables only
uv run databricks-setup setup --tables-only

# Explicit volume
uv run databricks-setup setup my-catalog.my-schema.my-volume

# Use a specific Databricks CLI profile
uv run databricks-setup setup --profile my-workspace
```

### What it does

Runs two parallel tracks by default:

**Track A — Cluster + Libraries:**
1. Creates (or reuses) a single-node Spark cluster with Dedicated (Single User) access mode
2. Waits for the cluster to reach RUNNING state
3. Installs the Neo4j Spark Connector and all Python libraries

**Track B — Data Upload + Lakehouse Tables:**
1. Finds the configured SQL Warehouse
2. Uploads CSV and Markdown data files to the volume
3. Creates Delta Lake tables via the Statement Execution API

If a cluster with the same name already exists, the CLI reuses it (starting it if terminated).

### Cluster defaults

| Setting | Value |
|---------|-------|
| Runtime | 17.3 LTS ML (Spark 4.0.0, Scala 2.13) |
| Photon | Disabled (workshop data is small; Photon only benefits >100GB workloads) |
| Node type (AWS) | `m5.xlarge` (16 GB, 4 cores) |
| Node type (Azure) | `Standard_D4ds_v5` (16 GB, 4 cores) |
| Workers | 0 (single node) |
| Access mode | Dedicated (Single User) |
| Auto-terminate | 30 minutes |

To change defaults, edit `.env`.


---

### Manual Setup (UI Alternative)

If you prefer to set up the cluster, libraries, and data through the Databricks UI instead of using `databricks-setup`, see the complete step-by-step guide in **[MANUAL_SETUP.md](docs/MANUAL_SETUP.md)**.

### Cleanup

To tear down everything the setup created (lakehouse tables, volume, schemas, and catalog) while keeping the compute cluster:

```bash
cd lab_setup/auto_scripts

# Interactive confirmation
uv run databricks-setup cleanup

# Skip confirmation
uv run databricks-setup cleanup --yes
```

Each step is idempotent — safe to re-run if partially completed.

---

## Step 4: Prepare Participant Instructions

Create a handout or slide with:

### Connection Information

| Resource | Value |
|----------|-------|
| Databricks Workspace URL | `https://your-workspace.cloud.databricks.com` |
| Cluster Name | `aircraft-workshop-cluster` |
| Notebook DBC File | `aircraft_etl_to_neo4j.dbc` (provide download link) |
| Data Volume Path | `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/` |
| Genie Space ID | `{your-genie-space-id}` (for Lab 7) |

### Quick Start Instructions

1. Sign in to Databricks with your workshop credentials
2. Navigate to Compute and ensure the cluster is running
3. Download the `aircraft_etl_to_neo4j.dbc` file
4. Go to Workspace > your personal folder
5. Right-click > Import > upload the DBC file
6. Open the imported notebook
7. Enter your Neo4j credentials from Lab 1
8. Run all cells (Shift+Enter or Run All)
9. Verify the counts in the output cells

---

## Troubleshooting

### Common Issues

**"Spark Connector not found" error**
- Verify cluster is in Dedicated (Single User) mode
- Check library installation status
- Restart cluster after adding library

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
- Verify table relationships are configured (Step 3.3)
- Add more sample questions to guide the model

**Lakehouse table creation fails**
- Ensure CSV files are uploaded to the Volume first
- Check file paths match exactly
- Verify the SQL Warehouse has access to the Volume

---

## File Inventory

For the full file inventory with sizes, record counts, and sensor data details, see **[MANUAL_SETUP.md](docs/MANUAL_SETUP.md#file-inventory)**.

The setup CLI uploads **25 files** to the Volume:
- **22 CSV files** from `aircraft_digital_twin_data/` (nodes and relationships for Labs 5 and 7)
- **3 Markdown files** (maintenance manuals for Lab 6: A320, A321neo, B737)

---

## Cost Considerations

- **Cluster:** Single-node clusters are sufficient for this small dataset
- **Auto-termination:** Set to 30-60 minutes to avoid idle costs
- **Storage:** Volume storage for CSV files is negligible (~25 MB total)
- **Delta Lake:** The lakehouse tables add minimal storage overhead
- **Genie:** Genie queries consume compute resources; monitor usage during workshop

---

## Contact

For issues during workshop setup, contact the workshop organizers or refer to:
- [Neo4j Spark Connector Documentation](https://neo4j.com/docs/spark/current/)
- [Databricks Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Databricks Genie Documentation](https://docs.databricks.com/en/genie/index.html)
