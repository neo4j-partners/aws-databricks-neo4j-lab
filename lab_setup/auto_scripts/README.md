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

Runs two tracks sequentially:

```
databricks-setup setup
├── Track A: Cluster + Libraries
│   ├── Create or reuse dedicated Spark cluster
│   ├── Wait for cluster to reach RUNNING state
│   └── Install Neo4j Spark Connector + Python packages
│
├── Track B: Data + Lakehouse Tables
│   ├── Find SQL Warehouse
│   ├── Upload CSV files to Unity Catalog volume
│   ├── Verify upload
│   └── Create Delta Lake tables via Statement Execution API
│
└── Report results
```

```bash
# Run setup
uv run databricks-setup setup

# Explicit volume target
uv run databricks-setup setup my-catalog.my-schema.my-volume
```

### `cleanup`

Deletes the lakehouse schema (with tables), volume, volume schema, and catalog. The compute cluster is **not** affected.

```bash
# Interactive confirmation prompt
uv run databricks-setup cleanup

# Skip confirmation
uv run databricks-setup cleanup --yes

# Explicit volume target
uv run databricks-setup cleanup my-catalog.my-schema.my-volume --yes
```

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
