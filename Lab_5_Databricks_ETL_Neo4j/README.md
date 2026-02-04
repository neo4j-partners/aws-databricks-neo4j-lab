# Lab 5: Databricks ETL to Neo4j

Load aircraft data from Databricks into Neo4j using the Spark Connector.

**Duration:** ~45 minutes

---

## Prerequisites

Before starting this lab, ensure you have:

- [ ] Neo4j Aura credentials from Lab 1 (URI, username, password)
- [ ] Access to the Databricks workspace (URL provided by instructor)
- [ ] Workshop login credentials

---

## Quick Start

1. **Log in** to Databricks workspace
2. **Start/verify** the workshop cluster is running
3. **Clone** the template notebook to your folder
4. **Enter** your Neo4j credentials
5. **Run All** cells
6. **Explore** the graph in Neo4j Aura

---

## Step-by-Step Instructions

### Part A: Access Databricks Workspace

1. Open the Databricks workspace URL provided by your instructor
2. Sign in with your workshop credentials
3. Navigate to **Compute** in the left sidebar
4. Verify the workshop cluster shows **Running** status
   - If stopped, click the cluster name and click **Start**
   - Wait for status to change to Running (may take 2-3 minutes)

### Part B: Clone the Notebook

1. Navigate to **Workspace** in the left sidebar
2. Go to the **Workshop_Materials** folder (or location specified by instructor)
3. Find the notebook: `aircraft_etl_to_neo4j_template`
4. Right-click the notebook and select **Clone**
5. Save the clone to your personal folder (e.g., `/Users/your-email/`)
6. Open your cloned notebook

### Part C: Configure and Run

1. Locate the **Configuration** cell (Section 1)
2. Enter your Neo4j Aura credentials:
   ```python
   NEO4J_URI = "neo4j+s://xxxxxxxx.databases.neo4j.io"  # Your URI
   NEO4J_USERNAME = "neo4j"
   NEO4J_PASSWORD = "your-password"  # Your password
   ```
3. Click **Run All** (or press Shift+Enter through each cell)
4. Watch the progress messages as data loads

### Part D: Verify Results

After running all cells, verify:

| Check | Expected Value |
|-------|----------------|
| Aircraft nodes | 20 |
| System nodes | 80 |
| Component nodes | 320 |
| HAS_SYSTEM relationships | 80 |
| HAS_COMPONENT relationships | 320 |

The verification cells at the end of the notebook will display these counts.

### Part E: Explore in Neo4j Aura

1. Open [console.neo4j.io](https://console.neo4j.io) in a new browser tab
2. Sign in and select your instance
3. Click **Query** to open the query interface
4. Try these visualization queries:

**See one aircraft's hierarchy:**
```cypher
MATCH (a:Aircraft {tail_number: 'N95040A'})-[r1:HAS_SYSTEM]->(s:System)-[r2:HAS_COMPONENT]->(c:Component)
RETURN a, r1, s, r2, c
```

**View fleet by manufacturer:**
```cypher
MATCH (a:Aircraft)
RETURN a.manufacturer AS Manufacturer, count(a) AS Count
```

**Explore component types:**
```cypher
MATCH (c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC
```

---

## What You Loaded

### Graph Structure

```
(Aircraft) -[:HAS_SYSTEM]-> (System) -[:HAS_COMPONENT]-> (Component)
```

### Data Summary

| Entity | Count | Description |
|--------|-------|-------------|
| Aircraft | 20 | Boeing 737-800, Airbus A320/A321, Embraer E190 |
| System | 80 | 2 engines + avionics + hydraulics per aircraft |
| Component | 320 | Fans, compressors, turbines, pumps, etc. |

### Sample Aircraft

| Tail Number | Model | Manufacturer | Operator |
|-------------|-------|--------------|----------|
| N95040A | B737-800 | Boeing | ExampleAir |
| N30268B | A320-200 | Airbus | SkyWays |
| N54980C | A321neo | Airbus | RegionalCo |
| N37272D | E190 | Embraer | NorthernJet |

---

## Troubleshooting

### "Connection refused" or timeout errors

- Verify your Neo4j URI starts with `neo4j+s://` (note the `+s`)
- Check your Neo4j Aura instance is running (green status in console)
- Confirm username and password are correct (no extra spaces)

### "Spark Connector not found" error

- Ensure you're using the workshop cluster (not a personal cluster)
- The cluster must be in **Dedicated (Single User)** access mode
- Try restarting the cluster

### "Path does not exist" for data files

- Verify the DATA_PATH matches your workshop configuration
- Ask your instructor for the correct Volume path

### Duplicate nodes appearing

- The notebook uses Overwrite mode, so re-running should replace data
- If needed, clear your Neo4j database first:
  ```cypher
  MATCH (n) DETACH DELETE n
  ```

### Notebook cells failing

- Run cells in order from top to bottom
- Don't skip the configuration cells
- Check the error message for specific issues

---

## Key Concepts Learned

1. **Unity Catalog Volumes** store files accessible from notebooks
2. **Neo4j Spark Connector** writes DataFrames directly to Neo4j
3. **Node loading** uses `labels` and `node.keys` options
4. **Relationship loading** uses `keys` strategy to match existing nodes
5. **Cypher queries** can be run from Databricks to verify data

---

## Next Steps

After completing this lab:
- Continue to **Phase 4** for Databricks Multi-Agent with AgentBricks
- The data you loaded will be queried by AI agents in later labs

---

## Help

- Ask your instructor for assistance
- Check the [Neo4j Spark Connector docs](https://neo4j.com/docs/spark/current/)
- Review the [Cypher Query Language reference](https://neo4j.com/docs/cypher-manual/current/)
