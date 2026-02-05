# Lab 5 Admin Setup Guide

**Purpose:** Instructions for workshop administrators to prepare the Databricks environment before participants arrive.

---

## Pre-Workshop Checklist

Complete these steps before the workshop begins:

- [ ] Create Unity Catalog and Schema
- [ ] Create a Volume for CSV data
- [ ] Upload CSV files to the Volume
- [ ] Configure a Dedicated cluster with Neo4j Spark Connector
- [ ] Provide DBC file to participants (or host for download)
- [ ] Test the complete workflow
- [ ] Document connection details for participants

---

## Step 1: Create Unity Catalog Structure

### 1.1 Create or Select a Catalog

If a catalog doesn't exist for the workshop:

1. Navigate to **Data** > **Catalogs** in the Databricks workspace
2. Click **Create Catalog**
3. Name it `aws-databricks-neo4j-lab` (or similar)
4. Select the appropriate metastore
5. Click **Create**

### 1.2 Create a Schema

1. Within the catalog, click **Create Schema**
2. Name it `lab-schema`
3. Click **Create**

**Resulting path:** `aws-databricks-neo4j-lab.lab-schema`

---

## Step 2: Create a Volume for CSV Data

Volumes store files that can be accessed from notebooks.

### 2.1 Create the Volume

1. Navigate to the schema created above
2. Click **Create** > **Volume**
3. Configure:
   - **Name:** `lab-volume`
   - **Volume type:** Managed
4. Click **Create**

**Resulting path:** `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/`

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
databricks fs cp ./nodes_aircraft.csv /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/
databricks fs cp ./nodes_systems.csv /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/
databricks fs cp ./nodes_components.csv /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/
databricks fs cp ./rels_aircraft_system.csv /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/
databricks fs cp ./rels_system_component.csv /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/
```

### 2.3 Verify Upload

Run in a notebook cell:
```python
display(dbutils.fs.ls("/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/"))
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


## Step 6: Prepare Participant Instructions

Create a handout or slide with:

### Connection Information

| Resource | Value |
|----------|-------|
| Databricks Workspace URL | `https://your-workspace.cloud.databricks.com` |
| Cluster Name | `aircraft-workshop-cluster` |
| Notebook DBC File | `aircraft_etl_to_neo4j.dbc` (provide download link) |
| Data Volume Path | `/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume/` |

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
