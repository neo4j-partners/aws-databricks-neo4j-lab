# Databricks Setup CLI

A modular Python CLI tool for setting up Databricks environments for the Neo4j workshop.

For full usage instructions, configuration options, and examples, see the main [Lab Admin Setup Guide](../README.md#step-2-automated-setup).

## Quick Start

```bash
cd lab_setup/auto_scripts
uv sync
uv run databricks-setup
```

## What It Does

Runs two parallel tracks by default:

```
databricks-setup CLI
├── Track A (parallel): Cluster + Libraries
│   ├── Create or reuse dedicated Spark cluster
│   ├── Wait for cluster to reach RUNNING state
│   └── Install Neo4j Spark Connector + Python packages
│
├── Track B (parallel): Data + Lakehouse Tables
│   ├── Find SQL Warehouse
│   ├── Upload CSV files to Unity Catalog volume
│   ├── Verify upload
│   └── Create Delta Lake tables via Statement Execution API
│
└── Wait for both tracks, report results
```

Use `--cluster-only` to skip Track B, or `--tables-only` to skip Track A.

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
    ├── lakehouse_tables.py     # Lakehouse SQL definitions + creation
    ├── warehouse.py            # SQL Warehouse management + SQL execution
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
