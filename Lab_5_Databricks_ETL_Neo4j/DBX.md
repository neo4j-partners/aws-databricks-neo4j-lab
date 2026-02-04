# Phase 3: Databricks ETL to Neo4j - Lab Proposal

**Phase Duration:** ~45 minutes
**Participant Skill Level:** Beginner
**Primary Goal:** Load aircraft data from Databricks to Neo4j using the Spark Connector

---

## Overview

This lab introduces participants to the Neo4j Spark Connector by loading a simplified subset of the Aircraft Digital Twin dataset from Databricks Unity Catalog into Neo4j Aura. Participants will experience the complete ETL workflow: reading data from Unity Catalog, transforming it for graph structure, and writing nodes and relationships to Neo4j.

### Design Philosophy

The lab is intentionally simplified to:
- Be completable in a short time window (~45 minutes)
- Focus on core concepts rather than complex transformations
- Use a small dataset that loads quickly and is easy to verify
- Provide clear success criteria with sample verification queries

---

## Simplified Data Model

### What We Load (Subset)

Instead of the full Aircraft Digital Twin dataset (9 node types, 11 relationship types), this lab loads a focused subset:

**Nodes (3 types):**
| Node Type | Count | Description |
|-----------|-------|-------------|
| Aircraft | 20 | Fleet aircraft with tail numbers, models, operators |
| System | 80 | Major systems (2 engines, avionics, hydraulics per aircraft) |
| Component | 320 | Parts within systems (fans, compressors, turbines, etc.) |

**Relationships (2 types):**
| Relationship | Pattern | Count | Description |
|--------------|---------|-------|-------------|
| HAS_SYSTEM | Aircraft -> System | 80 | Aircraft owns systems |
| HAS_COMPONENT | System -> Component | 320 | Systems contain components |

**Total:** ~420 nodes and ~400 relationships (small enough to load in seconds)

### Why This Subset?

1. **Hierarchical structure**: Demonstrates the Aircraft -> System -> Component hierarchy that's intuitive for graph thinking
2. **Small enough to verify**: Participants can count nodes and see the complete graph
3. **Fast loading**: No waiting for large data transfers
4. **No time-series complexity**: Avoids sensor readings which would require more time

---

## Participant Experience

### Pre-Configured Environment

Participants arrive to find:
- CSV files already uploaded to a Unity Catalog Volume
- A template notebook ready to clone and run
- Neo4j Aura credentials from Phase 1 (Lab 1)
- A pre-configured Databricks cluster with the Neo4j Spark Connector library

### Workflow Summary

1. **Part A: Access Workspace** - Log into Databricks, access the shared cluster
2. **Part B: Clone Notebook** - Right-click the template notebook and clone to their folder
3. **Part C: Understand Data Model** - Review CSV structure and graph mapping
4. **Part D: Load & Verify** - Run the notebook to load data and verify with queries (single notebook)
5. **Part E: Explore in Neo4j** - Open Neo4j Aura and visualize the graph

---

## Implementation Plan

### Part A: Databricks Workspace Access

**Objective:** Participants access the Databricks workspace and verify cluster connectivity.

**Steps:**
1. Navigate to the Databricks workspace URL provided by the instructor
2. Sign in with workshop credentials
3. Verify access to the shared compute cluster
4. Confirm the cluster is running (or start it if needed)

**Success Criteria:** Participant can see the workspace home page and the cluster shows "Running" status.

---

### Part B: Clone and Configure the Notebook

**Objective:** Participants get their own copy of the ETL notebook and configure Neo4j credentials.

**Steps:**
1. Navigate to the shared Workshop folder in the workspace
2. Find the template notebook: `aircraft_etl_to_neo4j_template`
3. Right-click and select "Clone"
4. Save the clone to their personal workspace folder
5. Open the cloned notebook
6. Locate the configuration cell and enter their Neo4j Aura credentials:
   - NEO4J_URI (from Lab 1)
   - NEO4J_USERNAME (typically "neo4j")
   - NEO4J_PASSWORD (from Lab 1)

**Success Criteria:** Notebook opens with a green checkmark on the cluster attachment and credentials cell is populated.

---

### Part C: Understand the Data Model

**Objective:** Participants understand how CSV data maps to graph nodes and relationships.

**Educational Content in Notebook:**
1. **Show the source data** - Display sample rows from each CSV file
   - `nodes_aircraft.csv`: See aircraft_id, tail_number, model, manufacturer, operator
   - `nodes_systems.csv`: See system_id, aircraft_id, type, name
   - `nodes_components.csv`: See component_id, system_id, type, name

2. **Explain the mapping:**
   - Each row becomes a node
   - Column values become node properties
   - Foreign keys (aircraft_id in systems, system_id in components) become relationships
   - The relationship CSV files define the graph connections

