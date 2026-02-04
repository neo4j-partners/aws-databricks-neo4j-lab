# Lab 5 Admin Setup Guide

**Purpose:** Instructions for workshop administrators to prepare the Databricks environment before participants arrive.

---

## Pre-Workshop Checklist

Complete these steps before the workshop begins:

- [ ] Create Unity Catalog and Schema
- [ ] Create a Volume for CSV data
- [ ] Upload CSV files to the Volume
- [ ] Configure a Dedicated cluster with Neo4j Spark Connector
- [ ] Create the template notebook
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

## Step 4: Create Template Notebook

### 4.1 Create Workshop Folder

1. Navigate to **Workspace**
2. Create a folder: `Workshop_Materials` (or similar shared location)
3. Set permissions so participants can read but not modify

### 4.2 Create the Template Notebook

Create a new notebook named `aircraft_etl_to_neo4j_template` with the following structure:

**Cell 1: Introduction (Markdown)**
```markdown
# Aircraft ETL to Neo4j

This notebook loads Aircraft, System, and Component data from Databricks into Neo4j.

## Instructions
1. Clone this notebook to your personal folder
2. Enter your Neo4j credentials in the configuration cell below
3. Run all cells in order
4. Verify the data loaded using the query cells at the end
```

**Cell 2: Configuration (Python)**
```python
# ============================================
# CONFIGURATION - Enter your Neo4j credentials
# ============================================

NEO4J_URI = ""  # e.g., "neo4j+s://xxxxxxxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = ""  # Your password from Lab 1

# Unity Catalog Volume path (pre-configured by admin)
DATA_PATH = "/Volumes/aircraft_workshop/aircraft_lab/aircraft_data"
```

**Cell 3: Set Spark Configuration (Python)**
```python
# Configure Neo4j Spark Connector
spark.conf.set("neo4j.url", NEO4J_URI)
spark.conf.set("neo4j.authentication.basic.username", NEO4J_USERNAME)
spark.conf.set("neo4j.authentication.basic.password", NEO4J_PASSWORD)
spark.conf.set("neo4j.database", "neo4j")

print("Neo4j connection configured!")
print(f"URI: {NEO4J_URI}")
```

**Cell 4: Helper Function (Python)**
```python
def read_csv(filename):
    """Read a CSV file from the Unity Catalog Volume."""
    path = f"{DATA_PATH}/{filename}"
    return spark.read.option("header", "true").csv(path)

def write_nodes(df, label, id_column):
    """Write a DataFrame as nodes to Neo4j."""
    (df
     .write
     .format("org.neo4j.spark.DataSource")
     .mode("Overwrite")
     .option("labels", f":{label}")
     .option("node.keys", id_column)
     .save())
    print(f"Wrote {df.count()} {label} nodes")

def write_relationships(df, rel_type, source_label, source_key, target_label, target_key):
    """Write relationships to Neo4j using keys strategy."""
    (df
     .write
     .format("org.neo4j.spark.DataSource")
     .mode("Overwrite")
     .option("relationship", rel_type)
     .option("relationship.save.strategy", "keys")
     .option("relationship.source.labels", f":{source_label}")
     .option("relationship.source.node.keys", source_key)
     .option("relationship.target.labels", f":{target_label}")
     .option("relationship.target.node.keys", target_key)
     .save())
    print(f"Wrote {rel_type} relationships")
```

**Cell 5: Load and Preview Data (Python)**
```python
# Read CSV files from Unity Catalog Volume
aircraft_df = read_csv("nodes_aircraft.csv")
systems_df = read_csv("nodes_systems.csv")
components_df = read_csv("nodes_components.csv")

print("=== Data Preview ===")
print(f"\nAircraft: {aircraft_df.count()} rows")
display(aircraft_df.limit(5))

print(f"\nSystems: {systems_df.count()} rows")
display(systems_df.limit(5))

print(f"\nComponents: {components_df.count()} rows")
display(components_df.limit(5))
```

**Cell 6: Transform Data (Python)**
```python
# Rename ID columns to standard names (remove Neo4j import format)
aircraft_clean = (aircraft_df
    .withColumnRenamed(":ID(Aircraft)", "aircraft_id"))

systems_clean = (systems_df
    .withColumnRenamed(":ID(System)", "system_id"))

components_clean = (components_df
    .withColumnRenamed(":ID(Component)", "component_id"))

print("Data transformed for Neo4j loading")
```

