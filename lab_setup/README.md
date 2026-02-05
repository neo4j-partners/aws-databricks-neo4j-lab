# Lab Admin Setup Guide

**Purpose:** Instructions for workshop administrators to prepare the Databricks environment before participants arrive.

---

## Prerequisites: Databricks CLI Authentication

Before running any CLI commands, authenticate the Databricks CLI with your user account:

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

This opens a browser for OAuth login. After authenticating, verify you are logged in as your user (not a service principal):

```bash
databricks current-user me
```

You should see your email address in the output. If you see a UUID instead, your CLI is configured with a service principal. Check for overriding environment variables:

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

---

## Pre-Workshop Checklist

Complete these steps before the workshop begins:

- [ ] Create Unity Catalog, Schema, and Volume (Step 1 — UI required)
- [ ] Run `setup_databricks.sh` to set up compute, upload data, and create tables (Step 2)
- [ ] Configure Databricks Genie Space (Lab 7)
- [ ] Provide DBC file to participants (or host for download)
- [ ] Test the complete workflow
- [ ] Document connection details for participants

---

## Why Catalog Creation Is Manual

Newer Databricks workspaces use **Default Storage**, which blocks programmatic catalog creation via CLI, REST API, and SQL — all return the same error. Only the UI has the special handling to assign Default Storage to a new catalog. Once the catalog exists, everything else (schema, volume, compute, data upload, and table creation) is automated by `setup_databricks.sh`. See [CATALOG_SETUP_COMPLEXITY.md](CATALOG_SETUP_COMPLEXITY.md) for details.

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

---

## Step 2: Upload Data Files

The `setup_databricks.sh` script uploads all required CSV and Markdown files to the volume in one command.

### What it does

Uploads all `.csv` and `.md` files from `aircraft_digital_twin_data/` to the specified Databricks volume, skipping documentation files. It then lists the volume contents to verify the upload.

### How to run it

```bash
./lab_setup/setup_databricks.sh <catalog>.<schema>.<volume>
```

For the default naming convention:

```bash
./lab_setup/setup_databricks.sh aws-databricks-neo4j-lab.lab-schema.lab-volume
```

### Expected output

After upload, the volume should contain:

```
/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/
├── nodes_aircraft.csv         (Lab 5)
├── nodes_systems.csv          (Lab 5)
├── nodes_components.csv       (Lab 5)
├── rels_aircraft_system.csv   (Lab 5)
├── rels_system_component.csv  (Lab 5)
├── MAINTENANCE_A320.md        (Lab 6)
├── nodes_sensors.csv          (Lab 7)
├── nodes_readings.csv         (Lab 7)
└── rels_system_sensor.csv     (Lab 7)
```

---

## Step 3: Configure Compute Cluster

