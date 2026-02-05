# Databricks Asset Bundles Automation Proposal

**Purpose:** Evaluate whether the lab setup process in `lab_setup/README.md` can be automated using Databricks Asset Bundles (DABs).

---

## What Are Databricks Asset Bundles?

Databricks Asset Bundles are an infrastructure-as-code feature of the Databricks CLI that lets you define Databricks resources (clusters, schemas, volumes, jobs, pipelines, etc.) as YAML or Python configuration files. You can then validate, deploy, and manage these resources programmatically.

**Key Benefits:**
- Version control your infrastructure alongside code
- Reproducible deployments across environments (dev/staging/prod)
- Single command deployment: `databricks bundle deploy`
- Supports Unity Catalog resources (schemas, volumes)
- Can install Maven libraries on clusters

---

## Current Manual Setup Process

From `lab_setup/README.md`, the workshop admin must:

| Step | Task | Manual Effort |
|------|------|---------------|
| 1.1 | Create Unity Catalog | UI clicks |
| 1.2 | Create Schema | UI clicks |
| 2.1 | Create Volume | UI clicks |
| 2.2-2.4 | Upload 9 CSV/MD files | UI drag-drop or CLI commands |
| 3.1 | Create Dedicated cluster | UI configuration |
| 3.2 | Install Neo4j Spark Connector (Maven) | UI library installation |
| 4.1 | Create Lakehouse schema | UI or SQL |
| 4.2 | Create Delta Lake tables | Run SQL statements |
| 4.3-4.4 | Add table comments | Run SQL statements |
| 5.1-5.6 | Configure Genie Space | UI configuration |

**Total: ~15-20 minutes of manual work, error-prone, hard to reproduce**

---

## What DABs Can Automate

### Fully Automatable (Native DAB Resources)

| Resource | DAB Support | Notes |
|----------|-------------|-------|
| Unity Catalog Schema | Yes | `resources.schemas` mapping |
| Unity Catalog Volume | Yes | `resources.volumes` mapping (CLI 0.236.0+) |
| Dedicated Cluster | Yes | `resources.clusters` mapping |
| Maven Library on Cluster | Yes | Via `libraries` in job tasks |
| Jobs to run SQL | Yes | `resources.jobs` with SQL tasks |

### Partially Automatable

| Task | Approach | Limitation |
|------|----------|------------|
| Upload CSV files to Volume | Use `artifact_path` pointing to Volume + sync | Files deploy to workspace first; need a job to copy to Volume |
| Create Delta Tables | Job with SQL File task | Works well, just requires SQL file |
| Add Table Comments | Job with SQL File task | Same as above |

### Not Directly Automatable (Requires Workarounds)

| Task | Issue | Workaround |
|------|-------|------------|
| Genie Space creation | No native DAB resource type | Use Databricks REST API via a Python job task |
| Genie Space table relationships | No native DAB resource type | Same - API call in job |
| Genie Space sample questions | No native DAB resource type | Same - API call in job |

---

## Proposed Bundle Structure

```
lab_setup/
├── databricks.yml              # Main bundle configuration
├── resources/
│   ├── catalog.yml             # Schema and Volume definitions
│   ├── cluster.yml             # Dedicated cluster with Neo4j connector
│   └── jobs.yml                # Setup jobs (tables, Genie)
├── src/
│   ├── create_tables.sql       # Delta table creation SQL
│   ├── add_comments.sql        # Table/column comments SQL
│   ├── setup_genie.py          # Python script to configure Genie via API
│   └── upload_data.py          # Script to copy files from workspace to Volume
└── data/
    ├── nodes_aircraft.csv
    ├── nodes_systems.csv
    ├── nodes_components.csv
    ├── nodes_sensors.csv
    ├── nodes_readings.csv
    ├── rels_aircraft_system.csv
    ├── rels_system_component.csv
    ├── rels_system_sensor.csv
    └── MAINTENANCE_A320.md
```

---

## Proposed `databricks.yml` Configuration

```yaml
bundle:
  name: neo4j-lab-setup

variables:
  catalog_name:
    description: "Unity Catalog name"
    default: "aws-databricks-neo4j-lab"
  schema_name:
    description: "Schema for workshop data"
    default: "lab-schema"
  lakehouse_schema:
    description: "Schema for Delta Lake tables"
    default: "lakehouse"
  volume_name:
    description: "Volume for CSV files"
    default: "lab-volume"
  cluster_name:
    description: "Workshop cluster name"
    default: "aircraft-workshop-cluster"
  neo4j_spark_connector_version:
    description: "Neo4j Spark Connector Maven coordinates"
    default: "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.2_for_spark_3"

workspace:
  artifact_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/artifacts

sync:
  include:
    - "data/*.csv"
    - "data/*.md"
    - "src/*.sql"
    - "src/*.py"

include:
  - "resources/*.yml"

targets:
  dev:
    default: true
    mode: development
  prod:
    mode: production
```

