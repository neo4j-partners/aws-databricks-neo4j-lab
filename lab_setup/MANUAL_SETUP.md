# Manual Setup Guide (UI Alternative)

**Purpose:** Step-by-step instructions for setting up the entire Databricks workshop environment through the UI, without using the `setup_databricks.sh` automation script.

> **Prefer the automated approach?** Run `./lab_setup/setup_databricks.sh` instead — it handles Steps 2–5 below in one command. See the main [README.md](README.md) for details.

---

## Prerequisites: Databricks CLI Authentication

Even with manual UI setup, the CLI is needed for data upload. Authenticate first:

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

## Step 1: Create Unity Catalog, Schema, and Volume (UI)

Newer Databricks workspaces use **Default Storage**, which blocks programmatic catalog creation via CLI, REST API, and SQL. Only the UI has the special handling to assign Default Storage to a new catalog. See [CATALOG_SETUP_COMPLEXITY.md](CATALOG_SETUP_COMPLEXITY.md) for details.

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

## Step 2: Create a Dedicated Compute Cluster (UI)

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

The Neo4j Spark Connector requires **Dedicated (Single User)** access mode — shared access modes are not supported. See [Neo4j Spark Connector docs](https://neo4j.com/docs/spark/current/databricks/).

### Cluster defaults reference

| Setting | Value |
|---------|-------|
| Runtime | 17.3 LTS ML (Spark 4.0.0, Scala 2.13) |
| Photon | Enabled |
| Node type | `Standard_D4ds_v5` (16 GB, 4 cores) |
| Workers | 0 (single node) |
| Access mode | Dedicated (Single User) |
| Auto-terminate | 30 minutes |

---

## Step 3: Install Libraries (UI)

After the cluster is created and running, install the following libraries:

1. Click on the cluster name
2. Go to **Libraries** tab
3. Click **Install new**

### Maven library

| Type | Coordinates |
|------|-------------|
| Maven | `org.neo4j:neo4j-connector-apache-spark_2.13:5.3.10_for_spark_3` |

### PyPI libraries

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

---

## Step 4: Upload Data Files to the Volume

Upload the CSV and Markdown files from the `aircraft_digital_twin_data/` directory to the volume using the Databricks CLI:

```bash
VOLUME_PATH="dbfs:/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume"

# Lab 5 - Aircraft digital twin nodes and relationships
databricks fs cp lab_setup/aircraft_digital_twin_data/nodes_aircraft.csv    "${VOLUME_PATH}/nodes_aircraft.csv" --overwrite
databricks fs cp lab_setup/aircraft_digital_twin_data/nodes_systems.csv     "${VOLUME_PATH}/nodes_systems.csv" --overwrite
databricks fs cp lab_setup/aircraft_digital_twin_data/nodes_components.csv  "${VOLUME_PATH}/nodes_components.csv" --overwrite
databricks fs cp lab_setup/aircraft_digital_twin_data/rels_aircraft_system.csv  "${VOLUME_PATH}/rels_aircraft_system.csv" --overwrite
databricks fs cp lab_setup/aircraft_digital_twin_data/rels_system_component.csv "${VOLUME_PATH}/rels_system_component.csv" --overwrite

# Lab 6 - Maintenance manual
databricks fs cp lab_setup/aircraft_digital_twin_data/MAINTENANCE_A320.md   "${VOLUME_PATH}/MAINTENANCE_A320.md" --overwrite

# Lab 7 - Sensor data
databricks fs cp lab_setup/aircraft_digital_twin_data/nodes_sensors.csv     "${VOLUME_PATH}/nodes_sensors.csv" --overwrite
databricks fs cp lab_setup/aircraft_digital_twin_data/nodes_readings.csv    "${VOLUME_PATH}/nodes_readings.csv" --overwrite
databricks fs cp lab_setup/aircraft_digital_twin_data/rels_system_sensor.csv "${VOLUME_PATH}/rels_system_sensor.csv" --overwrite
```

Alternatively, upload via the **Databricks UI**:

1. Navigate to **Data** > **Catalogs** > `aws-databricks-neo4j-lab` > `lab-schema` > `lab-volume`
2. Click **Upload to this volume**
3. Drag and drop (or browse) to upload each file listed above

### Verify the upload

```bash
databricks fs ls "${VOLUME_PATH}"
```

### Expected files in the volume

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

## Step 5: Create Lakehouse Tables

Create the Delta Lake tables needed for Databricks Genie (Lab 7). Use the helper script, which runs SQL against your cluster:

```bash
./lab_setup/create_lakehouse_tables.sh [catalog]
```

Or run `create_lakehouse_tables.py` directly in a Databricks notebook:

1. Upload `lab_setup/create_lakehouse_tables.py` to your Databricks workspace
2. Open it as a notebook
3. Attach it to the cluster created in Step 2
4. Set the catalog, schema, and volume values at the top of the script
5. Run all cells

### Expected lakehouse table row counts

| Table | Rows |
|-------|------|
| aircraft | 20 |
| systems | 80 |
| sensors | 160 |
| sensor_readings | 345,600 |

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

| File | Size | Description | Required for Lab 6 |
|------|------|-------------|-------------------|
| `MAINTENANCE_A320.md` | ~30 KB | A320-200 Maintenance and Troubleshooting Manual | Yes |

**Note:** The maintenance manual covers the aircraft loaded in Lab 5. It includes specifications, troubleshooting procedures, fault codes, and scheduled maintenance tasks.

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

---

## Troubleshooting

### Cluster Issues

**"Spark Connector not found" error**
- Verify cluster is in Dedicated (Single User) mode
- Check library installation status
- Restart cluster after adding library

### Connection Issues

**"Connection refused" to Neo4j**
- Verify URI format: `neo4j+s://` for Aura
- Check participant's Neo4j instance is running
- Verify credentials are correct

### Data Issues

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

**Lakehouse table creation fails**
- Ensure CSV files are uploaded to the Volume first
- Check file paths match exactly
- Verify cluster has access to the Volume

### Genie Issues

**Genie not generating correct SQL**
- Ensure table comments are added
- Verify table relationships are configured
- Add more sample questions to guide the model