The Neo4j Spark Connector requires **Dedicated (Single User)** access mode — shared access modes are not supported. See [Neo4j Spark Connector docs](https://neo4j.com/docs/spark/current/databricks/).

### Option A: Automated Setup (Recommended)

The `setup_compute.sh` script creates the cluster and installs all libraries in one command.

#### What it does

1. Creates a single-node cluster with Dedicated access mode
2. Waits for the cluster to reach RUNNING state
3. Installs the Neo4j Spark Connector (Maven) and all PyPI libraries
4. Polls until all libraries are installed

#### How to run it

```bash
./lab_setup/setup_compute.sh [user-email] [cluster-name]
```

Examples:

```bash
# Auto-detect user, default name "Small Spark 4.0"
./lab_setup/setup_compute.sh

# Explicit user
./lab_setup/setup_compute.sh ryan.knight@neo4j.com

# Explicit user and custom cluster name
./lab_setup/setup_compute.sh ryan.knight@neo4j.com "Workshop Cluster"
```

#### Cluster defaults

| Setting | Value |
|---------|-------|
| Runtime | 17.3 LTS ML (Spark 4.0.0, Scala 2.13) |
| Photon | Enabled |
| Node type | `Standard_D4ds_v5` (16 GB, 4 cores) |
| Workers | 0 (single node) |
| Access mode | Dedicated (Single User) |
| Auto-terminate | 30 minutes |

To change defaults, edit the configuration variables at the top of `setup_compute.sh`.

---

### Option B: Manual Setup (UI)

If you prefer to create the cluster through the Databricks UI:

#### 3.1 Create a Dedicated Cluster

1. Navigate to **Compute**
2. Click **Create compute**
3. Configure:
   - **Name:** `Small Spark 4.0` (or your preferred name)
   - **Databricks Runtime:** 17.3 LTS ML (includes Apache Spark 4.0.0, Scala 2.13)
   - **Photon acceleration:** Enabled
   - **Node type:** `Standard_D4ds_v5` (16 GB Memory, 4 Cores) or equivalent
   - **Single node:** Enabled (0 workers)
   - **Auto termination:** 30 minutes
4. Expand **Advanced** options:
   - **Access mode:** Set to **Manual**
   - **Security mode:** **Dedicated**
   - **Single user or group:** Your Databricks user email

#### 3.2 Install Libraries

After the cluster is created and running, install the following libraries:

1. Click on the cluster name
2. Go to **Libraries** tab
3. Click **Install new**

**Maven library:**

| Type | Coordinates |
|------|-------------|
| Maven | `org.neo4j:neo4j-connector-apache-spark_2.13:5.3.10_for_spark_3` |

**PyPI libraries:**

| Package | Type |
|---------|------|
| `neo4j==6.0.2` | PyPI |
| `databricks-agents>=1.2.0` | PyPI |
| `langgraph==1.0.5` | PyPI |
| `langchain-openai==1.1.2` | PyPI |
| `pydantic==2.12.5` | PyPI |
| `langchain-core>=1.2.0` | PyPI |
| `databricks-langchain>=0.11.0` | PyPI |
| `dspy>=3.0.4` | PyPI |
| `neo4j-graphrag>=1.10.0` | PyPI |
| `beautifulsoup4>=4.12.0` | PyPI |
| `sentence_transformers` | PyPI |

Install each library one at a time (or use the bulk install option if available). Wait for all libraries to show **Installed** status before proceeding.

#### 3.3 Verify the Cluster

1. Confirm the cluster state is **Running**
2. Confirm all libraries show **Installed** status
3. Confirm access mode shows **Dedicated** in the cluster details

---

## Step 4: Create Lakehouse Tables (Lab 7)

Lab 7 uses Databricks Genie for natural language queries against sensor data stored in Delta Lake tables.

The `create_lakehouse_tables.sh` script automates this entire step. It uses the Databricks CLI to execute SQL via the [Statement Execution API](https://docs.databricks.com/aws/en/dev-tools/sql-execution-tutorial) against your SQL Warehouse.

### What it does

1. Creates the `lakehouse` schema in your catalog
2. Creates four Delta Lake tables from the CSV files in the volume (`aircraft`, `systems`, `sensors`, `sensor_readings`)
3. Adds table and column comments (improves Genie's natural language understanding)
4. Verifies row counts

**Requires:** A SQL Warehouse in the workspace (it auto-discovers the first available one).

### How to run it

```bash
./lab_setup/create_lakehouse_tables.sh [catalog]
```

For the default catalog:

```bash
./lab_setup/create_lakehouse_tables.sh aws-databricks-neo4j-lab
```

### Expected row counts

| Table | Rows |
|-------|------|
| aircraft | 20 |
| systems | 80 |
| sensors | 160 |
| sensor_readings | 345,600 |

> **Alternative:** For a Python-based approach using `databricks-sdk`, see [PYTHON_SDK_ALTERNATIVE.md](PYTHON_SDK_ALTERNATIVE.md).

---

## Step 5: Configure Databricks Genie Space (Lab 7)

Databricks Genie provides a natural language interface for querying data.

### 5.1 Create Genie Space

1. Navigate to **Genie** in the left sidebar (under AI/BI)
2. Click **New** > **Genie space**
3. Configure:
   - **Name:** `Aircraft Sensor Analytics`
   - **Description:** `Natural language queries for aircraft sensor data`
4. Click **Create**

### 5.2 Add Tables to Genie Space

1. In the Genie space, click **Add tables**
2. Navigate to `aws-databricks-neo4j-lab.lakehouse`
3. Select all four tables:
   - `aircraft`
   - `systems`
   - `sensors`
   - `sensor_readings`
4. Click **Add**

### 5.3 Configure Table Relationships (Optional but Recommended)

Help Genie understand how tables relate:

1. Click on **Data model** in the Genie space
2. Define relationships:
   - `systems.aircraft_id` → `aircraft.:ID(Aircraft)`
   - `sensors.system_id` → `systems.:ID(System)`
   - `sensor_readings.sensor_id` → `sensors.:ID(Sensor)`

### 5.4 Add Sample Questions

Add sample questions to help users understand what they can ask:

1. Click **Instructions** in the Genie space
2. Add sample questions:
   - "What is the average EGT for all engines?"
   - "Show vibration readings for aircraft N95040A"
   - "Which sensors have the highest readings?"
   - "Compare fuel flow across aircraft models"
   - "Find sensors with readings above 700 degrees"
   - "What are the daily average temperatures by aircraft?"

### 5.5 Test Genie

Test the Genie space with a sample query:

1. Type: "What is the average temperature for each aircraft?"
2. Verify Genie generates appropriate SQL and returns results
3. Test a few more queries to ensure the space is working

### 5.6 Record Genie Space ID

For programmatic access in Lab 7, note the Genie Space ID:

1. Open the Genie space
2. Copy the ID from the URL: `https://your-workspace.cloud.databricks.com/genie/spaces/{SPACE_ID}`
3. Provide this to participants or add to `CONFIG.txt`

---

## Step 6: Prepare Participant Instructions

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
- Ensure table comments are added (Step 4.4)
- Verify table relationships are configured (Step 5.3)
- Add more sample questions to guide the model

**Lakehouse table creation fails**
- Ensure CSV files are uploaded to the Volume first
- Check file paths match exactly
- Verify cluster has access to the Volume

---

## File Inventory

### Lab 5 - Aircraft Digital Twin Data

The `aircraft_digital_twin_data/` directory contains:

| File | Size | Records | Required for Lab |
|------|------|---------|------------------|
| `nodes_aircraft.csv` | 1 KB | 20 | Lab 5, Lab 7 |
| `nodes_systems.csv` | 3 KB | 80 | Lab 5, Lab 7 |
| `nodes_components.csv` | 12 KB | 320 | Lab 5 |
| `rels_aircraft_system.csv` | 2 KB | 80 | Lab 5 |
| `rels_system_component.csv` | 10 KB | 320 | Lab 5 |
| `nodes_sensors.csv` | 9 KB | 160 | Lab 7 |
| `nodes_readings.csv` | 23 MB | 345,600 | Lab 7 |
| `rels_system_sensor.csv` | 6 KB | 160 | Lab 7 |
| Other files | Various | Various | No |

### Lab 6 - Maintenance Manual

The `aircraft_digital_twin_data/` directory also contains:

| File | Size | Description | Required for Lab 6 |
|------|------|-------------|-------------------|
| `MAINTENANCE_A320.md` | ~30 KB | A320-200 Maintenance and Troubleshooting Manual | Yes |

**Note:** The maintenance manual is the A320-200 manual that covers the aircraft loaded in Lab 5. It includes specifications, troubleshooting procedures, fault codes, and scheduled maintenance tasks.

### Lab 7 - Sensor Data Details

The sensor data covers **90 days** of hourly readings (July 1 - September 29, 2024):

| Sensor Type | Unit | Description | Typical Range |
|-------------|------|-------------|---------------|
| EGT | °C | Exhaust Gas Temperature | 600-750 |
| Vibration | ips | Engine vibration | 0.1-2.0 |
| N1Speed | RPM | Engine fan speed | 2000-3500 |
| FuelFlow | kg/s | Fuel consumption rate | 0.5-2.0 |

**Data characteristics:**
- 160 sensors across 20 aircraft (4 sensors per engine, 2 engines per aircraft)
- 2,160 readings per sensor (90 days × 24 hours)
- Includes realistic degradation trends and anomalies

### Summary

Upload these files to the Volume for the complete workshop:
- **5 CSV files** from `aircraft_digital_twin_data/` (Lab 5)
- **1 Markdown file** (`MAINTENANCE_A320.md`) from `aircraft_digital_twin_data/` (Lab 6)
- **3 CSV files** from `aircraft_digital_twin_data/` (Lab 7: sensors, readings, relationships)

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
