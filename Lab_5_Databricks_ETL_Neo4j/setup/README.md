# Lab 5 Admin Setup Guide

**Purpose:** Instructions for workshop administrators to prepare the Databricks environment before participants arrive.

---

## Pre-Workshop Checklist

Complete these steps before the workshop begins:

- [ ] Create Unity Catalog and Schema
- [ ] Create a Volume for CSV data
- [ ] Upload CSV files to the Volume
- [ ] Configure a Dedicated cluster with Neo4j Spark Connector
- [ ] Import the template notebook
- [ ] Test the complete workflow
- [ ] Document connection details for participants

---

## Step 1: Create Unity Catalog Structure

### 1.1 Create or Select a Catalog

If a catalog doesn't exist for the workshop:

1. Navigate to **Data** > **Catalogs** in the Databricks workspace
2. Click **Create Catalog**
3. Name it `aircraft_workshop` (or similar)
4. Select the appropriate metastore
5. Click **Create**

### 1.2 Create a Schema

1. Within the catalog, click **Create Schema**
2. Name it `aircraft_lab`
3. Click **Create**

**Resulting path:** `aircraft_workshop.aircraft_lab`

---

## Step 2: Create a Volume for CSV Data

Volumes store files that can be accessed from notebooks.

### 2.1 Create the Volume

1. Navigate to the schema created above
2. Click **Create** > **Volume**
3. Configure:
   - **Name:** `aircraft_data`
   - **Volume type:** Managed
4. Click **Create**

**Resulting path:** `/Volumes/aircraft_workshop/aircraft_lab/aircraft_data/`

### 2.2 Upload CSV Files

Upload the following files from `aircraft_digital_twin_data/`:

**Required Node Files:**
- `nodes_aircraft.csv` (20 rows)
- `nodes_systems.csv` (80 rows)
- `nodes_components.csv` (320 rows)

**Required Relationship Files:**
- `rels_aircraft_system.csv` (80 rows)
- `rels_system_component.csv` (320 rows)

**Upload Methods:**

**Option A: UI Upload**
1. Click into the Volume
2. Click **Upload**
3. Drag and drop the CSV files
4. Wait for upload completion

**Option B: Databricks CLI**
```bash
databricks fs cp ./nodes_aircraft.csv /Volumes/aircraft_workshop/aircraft_lab/aircraft_data/
databricks fs cp ./nodes_systems.csv /Volumes/aircraft_workshop/aircraft_lab/aircraft_data/
databricks fs cp ./nodes_components.csv /Volumes/aircraft_workshop/aircraft_lab/aircraft_data/
databricks fs cp ./rels_aircraft_system.csv /Volumes/aircraft_workshop/aircraft_lab/aircraft_data/
databricks fs cp ./rels_system_component.csv /Volumes/aircraft_workshop/aircraft_lab/aircraft_data/
```

### 2.3 Verify Upload

Run in a notebook cell:
```python
display(dbutils.fs.ls("/Volumes/aircraft_workshop/aircraft_lab/aircraft_data/"))
```

Expected output shows 5 CSV files.

---

## Step 3: Configure Compute Cluster

### 3.1 Create a Dedicated Cluster

The Neo4j Spark Connector requires **Dedicated (Single User)** access mode.

1. Navigate to **Compute**
2. Click **Create compute**
3. Configure:
   - **Name:** `aircraft-workshop-cluster`
   - **Access mode:** **Single User** (Dedicated)
   - **Databricks Runtime:** 14.3 LTS or later
   - **Node type:** Standard (e.g., `m5.xlarge` or equivalent)
   - **Workers:** 0 (single node is sufficient for this small dataset)
   - **Auto termination:** 30 minutes (saves cost between sessions)

### 3.2 Install Neo4j Spark Connector Library

1. Click on the cluster name
2. Go to **Libraries** tab
3. Click **Install new**
4. Select **Maven**
5. Enter coordinates:
   ```
   org.neo4j:neo4j-connector-apache-spark_2.12:5.3.2_for_spark_3
   ```
   (Adjust version to match your Spark version)
6. Click **Install**
7. Wait for status to show "Installed"

### 3.3 Start the Cluster

1. Start the cluster
2. Wait for status to show "Running"
3. Verify library shows "Installed" status

---

## Step 4: Import Template Notebook

### 4.1 Create Workshop Folder