---

## Resource Definitions

### `resources/catalog.yml` - Unity Catalog Resources

```yaml
resources:
  schemas:
    lab_schema:
      catalog_name: ${var.catalog_name}
      name: ${var.schema_name}
      comment: "Workshop data and files for Neo4j lab"
      grants:
        - principal: account users
          privileges:
            - USE_SCHEMA
            - SELECT

    lakehouse_schema:
      catalog_name: ${var.catalog_name}
      name: ${var.lakehouse_schema}
      comment: "Delta Lake tables for Genie queries"
      grants:
        - principal: account users
          privileges:
            - USE_SCHEMA
            - SELECT

  volumes:
    lab_volume:
      catalog_name: ${var.catalog_name}
      schema_name: ${var.schema_name}
      name: ${var.volume_name}
      volume_type: MANAGED
      comment: "CSV and markdown files for workshop labs"
```

### `resources/cluster.yml` - Dedicated Cluster

```yaml
resources:
  clusters:
    workshop_cluster:
      cluster_name: ${var.cluster_name}
      spark_version: "14.3.x-scala2.12"
      node_type_id: "m5.xlarge"
      num_workers: 0
      autotermination_minutes: 30
      data_security_mode: "SINGLE_USER"
      spark_conf:
        spark.databricks.cluster.profile: singleNode
        spark.master: "local[*]"
      custom_tags:
        workshop: "neo4j-graphrag"
```

### `resources/jobs.yml` - Setup Jobs

```yaml
resources:
  jobs:
    # Job 1: Upload data files to Volume
    upload_data_job:
      name: "Lab Setup - Upload Data to Volume"
      tasks:
        - task_key: upload_files
          spark_python_task:
            python_file: ./src/upload_data.py
            parameters:
              - "--source=/Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/artifacts/data"
              - "--target=/Volumes/${var.catalog_name}/${var.schema_name}/${var.volume_name}"
          new_cluster:
            spark_version: "14.3.x-scala2.12"
            node_type_id: "m5.xlarge"
            num_workers: 0

    # Job 2: Create Delta Lake tables
    create_tables_job:
      name: "Lab Setup - Create Lakehouse Tables"
      tasks:
        - task_key: create_tables
          sql_task:
            file:
              path: ./src/create_tables.sql
            warehouse_id: ${var.warehouse_id}
        - task_key: add_comments
          depends_on:
            - task_key: create_tables
          sql_task:
            file:
              path: ./src/add_comments.sql
            warehouse_id: ${var.warehouse_id}

    # Job 3: Configure Genie Space (via API)
    setup_genie_job:
      name: "Lab Setup - Configure Genie Space"
      tasks:
        - task_key: setup_genie
          depends_on:
            - task_key: add_comments
          spark_python_task:
            python_file: ./src/setup_genie.py
            parameters:
              - "--catalog=${var.catalog_name}"
              - "--schema=${var.lakehouse_schema}"
              - "--space-name=Aircraft Sensor Analytics"
          new_cluster:
            spark_version: "14.3.x-scala2.12"
            node_type_id: "m5.xlarge"
            num_workers: 0
          libraries:
            - pypi:
                package: "databricks-sdk"
```

---

## Supporting Scripts

### `src/upload_data.py` - Copy Files to Volume

```python
"""Copy workshop data files from workspace to Unity Catalog Volume."""
import argparse
import os
import shutil

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    # In Databricks, /Volumes paths are accessible as local filesystem
    os.makedirs(args.target, exist_ok=True)

    for filename in os.listdir(args.source):
        src_path = os.path.join(args.source, filename)
        dst_path = os.path.join(args.target, filename)
        print(f"Copying {filename} to {args.target}")
        shutil.copy2(src_path, dst_path)

    print(f"Uploaded {len(os.listdir(args.source))} files to Volume")

if __name__ == "__main__":
    main()
```

### `src/setup_genie.py` - Configure Genie Space via API

