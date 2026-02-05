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
- [ ] Run `setup_databricks.sh` to set up compute, upload data, and create tables (Step 2)
- [ ] Configure Databricks Genie Space (Lab 7)
- [ ] Provide DBC file to participants (or host for download)
- [ ] Test the complete workflow
- [ ] Document connection details for participants

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

## Step 2: Automated Setup

The `setup_databricks.sh` script handles everything after catalog creation in one command:

1. Creates (or reuses) a Dedicated compute cluster
2. Installs the Neo4j Spark Connector and all PyPI libraries
3. Uploads CSV and Markdown data files to the volume
4. Creates Delta Lake tables for Databricks Genie (Lab 7)

If a cluster with the same name already exists, the script reuses it (starting it if terminated) instead of creating a new one.

### How to run it

```bash
./lab_setup/setup_databricks.sh [--cluster-only] [catalog.schema.volume] [user-email] [cluster-name]
```

All arguments are optional:

```bash
# All defaults (catalog=aws-databricks-neo4j-lab, auto-detect user, cluster="Small Spark 4.0")
./lab_setup/setup_databricks.sh

# Cluster + libraries only (skip data upload and table creation)
./lab_setup/setup_databricks.sh --cluster-only

# Explicit volume
./lab_setup/setup_databricks.sh aws-databricks-neo4j-lab.lab-schema.lab-volume

# Explicit volume + user
./lab_setup/setup_databricks.sh test_catalog.test_schema.test_volume ryan.knight@neo4j.com

# Explicit volume + user + cluster name
./lab_setup/setup_databricks.sh test_catalog.test_schema.test_volume ryan.knight@neo4j.com "My Workshop"
```

The `--cluster-only` flag creates the cluster and installs libraries, then exits — skipping data upload and lakehouse table creation. Useful when you only need a running cluster with the right libraries (e.g., for Lab 6 which doesn't use lakehouse tables).

### Cluster defaults

| Setting | Value |
|---------|-------|
| Runtime | 17.3 LTS ML (Spark 4.0.0, Scala 2.13) |
| Photon | Enabled |
| Node type | `Standard_D4ds_v5` (16 GB, 4 cores) |
| Workers | 0 (single node) |
| Access mode | Dedicated (Single User) |
| Auto-terminate | 30 minutes |

To change defaults, edit the configuration variables at the top of `setup_databricks.sh`.

### Expected data files in volume

The script uploads all `.csv` and `.md` files from `aircraft_digital_twin_data/` (excluding documentation files). This includes data for Labs 5, 6, and 7:

```
/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/
│
│  Nodes (Lab 5 core)
├── nodes_aircraft.csv
├── nodes_systems.csv
├── nodes_components.csv
│
│  Nodes (Lab 5 full dataset - notebook 02)
├── nodes_airports.csv
├── nodes_delays.csv
├── nodes_flights.csv
├── nodes_maintenance.csv
├── nodes_removals.csv
│
│  Nodes (Lab 7 sensors)
├── nodes_sensors.csv
├── nodes_readings.csv          (23 MB, 345,600 rows)
│
│  Relationships (Lab 5 core)
├── rels_aircraft_system.csv
├── rels_system_component.csv
│
│  Relationships (Lab 5 full dataset - notebook 02)
├── rels_aircraft_flight.csv
├── rels_aircraft_removal.csv
├── rels_component_event.csv
├── rels_component_removal.csv
├── rels_event_aircraft.csv
├── rels_event_system.csv
├── rels_flight_arrival.csv
├── rels_flight_delay.csv
├── rels_flight_departure.csv
│
│  Relationships (Lab 7)
├── rels_system_sensor.csv
│
│  Maintenance Manuals (Lab 6)
├── MAINTENANCE_A320.md
├── MAINTENANCE_A321neo.md
└── MAINTENANCE_B737.md
```

### Expected lakehouse table row counts

| Table | Rows |
|-------|------|
| aircraft | 20 |
| systems | 80 |
| sensors | 160 |
| sensor_readings | 345,600 |


---

### Manual Setup (UI Alternative)

If you prefer to set up the cluster, libraries, and data through the Databricks UI instead of using `setup_databricks.sh`, see the complete step-by-step guide in **[MANUAL_SETUP.md](MANUAL_SETUP.md)**.

---

## Step 3: Configure Databricks Genie Space (Lab 7)

Databricks Genie provides a natural language interface for querying data.

### 3.1 Create Genie Space

1. Navigate to **Genie** in the left sidebar (under AI/BI)
2. Click **New** > **Genie space**
3. Configure:
   - **Name:** `Aircraft Sensor Analytics`
   - **Description:** `Natural language queries for aircraft sensor data`
4. Click **Create**

### 3.2 Add Tables to Genie Space

1. In the Genie space, click **Add tables**
2. Navigate to `aws-databricks-neo4j-lab.lakehouse`
3. Select all four tables:
   - `aircraft`
   - `systems`
   - `sensors`
   - `sensor_readings`
4. Click **Add**

### 3.3 Configure Table Relationships (Optional but Recommended)

Help Genie understand how tables relate:

1. Click on **Data model** in the Genie space
2. Define relationships:
   - `systems.aircraft_id` → `aircraft.:ID(Aircraft)`
   - `sensors.system_id` → `systems.:ID(System)`
   - `sensor_readings.sensor_id` → `sensors.:ID(Sensor)`

### 3.4 Add Sample Questions

Add sample questions to help users understand what they can ask:

1. Click **Instructions** in the Genie space
2. Add sample questions:
   - "What is the average EGT for all engines?"
   - "Show vibration readings for aircraft N95040A"
   - "Which sensors have the highest readings?"
   - "Compare fuel flow across aircraft models"
   - "Find sensors with readings above 700 degrees"
   - "What are the daily average temperatures by aircraft?"

### 3.5 Test Genie

Test the Genie space with a sample query:

1. Type: "What is the average temperature for each aircraft?"
2. Verify Genie generates appropriate SQL and returns results
3. Test a few more queries to ensure the space is working

### 3.6 Record Genie Space ID

For programmatic access in Lab 7, note the Genie Space ID:

1. Open the Genie space
2. Copy the ID from the URL: `https://your-workspace.cloud.databricks.com/genie/spaces/{SPACE_ID}`
3. Provide this to participants (e.g., in a shared document or handout)

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
- Ensure table comments are added (handled by `create_lakehouse_tables.py`)
- Verify table relationships are configured (Step 3.3)
- Add more sample questions to guide the model

**Lakehouse table creation fails**
- Ensure CSV files are uploaded to the Volume first
- Check file paths match exactly
- Verify cluster has access to the Volume

---

## File Inventory

For the full file inventory with sizes, record counts, and sensor data details, see **[MANUAL_SETUP.md](MANUAL_SETUP.md#file-inventory)**.

The setup script uploads **25 files** to the Volume:
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