3. **Show the target graph structure:**
   ```
   (Aircraft) -[:HAS_SYSTEM]-> (System) -[:HAS_COMPONENT]-> (Component)
   ```

**Success Criteria:** Participant can articulate that "aircraft_id links Aircraft to System nodes" and "system_id links System to Component nodes."

---

### Part D: Load Data and Verify (Single Notebook)

**Objective:** Participants execute the notebook to load nodes and relationships into Neo4j, then verify the data loaded correctly.

> **Note:** Parts D (Load) and E (Verify) are combined into a single notebook that participants run from start to finish. The notebook handles both loading and verification in one cohesive workflow.

**Notebook Structure:**

**Section 1: Introduction & Configuration**
- Markdown cell explaining the lab objectives
- Configuration cell for Neo4j credentials (participants fill in)
- Spark configuration cell to set up the connector

**Section 2: Data Preview**
- Read CSV files from Unity Catalog Volume
- Display sample rows from each file
- Show row counts
- Markdown explaining the data model mapping

**Section 3: Load Nodes**
- Transform DataFrames (rename ID columns)
- Write Aircraft nodes to Neo4j
- Write System nodes to Neo4j
- Write Component nodes to Neo4j
- Print progress after each write

**Section 4: Load Relationships**
- Read relationship CSVs
- Transform column names to match node keys
- Write HAS_SYSTEM relationships
- Write HAS_COMPONENT relationships
- Print "ETL Complete" summary with counts

**Section 5: Verification Queries**
- Helper function to run Cypher queries from Spark
- Count nodes by label (expected: Aircraft=20, System=80, Component=320)
- Count relationships by type (expected: HAS_SYSTEM=80, HAS_COMPONENT=320)
- Sample query: View aircraft N95040A hierarchy
- Sample query: Find Boeing aircraft

**Section 6: Next Steps**
- Markdown with instructions to explore in Neo4j Aura
- Sample visualization queries to try in Aura console

**Verification Queries (included in notebook):**

1. **Count all nodes:**
   ```cypher
   MATCH (n) RETURN labels(n) AS NodeType, count(*) AS Count
   ```
   Expected: Aircraft=20, System=80, Component=320

2. **Count all relationships:**
   ```cypher
   MATCH ()-[r]->() RETURN type(r) AS RelType, count(*) AS Count
   ```
   Expected: HAS_SYSTEM=80, HAS_COMPONENT=320

3. **View one aircraft's full hierarchy:**
   ```cypher
   MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)
   OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
   RETURN a.tail_number, s.name AS system, collect(c.name) AS components
   ```

**Success Criteria:** All notebook cells execute without errors. Verification queries return expected counts.

---

### Part E: Explore Data in Neo4j Aura

**Objective:** Participants visualize the loaded graph in Neo4j Aura console.

**Steps:**
1. Open Neo4j Aura console in a browser
2. Connect to their instance
3. Open the Query tab
4. Run visualization queries:

**Visualization Query 1: See the full graph**
```cypher
MATCH (a:Aircraft)-[r1:HAS_SYSTEM]->(s:System)-[r2:HAS_COMPONENT]->(c:Component)
WHERE a.tail_number = 'N95040A'
RETURN a, r1, s, r2, c
```

**Visualization Query 2: Compare aircraft by manufacturer**
```cypher
MATCH (a:Aircraft)
RETURN a.manufacturer AS Manufacturer, count(a) AS AircraftCount
```

**Visualization Query 3: Find component types across the fleet**
```cypher
MATCH (c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC
```

**Exploration Activity:**
- Click on nodes to see their properties
- Expand nodes to see connected systems and components
- Use the graph visualization to understand the hierarchy

**Success Criteria:** Participant can visualize an aircraft with its connected systems and components as a graph.

---

## Key Learning Outcomes

By completing this lab, participants will be able to:

1. **Describe** how tabular CSV data maps to graph nodes and relationships
2. **Configure** the Neo4j Spark Connector in Databricks
3. **Execute** a data load pipeline using the Spark Connector write format
4. **Verify** data integrity using Cypher queries from Databricks
5. **Visualize** hierarchical data as a connected graph in Neo4j Aura

---

## Data Files Required

Located in the setup directory: `Lab_5_Databricks_ETL_Neo4j/setup/aircraft_digital_twin_data/`

**Node Files:**
| File | Records | Description |
|------|---------|-------------|
| `nodes_aircraft.csv` | 20 | Aircraft fleet |
| `nodes_systems.csv` | 80 | Aircraft systems |
| `nodes_components.csv` | 320 | System components |

**Relationship Files:**
| File | Records | Description |
|------|---------|-------------|
| `rels_aircraft_system.csv` | 80 | Aircraft -> System |
| `rels_system_component.csv` | 320 | System -> Component |