```python
"""Create and configure Genie Space using Databricks SDK."""
import argparse
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import GenieCreateRequestV2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--space-name", required=True)
    args = parser.parse_args()

    w = WorkspaceClient()

    # Create Genie Space
    tables = [
        f"{args.catalog}.{args.schema}.aircraft",
        f"{args.catalog}.{args.schema}.systems",
        f"{args.catalog}.{args.schema}.sensors",
        f"{args.catalog}.{args.schema}.sensor_readings",
    ]

    space = w.genie.create(
        space_name=args.space_name,
        description="Natural language queries for aircraft sensor data",
        table_identifiers=tables,
    )

    print(f"Created Genie Space: {space.space_id}")
    print(f"URL: https://{w.config.host}/genie/spaces/{space.space_id}")

if __name__ == "__main__":
    main()
```

---

## Deployment Workflow

### One-Time Setup

```bash
# 1. Install Databricks CLI (if not already)
brew install databricks

# 2. Configure authentication
databricks auth login --host https://your-workspace.cloud.databricks.com

# 3. Navigate to lab_setup directory
cd lab_setup

# 4. Validate the bundle
databricks bundle validate

# 5. Deploy resources (creates schemas, volumes, cluster)
databricks bundle deploy

# 6. Run setup jobs
databricks bundle run upload_data_job
databricks bundle run create_tables_job
databricks bundle run setup_genie_job
```

### Teardown (After Workshop)

```bash
# Destroy all created resources
databricks bundle destroy
```

---

## Automation Coverage Summary

| Setup Step | Manual | With DABs | Improvement |
|------------|--------|-----------|-------------|
| Create Schema | 2 min | 0 (declarative) | Automated |
| Create Volume | 2 min | 0 (declarative) | Automated |
| Upload 9 files | 5 min | 1 command | 80% faster |
| Create Cluster | 3 min | 0 (declarative) | Automated |
| Install Neo4j Connector | 2 min | 0 (declarative) | Automated |
| Create Lakehouse Schema | 1 min | 0 (declarative) | Automated |
| Create Delta Tables | 3 min | 1 command | 80% faster |
| Add Table Comments | 2 min | 0 (bundled with above) | Automated |
| Configure Genie Space | 5 min | 1 command | 80% faster |
| **Total** | **~25 min** | **~3 commands** | **90% reduction** |

---

## Limitations and Considerations

### What DABs Cannot Do

1. **Create the Catalog itself** - The Unity Catalog must exist before deploying (can create schemas within it)
2. **Install cluster libraries persistently** - Libraries in DABs are job-scoped, not cluster-scoped. Participants still need to install Neo4j Spark Connector on the shared cluster manually, OR use a job cluster per task.
3. **Native Genie Space resource** - Genie Spaces are not a first-class DAB resource; requires API calls via Python job

### Workaround for Cluster Libraries

Option A: Document that the cluster library must be added manually after `bundle deploy`

Option B: Use job clusters with libraries specified per-task (each job run provisions cluster with libraries)

Option C: Use a separate Databricks CLI command:
```bash
databricks libraries cluster install \
  --cluster-id $(databricks clusters get --cluster-name aircraft-workshop-cluster --output json | jq -r '.cluster_id') \
  --maven-coordinates "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.2_for_spark_3"
```

---

## Recommendation

**Proceed with DABs automation.** The benefits significantly outweigh the limitations:

1. **Reproducibility** - Same setup every time, no human error
2. **Version Control** - Infrastructure changes are tracked in git
3. **Speed** - Setup time drops from ~25 minutes to ~3 commands
4. **Documentation** - The bundle itself documents the infrastructure
5. **Teardown** - `bundle destroy` cleanly removes all resources

### Implementation Priority

| Phase | Tasks | Effort |
|-------|-------|--------|
| 1 | Schema + Volume + basic file upload | 2-3 hours |
| 2 | Delta table creation jobs | 1-2 hours |
| 3 | Genie Space API integration | 2-3 hours |
| 4 | Testing and documentation | 2-3 hours |

**Total estimated effort: 1-2 days**

---

## References

- [What are Databricks Asset Bundles?](https://docs.databricks.com/aws/en/dev-tools/bundles/)
- [DAB Resources](https://docs.databricks.com/aws/en/dev-tools/bundles/resources)
- [Bundle Configuration](https://docs.databricks.com/aws/en/dev-tools/bundles/settings)
- [Bundle Examples](https://docs.databricks.com/aws/en/dev-tools/bundles/examples)
- [Library Dependencies](https://docs.databricks.com/aws/en/dev-tools/bundles/library-dependencies)
- [Genie Space Setup](https://docs.databricks.com/aws/en/genie/set-up)
