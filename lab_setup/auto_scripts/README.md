# Databricks Setup CLI

A modular Python CLI tool for setting up and cleaning up Databricks environments for the Neo4j workshop.

For full usage instructions, configuration options, and examples, see the main [Lab Admin Setup Guide](../README.md#step-2-automated-setup).

## Quick Start

```bash
cd lab_setup/auto_scripts
uv sync

# Set up environment
uv run databricks-setup setup

# Tear down everything except the compute cluster
uv run databricks-setup cleanup
```

## Commands

### `setup`

Runs three tracks sequentially:

```
databricks-setup setup
├── Track A: Admin Cluster + Libraries
│   ├── Create or reuse dedicated admin Spark cluster
│   ├── Wait for cluster to reach RUNNING state
│   └── Install Neo4j Spark Connector + Python packages
│
├── Track B: Data + Lakehouse Tables
│   ├── Find SQL Warehouse
│   ├── Upload CSV files to Unity Catalog volume
│   ├── Upload workshop notebooks to shared workspace folder
│   ├── Verify upload
│   └── Create Delta Lake tables via Statement Execution API
│
├── Track C: Permissions Lockdown
│   ├── Remove compute-creation entitlements from `users` group
│   ├── Remove non-admin access from Personal Compute policy
│   ├── Verify `aircraft_workshop_group` exists in workspace
│   ├── Grant read-only Unity Catalog privileges to the group
│   └── Grant CAN_READ on shared notebook folder to the group
│
└── Report results
```

```bash
uv run databricks-setup setup
```

All configuration is loaded from `lab_setup/.env` — see [Configuration](#configuration) below.

### `add-users`

Creates workspace accounts, adds users to the workshop group, and creates per-user clusters.

```bash
uv run databricks-setup add-users
```

To add users to the group **without creating clusters** (e.g., if you'll create clusters later or want users to share an existing cluster):

```bash
uv run databricks-setup add-users --skip-clusters
```

### `remove-users`

Removes users from the group and deletes their per-user clusters.

```bash
uv run databricks-setup remove-users
```

To remove users from the group **while keeping their clusters**:

```bash
uv run databricks-setup remove-users --keep-clusters
```

### `list-users`

Shows all group members with their email, display name, cluster name, and cluster state.

```bash
uv run databricks-setup list-users
```

### `cleanup`

Deletes permissions, notebooks, lakehouse tables, volume, schemas, and catalog. Per-user clusters are **not** affected — use `remove-users` for that.

```bash
# Interactive confirmation prompt
uv run databricks-setup cleanup

# Skip confirmation
uv run databricks-setup cleanup --yes
```

## Configuration

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

### All options

| Variable | Description | Default |
|----------|-------------|---------|
| `CATALOG_NAME` | Unity Catalog name | `aws-databricks-neo4j-lab` |
| `VOLUME_SCHEMA` | Schema for the data volume | `lab-schema` |
| `VOLUME_NAME` | Volume name for CSV data upload | `lab-volume` |
| `LAKEHOUSE_SCHEMA` | Schema for lakehouse Delta tables | `lakehouse` |
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

### Cloud provider defaults

| Provider | Default Node Type | Notes |
|----------|------------------|-------|
| AWS | `m5.xlarge` | 16 GB, 4 cores, EBS volume attached |
| Azure | `Standard_D4ds_v5` | 16 GB, 4 cores |

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

## Project Structure

```
auto_scripts/
├── pyproject.toml              # Project config, dependencies
├── uv.lock                     # Locked dependencies
├── README.md
└── src/databricks_setup/
    ├── __init__.py
    ├── main.py                 # Typer CLI entry point (setup + cleanup)
    ├── config.py               # Configuration dataclasses
    ├── models.py               # Shared domain models (SqlStep, SqlResult, etc.)
    ├── log.py                  # Dual-output logging (terminal + timestamped log file)
    ├── utils.py                # Polling, client helpers
    ├── cluster.py              # Cluster creation/management
    ├── libraries.py            # Library installation
    ├── data_upload.py          # Volume file upload
    ├── warehouse.py            # SQL Warehouse management + SQL execution
    ├── lakehouse_tables.py     # Lakehouse SQL definitions + creation
    └── cleanup.py              # Teardown logic (schemas, volume, catalog)
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run linter
uv run ruff check src/

# Run type checker
uv run mypy src/

# Auto-fix linting issues
uv run ruff check --fix src/
```
