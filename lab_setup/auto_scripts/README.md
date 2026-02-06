# Databricks Setup CLI

A modular Python CLI tool for setting up Databricks environments for the Neo4j workshop. Replaces the shell script `setup_databricks.sh` with a clean, type-safe implementation using the Databricks SDK.

## Features

- **Two execution modes**:
  - **Serverless mode**: Uses SQL Warehouse (faster, no cluster needed)
  - **Cluster mode**: Creates dedicated Spark cluster with Neo4j Spark Connector
- Upload data files to Unity Catalog volumes
- Create Delta Lake tables for Databricks Genie
- Full configuration via environment variables or `.env` file

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Databricks CLI configured with authentication (`databricks auth login`)

## Installation

```bash
cd lab_setup/auto_scripts

# Install dependencies and create virtual environment
uv sync
```

## Usage

```bash
# Run with all defaults
uv run databricks-setup

# Cluster + libraries only (skip data upload and tables)
uv run databricks-setup --cluster-only

# Specify volume, user, and cluster name
uv run databricks-setup my-catalog.my-schema.my-volume \
  --user user@example.com \
  --cluster "My Workshop Cluster"

# Use a specific Databricks CLI profile
uv run databricks-setup --profile my-workspace
```

### CLI Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `VOLUME` | | Target volume (`catalog.schema.volume`) | `aws-databricks-neo4j-lab.lab-schema.lab-volume` |
| `--user` | `-u` | Cluster owner email | Auto-detected |
| `--cluster` | `-c` | Cluster name to create/reuse | `Small Spark 4.0` |
| `--cluster-only` | | Skip data upload and table creation | `false` |
| `--env-file` | `-e` | Path to `.env` configuration file | `../lab_setup/.env` |
| `--profile` | `-p` | Databricks CLI profile | Default profile |

## Configuration

The CLI reads from `lab_setup/.env`. Copy the example and customize:

```bash
cd lab_setup
cp .env.example .env
```

### Serverless Mode (Recommended)

Use a SQL Warehouse instead of creating a cluster. This is faster and more cost-effective:

```bash
# In lab_setup/.env
USE_SERVERLESS=true
WAREHOUSE_NAME=Starter Warehouse
```

When `USE_SERVERLESS=true`:
- Skips cluster creation and library installation
- Uses the Statement Execution API to create tables
- Requires a SQL Warehouse (Starter Warehouse works)

### Cluster Mode

Create a dedicated Spark cluster (required for Neo4j Spark Connector):

```bash
# In lab_setup/.env
USE_SERVERLESS=false

# Cluster settings
SPARK_VERSION=17.3.x-cpu-ml-scala2.13
AUTOTERMINATION_MINUTES=30
RUNTIME_ENGINE=STANDARD  # or PHOTON
NODE_TYPE=m5.xlarge      # AWS default
CLOUD_PROVIDER=aws       # or azure
```

### All Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_SERVERLESS` | Use SQL Warehouse instead of cluster | `false` |
| `WAREHOUSE_NAME` | SQL Warehouse name (serverless mode) | `Starter Warehouse` |
| `WAREHOUSE_TIMEOUT` | SQL statement timeout (seconds) | `600` |
| `DATABRICKS_PROFILE` | CLI profile from ~/.databrickscfg | Default |
| `SPARK_VERSION` | Databricks Runtime version | `17.3.x-cpu-ml-scala2.13` |
| `AUTOTERMINATION_MINUTES` | Cluster auto-shutdown | `30` |
| `RUNTIME_ENGINE` | `STANDARD` or `PHOTON` | `STANDARD` |
| `CLOUD_PROVIDER` | `aws` or `azure` | `aws` |
| `NODE_TYPE` | Instance type | Auto-detected |

### Cloud Provider Defaults

| Provider | Default Node Type | Notes |
|----------|------------------|-------|
| AWS | `m5.xlarge` | 16 GB, 4 cores, EBS volume attached |
| Azure | `Standard_D4ds_v5` | 16 GB, 4 cores |

## Project Structure

```
auto_scripts/
├── pyproject.toml              # Project config, dependencies
├── uv.lock                     # Locked dependencies
├── README.md
└── src/databricks_setup/
    ├── __init__.py
    ├── config.py               # Configuration dataclasses
    ├── utils.py                # Polling, client helpers
    ├── cluster.py              # Cluster creation/management
    ├── libraries.py            # Library installation
    ├── data_upload.py          # Volume file upload
    ├── lakehouse.py            # Table creation via cluster
    ├── warehouse.py            # Table creation via SQL Warehouse
    └── main.py                 # Typer CLI entry point
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

## What It Does

### Serverless Mode (`USE_SERVERLESS=true`)

1. **Find Warehouse**: Locates the configured SQL Warehouse
2. **Data Upload**: Uploads CSV files to Unity Catalog volume (no cluster needed)
3. **Table Creation**: Creates Delta Lake tables via Statement Execution API

### Cluster Mode (`USE_SERVERLESS=false`)

1. **Cluster Setup**: Creates a single-node Spark 4.0 cluster with Dedicated (Single User) access mode (required for Neo4j Spark Connector)
2. **Library Installation**: Installs Neo4j Spark Connector + Python packages
3. **Data Upload**: Uploads CSV files to Unity Catalog volume
4. **Table Creation**: Executes `create_lakehouse_tables.py` via Command Execution API

## Comparison with Shell Script

| Feature | Shell Script | Python CLI |
|---------|-------------|------------|
| Dependencies | `jq`, `databricks` CLI | `databricks-sdk`, `typer` |
| Serverless Mode | No | Yes (`USE_SERVERLESS=true`) |
| Type Safety | None | Full mypy strict |
| Error Handling | Exit codes | Exceptions with context |
| Progress Display | Echo statements | Rich progress bars |
| Testability | Difficult | Modular, mockable |
| Configuration | Positional args | Named options + `.env` |