**Total CSV size:** ~50KB (very small, loads in seconds)

---

## Technical Requirements

### Databricks Cluster Configuration

**Access Mode:** Dedicated (Single User) - Required for Spark Connector JARs

**Library:**
- Maven coordinate: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.x_for_spark_3`
- Must be installed on the cluster before the workshop

### Neo4j Aura Requirements

- Instance must be running (created in Lab 1)
- Connection URI, username, and password available
- Database should be empty or participants should be prepared to see existing data

---

## Troubleshooting Guide

**Issue: Connection refused to Neo4j**
- Verify the URI starts with `neo4j+s://` (for Aura)
- Check credentials are correct
- Ensure the Aura instance is running

**Issue: Spark Connector not found**
- Verify cluster is in Dedicated (Single User) mode
- Check the Maven library is installed on the cluster
- Restart the cluster if library was just added

**Issue: Data not appearing in Neo4j**
- Run the count queries to verify
- Check for errors in notebook cell outputs
- Verify the correct database is selected in Aura console

**Issue: Duplicate nodes appearing**
- The notebook should use "Overwrite" mode for repeatability
- Or add MERGE-like behavior with unique constraints

---

## Extension Activities (Optional)

For participants who finish early:

1. **Add Operators:** Create Operator nodes and OPERATES relationship from the operator property
2. **Query Patterns:** Write queries to find aircraft with the most components
3. **Data Quality:** Add a validation cell that checks referential integrity
4. **Visualization:** Export the graph image and annotate the hierarchy

---

## References

- [Neo4j Spark Connector Documentation](https://neo4j.com/docs/spark/current/)
- [Databricks Unity Catalog Volumes](https://docs.databricks.com/en/connect/unity-catalog/volumes.html)
- [Neo4j Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)

---

## Artifacts to Create

The following artifacts need to be created to deliver this lab:

### Required Artifacts

| Artifact | Location | Status | Description |
|----------|----------|--------|-------------|
| **DBX.md** | `Lab_5_Databricks_ETL_Neo4j/DBX.md` | Complete | This proposal document |
| **Admin Setup Guide** | `Lab_5_Databricks_ETL_Neo4j/setup/README.md` | Complete | Instructions for lab administrators |
| **ETL Notebook** | `Lab_5_Databricks_ETL_Neo4j/aircraft_etl_to_neo4j.ipynb` | Complete | Jupyter notebook (ipynb format) |
| **Participant README** | `Lab_5_Databricks_ETL_Neo4j/README.md` | Complete | Step-by-step guide for participants |

### Data Files (Already Exist)

| File | Location | Status |
|------|----------|--------|
| `nodes_aircraft.csv` | `setup/aircraft_digital_twin_data/` | Exists |
| `nodes_systems.csv` | `setup/aircraft_digital_twin_data/` | Exists |
| `nodes_components.csv` | `setup/aircraft_digital_twin_data/` | Exists |
| `rels_aircraft_system.csv` | `setup/aircraft_digital_twin_data/` | Exists |
| `rels_system_component.csv` | `setup/aircraft_digital_twin_data/` | Exists |

### Artifact Details

#### 1. ETL Notebook (`aircraft_etl_to_neo4j.ipynb`)

A Jupyter notebook that can be imported directly into Databricks. Contains 6 sections with ~30 cells:
- **Section 1:** Introduction & Configuration (credentials input)
- **Section 2:** Data Preview (read and display CSVs)
- **Section 3:** Load Nodes (Aircraft, System, Component)
- **Section 4:** Load Relationships (HAS_SYSTEM, HAS_COMPONENT)
- **Section 5:** Verification Queries (counts, sample queries)
- **Section 6:** Next Steps (Neo4j Aura exploration guidance)

**Format:** Jupyter notebook (`.ipynb`) following nbformat v4.5+ specification

**To import:** In Databricks, go to Workspace > Import > select the `.ipynb` file

#### 2. Participant README (`README.md`)

A concise guide for participants covering:
- Prerequisites checklist
- Quick start (6 steps)
- Detailed step-by-step instructions for Parts A-E
- Expected results table
- Data summary and sample queries
- Troubleshooting guide with common issues
- Key concepts learned

### Optional Enhancements

| Artifact | Purpose | Priority |
|----------|---------|----------|
| Architecture diagram | Visual showing Aircraft -> System -> Component | Nice to have |
| Solution notebook | Completed notebook with sample output for instructors | Recommended |

---

## Next Steps

After completing this lab, participants will:
- Move to **Phase 4: Databricks Multi-Agent with AgentBricks** where they configure a Genie space and multi-agent supervisor
- Use the data loaded in this phase as part of the integrated multi-agent system