**Cell 7: Write Nodes to Neo4j (Python)**
```python
print("=== Writing Nodes to Neo4j ===\n")

write_nodes(aircraft_clean, "Aircraft", "aircraft_id")
write_nodes(systems_clean, "System", "system_id")
write_nodes(components_clean, "Component", "component_id")

print("\nAll nodes written successfully!")
```

**Cell 8: Load and Write Relationships (Python)**
```python
print("=== Writing Relationships to Neo4j ===\n")

# Read relationship CSVs
aircraft_system_df = read_csv("rels_aircraft_system.csv")
system_component_df = read_csv("rels_system_component.csv")

# Rename columns to match node keys
aircraft_system_clean = (aircraft_system_df
    .withColumnRenamed(":START_ID(Aircraft)", "aircraft_id")
    .withColumnRenamed(":END_ID(System)", "system_id"))

system_component_clean = (system_component_df
    .withColumnRenamed(":START_ID(System)", "system_id")
    .withColumnRenamed(":END_ID(Component)", "component_id"))

# Write relationships
write_relationships(
    aircraft_system_clean, "HAS_SYSTEM",
    "Aircraft", "aircraft_id",
    "System", "system_id"
)

write_relationships(
    system_component_clean, "HAS_COMPONENT",
    "System", "system_id",
    "Component", "component_id"
)

print("\nAll relationships written successfully!")
```

**Cell 9: ETL Complete (Python)**
```python
print("=" * 50)
print("ETL COMPLETE!")
print("=" * 50)
print(f"\nNodes loaded:")
print(f"  - Aircraft: {aircraft_clean.count()}")
print(f"  - System: {systems_clean.count()}")
print(f"  - Component: {components_clean.count()}")
print(f"\nRelationships loaded:")
print(f"  - HAS_SYSTEM: {aircraft_system_clean.count()}")
print(f"  - HAS_COMPONENT: {system_component_clean.count()}")
print(f"\nTotal: {aircraft_clean.count() + systems_clean.count() + components_clean.count()} nodes")
print(f"Total: {aircraft_system_clean.count() + system_component_clean.count()} relationships")
```

**Cell 10: Verification Queries - Setup (Python)**
```python
# Helper to run Cypher queries from Databricks
def run_cypher(query):
    """Execute a Cypher query and return results as DataFrame."""
    return (spark.read
        .format("org.neo4j.spark.DataSource")
        .option("query", query)
        .load())
```

**Cell 11: Verify Node Counts (Python)**
```python
print("=== Verification: Node Counts ===\n")
result = run_cypher("MATCH (n) RETURN labels(n)[0] AS NodeType, count(*) AS Count ORDER BY NodeType")
display(result)
```

**Cell 12: Verify Relationship Counts (Python)**
```python
print("=== Verification: Relationship Counts ===\n")
result = run_cypher("MATCH ()-[r]->() RETURN type(r) AS RelType, count(*) AS Count ORDER BY RelType")
display(result)
```

**Cell 13: View Aircraft Hierarchy (Python)**
```python
print("=== Sample Query: Aircraft N95040A Hierarchy ===\n")
query = """
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
RETURN a.tail_number AS Aircraft,
       s.name AS System,
       s.type AS SystemType,
       collect(c.name) AS Components
ORDER BY s.type, s.name
"""
result = run_cypher(query)
display(result)
```

**Cell 14: Next Steps (Markdown)**
```markdown
## Success!

You have successfully loaded aircraft data into Neo4j!

### What you loaded:
- **20 Aircraft** (Boeing 737-800, Airbus A320/A321, Embraer E190)
- **80 Systems** (2 engines, avionics, hydraulics per aircraft)
- **320 Components** (fans, compressors, turbines, pumps, etc.)
- **400 Relationships** connecting aircraft to systems to components

### Next: Explore in Neo4j Aura

1. Open your Neo4j Aura console
2. Go to the Query tab
3. Try these visualization queries:

**See one aircraft's full hierarchy:**
```cypher
MATCH (a:Aircraft {tail_number: 'N95040A'})-[r1:HAS_SYSTEM]->(s:System)-[r2:HAS_COMPONENT]->(c:Component)
RETURN a, r1, s, r2, c
```

**Compare manufacturers:**
```cypher
MATCH (a:Aircraft)
RETURN a.manufacturer AS Manufacturer, count(a) AS Count
```

**Find component distribution:**
```cypher
MATCH (c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC
```
```

### 4.3 Set Notebook Permissions

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