1. Navigate to **Workspace**
2. Create a folder: `Workshop_Materials` (or similar shared location)
3. Set permissions so participants can read but not modify

### 4.2 Import the Notebook

The notebook file is provided at `Lab_5_Databricks_ETL_Neo4j/aircraft_etl_to_neo4j.ipynb`.

**To import:**

1. Navigate to the `Workshop_Materials` folder
2. Click the **...** menu (or right-click)
3. Select **Import**
4. Choose **File** and upload `aircraft_etl_to_neo4j.ipynb`
5. The notebook will appear as `aircraft_etl_to_neo4j`
6. Optionally rename to `aircraft_etl_to_neo4j_template` for clarity

### 4.3 Update Volume Path (if needed)

If your Unity Catalog path differs from the default, update the `DATA_PATH` in the Configuration cell:

```python
# Default path - update if your setup differs
DATA_PATH = "/Volumes/aircraft_workshop/aircraft_lab/aircraft_data"
```

### 4.4 Notebook Contents

The imported notebook contains 6 sections with ~30 cells:

| Section | Description |
|---------|-------------|
| **Section 1** | Introduction & Configuration (Neo4j credentials) |
| **Section 2** | Data Preview (read and display CSVs) |
| **Section 3** | Load Nodes (Aircraft, System, Component) |
| **Section 4** | Load Relationships (HAS_SYSTEM, HAS_COMPONENT) |
| **Section 5** | Verification Queries (counts, sample queries) |
| **Section 6** | Next Steps (Neo4j Aura exploration guidance) |

Participants will clone this notebook, enter their Neo4j credentials, and run all cells.

### 4.5 Set Notebook Permissions

1. Right-click the notebook
2. Select **Permissions**
3. Add the participant group with **Can Read** permission
4. This allows cloning but prevents modifications to the template

---

## Step 5: Test the Complete Workflow

Before the workshop, run through the entire participant experience:

1. Clone the template notebook
2. Enter test Neo4j credentials
3. Run all cells
4. Verify counts match expected values:
   - Aircraft: 20
   - System: 80
   - Component: 320
   - HAS_SYSTEM: 80
   - HAS_COMPONENT: 320

5. Open Neo4j Aura and verify data is visible

---

## Step 6: Prepare Participant Instructions

Create a handout or slide with:

### Connection Information

| Resource | Value |
|----------|-------|
| Databricks Workspace URL | `https://your-workspace.cloud.databricks.com` |
| Cluster Name | `aircraft-workshop-cluster` |
| Template Notebook Location | `/Workspace/Workshop_Materials/aircraft_etl_to_neo4j_template` |
| Data Volume Path | `/Volumes/aircraft_workshop/aircraft_lab/aircraft_data/` |

### Quick Start Instructions

1. Sign in to Databricks with your workshop credentials
2. Navigate to Compute and ensure the cluster is running
3. Go to Workspace > Workshop_Materials
4. Right-click `aircraft_etl_to_neo4j_template` > Clone
5. Open your cloned notebook
6. Enter your Neo4j credentials from Lab 1
7. Run all cells (Shift+Enter or Run All)
8. Verify the counts in the output cells

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

---

## File Inventory

The `aircraft_digital_twin_data/` directory contains:

| File | Size | Records | Required for Lab |
|------|------|---------|------------------|
| `nodes_aircraft.csv` | 1 KB | 20 | Yes |
| `nodes_systems.csv` | 3 KB | 80 | Yes |
| `nodes_components.csv` | 12 KB | 320 | Yes |
| `rels_aircraft_system.csv` | 2 KB | 80 | Yes |
| `rels_system_component.csv` | 10 KB | 320 | Yes |
| `nodes_sensors.csv` | 5 KB | 160 | No (optional) |
| `nodes_readings.csv` | 25 MB | 345,600 | No (too large for this lab) |
| Other files | Various | Various | No |

Only the 5 files marked "Yes" need to be uploaded for the basic lab.

---

## Cost Considerations

- **Cluster:** Single-node clusters are sufficient for this small dataset
- **Auto-termination:** Set to 30-60 minutes to avoid idle costs
- **Storage:** Volume storage for 5 small CSV files is negligible

---

## Contact

For issues during workshop setup, contact the workshop organizers or refer to:
- [Neo4j Spark Connector Documentation](https://neo4j.com/docs/spark/current/)
- [Databricks Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
