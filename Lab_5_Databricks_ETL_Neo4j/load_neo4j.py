"""
Aircraft Digital Twin - Neo4j Data Loader for Databricks

Loads the complete aircraft digital twin dataset into Neo4j, including:
- Core aircraft structure (Aircraft, System, Component, Sensor)
- Operational data (Airport, Flight, Delay)
- Maintenance events and part removals

Usage in Databricks:
    %run ./load_neo4j

Or execute directly:
    exec(open("/Workspace/path/to/load_neo4j.py").read())

Prerequisites:
    1. Databricks Secrets configured in scope "neo4j-creds":
       - uri: Neo4j connection URI (e.g., neo4j+s://xxx.databases.neo4j.io)
       - username: Neo4j username (default: neo4j)
       - password: Neo4j password
    2. CSV data files uploaded to Unity Catalog Volume
    3. neo4j Python package installed on cluster
"""

import time
from typing import Any

from neo4j import GraphDatabase

# =============================================================================
# CONFIGURATION
# =============================================================================

SCOPE_NAME = "neo4j-creds"

# Path to CSV files in Unity Catalog Volume
# Update this to match your volume path
DATA_VOLUME_PATH = "/Volumes/main/default/aircraft_data"

# Batch size for transaction handling
BATCH_SIZE = 1000


def load_config() -> dict:
    """Load Neo4j configuration from Databricks Secrets."""
    print("=" * 60)
    print("LOADING CONFIGURATION")
    print("=" * 60)

    config = {}

    try:
        config["uri"] = dbutils.secrets.get(SCOPE_NAME, "uri")
        print("  [OK] uri: retrieved")
    except Exception as e:
        print(f"  [FAIL] uri: {e}")
        raise

    try:
        config["username"] = dbutils.secrets.get(SCOPE_NAME, "username")
        print("  [OK] username: retrieved")
    except Exception:
        config["username"] = "neo4j"
        print("  [OK] username: using default 'neo4j'")

    try:
        config["password"] = dbutils.secrets.get(SCOPE_NAME, "password")
        print("  [OK] password: retrieved")
    except Exception as e:
        print(f"  [FAIL] password: {e}")
        raise

    print(f"\n  URI: {config['uri']}")

    return config


# =============================================================================
# CSV READING
# =============================================================================

def read_csv(file_path: str) -> list[dict[str, Any]]:
    """Read CSV file from UC Volume and return list of dictionaries."""
    import csv

    full_path = f"{DATA_VOLUME_PATH}/{file_path}"
    print(f"    Reading: {full_path}")

    with open(full_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def run_in_batches(driver, records: list[dict], query: str, batch_size: int = BATCH_SIZE):
    """Execute a query for records in batches."""
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        with driver.session() as session:
            session.run(query, {"batch": batch})
        progress = min(i + batch_size, total)
        print(f"    Progress: {progress}/{total} ({100 * progress // total}%)", end="\r")
    print()


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def clear_database(driver):
    """Clear all nodes and relationships from the database."""
    print("\nClearing database...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("  [OK] Database cleared.")


def create_constraints(driver):
    """Create uniqueness constraints for all node types."""
    print("\nCreating constraints...")
    constraints = [
        ("Aircraft", "aircraft_id"),
        ("System", "system_id"),
        ("Component", "component_id"),
        ("Sensor", "sensor_id"),
        ("Airport", "airport_id"),
        ("Flight", "flight_id"),
        ("Delay", "delay_id"),
        ("MaintenanceEvent", "event_id"),
        ("Removal", "removal_id"),
    ]

    with driver.session() as session:
        for label, prop in constraints:
            try:
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                )
                print(f"  [OK] Constraint: {label}.{prop}")
            except Exception as e:
                print(f"  [WARN] Could not create constraint for {label}.{prop}: {e}")


def create_indexes(driver):
    """Create additional indexes for query performance."""
    print("\nCreating indexes...")
    indexes = [
        ("MaintenanceEvent", "severity"),
        ("Flight", "aircraft_id"),
        ("Removal", "aircraft_id"),
    ]

    with driver.session() as session:
        for label, prop in indexes:
            try:
                index_name = f"idx_{label.lower()}_{prop.lower()}"
                session.run(f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})")
                print(f"  [OK] Index: {label}.{prop}")
            except Exception as e:
                print(f"  [WARN] Could not create index for {label}.{prop}: {e}")


# =============================================================================
# NODE LOADERS
# =============================================================================

def load_aircraft(driver):
    """Load Aircraft nodes."""
    print("\nLoading Aircraft nodes...")
    records = read_csv("nodes_aircraft.csv")

    query = """
    UNWIND $batch AS row
    CREATE (a:Aircraft {
        aircraft_id: row[':ID(Aircraft)'],
        tail_number: row['tail_number'],
        icao24: row['icao24'],
        model: row['model'],
        manufacturer: row['manufacturer'],
        operator: row['operator']
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} aircraft.")


def load_systems(driver):
    """Load System nodes."""
    print("\nLoading System nodes...")
    records = read_csv("nodes_systems.csv")

    query = """
    UNWIND $batch AS row
    CREATE (s:System {
        system_id: row[':ID(System)'],
        aircraft_id: row['aircraft_id'],
        type: row['type'],
        name: row['name']
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} systems.")


def load_components(driver):
    """Load Component nodes."""
    print("\nLoading Component nodes...")
    records = read_csv("nodes_components.csv")

    query = """
    UNWIND $batch AS row
    CREATE (c:Component {
        component_id: row[':ID(Component)'],
        system_id: row['system_id'],
        type: row['type'],
        name: row['name']
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} components.")


def load_sensors(driver):
    """Load Sensor nodes."""
    print("\nLoading Sensor nodes...")
    records = read_csv("nodes_sensors.csv")

    query = """
    UNWIND $batch AS row
    CREATE (s:Sensor {
        sensor_id: row[':ID(Sensor)'],
        system_id: row['system_id'],
        type: row['type'],
        name: row['name'],
        unit: row['unit']
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} sensors.")


def load_airports(driver):
    """Load Airport nodes."""
    print("\nLoading Airport nodes...")
    records = read_csv("nodes_airports.csv")

    query = """
    UNWIND $batch AS row
    CREATE (a:Airport {
        airport_id: row[':ID(Airport)'],
        name: row['name'],
        city: row['city'],
        country: row['country'],
        iata: row['iata'],
        icao: row['icao'],
        lat: toFloat(row['lat']),
        lon: toFloat(row['lon'])
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} airports.")


def load_flights(driver):
    """Load Flight nodes."""
    print("\nLoading Flight nodes...")
    records = read_csv("nodes_flights.csv")

    query = """
    UNWIND $batch AS row
    CREATE (f:Flight {
        flight_id: row[':ID(Flight)'],
        flight_number: row['flight_number'],
        aircraft_id: row['aircraft_id'],
        operator: row['operator'],
        origin: row['origin'],
        destination: row['destination'],
        scheduled_departure: row['scheduled_departure'],
        scheduled_arrival: row['scheduled_arrival']
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} flights.")


def load_delays(driver):
    """Load Delay nodes."""
    print("\nLoading Delay nodes...")
    records = read_csv("nodes_delays.csv")

    query = """
    UNWIND $batch AS row
    CREATE (d:Delay {
        delay_id: row[':ID(Delay)'],
        cause: row['cause'],
        minutes: toInteger(row['minutes'])
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} delays.")


def load_maintenance_events(driver):
    """Load MaintenanceEvent nodes."""
    print("\nLoading MaintenanceEvent nodes...")
    records = read_csv("nodes_maintenance.csv")

    query = """
    UNWIND $batch AS row
    CREATE (m:MaintenanceEvent {
        event_id: row[':ID(MaintenanceEvent)'],
        component_id: row['component_id'],
        system_id: row['system_id'],
        aircraft_id: row['aircraft_id'],
        fault: row['fault'],
        severity: row['severity'],
        reported_at: row['reported_at'],
        corrective_action: row['corrective_action']
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} maintenance events.")


def load_removals(driver):
    """Load Removal nodes."""
    print("\nLoading Removal nodes...")
    records = read_csv("nodes_removals.csv")

    query = """
    UNWIND $batch AS row
    CREATE (r:Removal {
        removal_id: row[':ID(Removal)'],
        component_id: row['component_id'],
        aircraft_id: row['aircraft_id'],
        removal_date: row['removal_date'],
        reason: row['reason'],
        tsn: toFloat(row['tsn']),
        csn: toInteger(row['csn'])
    })
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} removals.")


# =============================================================================
# RELATIONSHIP LOADERS
# =============================================================================

def load_relationships(driver):
    """Load all relationships."""
    print("\n" + "=" * 60)
    print("LOADING RELATIONSHIPS")
    print("=" * 60)

    # HAS_SYSTEM: Aircraft -> System
    print("\n  Loading HAS_SYSTEM relationships...")
    records = read_csv("rels_aircraft_system.csv")
    query = """
    UNWIND $batch AS row
    MATCH (a:Aircraft {aircraft_id: row[':START_ID(Aircraft)']})
    MATCH (s:System {system_id: row[':END_ID(System)']})
    CREATE (a)-[:HAS_SYSTEM]->(s)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} HAS_SYSTEM relationships.")

    # HAS_COMPONENT: System -> Component
    print("\n  Loading HAS_COMPONENT relationships...")
    records = read_csv("rels_system_component.csv")
    query = """
    UNWIND $batch AS row
    MATCH (s:System {system_id: row[':START_ID(System)']})
    MATCH (c:Component {component_id: row[':END_ID(Component)']})
    CREATE (s)-[:HAS_COMPONENT]->(c)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} HAS_COMPONENT relationships.")

    # HAS_SENSOR: System -> Sensor
    print("\n  Loading HAS_SENSOR relationships...")
    records = read_csv("rels_system_sensor.csv")
    query = """
    UNWIND $batch AS row
    MATCH (s:System {system_id: row[':START_ID(System)']})
    MATCH (sn:Sensor {sensor_id: row[':END_ID(Sensor)']})
    CREATE (s)-[:HAS_SENSOR]->(sn)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} HAS_SENSOR relationships.")

    # HAS_EVENT: Component -> MaintenanceEvent
    print("\n  Loading HAS_EVENT relationships...")
    records = read_csv("rels_component_event.csv")
    query = """
    UNWIND $batch AS row
    MATCH (c:Component {component_id: row[':START_ID(Component)']})
    MATCH (m:MaintenanceEvent {event_id: row[':END_ID(MaintenanceEvent)']})
    CREATE (c)-[:HAS_EVENT]->(m)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} HAS_EVENT relationships.")

    # OPERATES_FLIGHT: Aircraft -> Flight
    print("\n  Loading OPERATES_FLIGHT relationships...")
    records = read_csv("rels_aircraft_flight.csv")
    query = """
    UNWIND $batch AS row
    MATCH (a:Aircraft {aircraft_id: row[':START_ID(Aircraft)']})
    MATCH (f:Flight {flight_id: row[':END_ID(Flight)']})
    CREATE (a)-[:OPERATES_FLIGHT]->(f)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} OPERATES_FLIGHT relationships.")

    # DEPARTS_FROM: Flight -> Airport
    print("\n  Loading DEPARTS_FROM relationships...")
    records = read_csv("rels_flight_departure.csv")
    query = """
    UNWIND $batch AS row
    MATCH (f:Flight {flight_id: row[':START_ID(Flight)']})
    MATCH (a:Airport {airport_id: row[':END_ID(Airport)']})
    CREATE (f)-[:DEPARTS_FROM]->(a)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} DEPARTS_FROM relationships.")

    # ARRIVES_AT: Flight -> Airport
    print("\n  Loading ARRIVES_AT relationships...")
    records = read_csv("rels_flight_arrival.csv")
    query = """
    UNWIND $batch AS row
    MATCH (f:Flight {flight_id: row[':START_ID(Flight)']})
    MATCH (a:Airport {airport_id: row[':END_ID(Airport)']})
    CREATE (f)-[:ARRIVES_AT]->(a)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} ARRIVES_AT relationships.")

    # HAS_DELAY: Flight -> Delay
    print("\n  Loading HAS_DELAY relationships...")
    records = read_csv("rels_flight_delay.csv")
    query = """
    UNWIND $batch AS row
    MATCH (f:Flight {flight_id: row[':START_ID(Flight)']})
    MATCH (d:Delay {delay_id: row[':END_ID(Delay)']})
    CREATE (f)-[:HAS_DELAY]->(d)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} HAS_DELAY relationships.")

    # AFFECTS_SYSTEM: MaintenanceEvent -> System
    print("\n  Loading AFFECTS_SYSTEM relationships...")
    records = read_csv("rels_event_system.csv")
    query = """
    UNWIND $batch AS row
    MATCH (m:MaintenanceEvent {event_id: row[':START_ID(MaintenanceEvent)']})
    MATCH (s:System {system_id: row[':END_ID(System)']})
    CREATE (m)-[:AFFECTS_SYSTEM]->(s)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} AFFECTS_SYSTEM relationships.")

    # AFFECTS_AIRCRAFT: MaintenanceEvent -> Aircraft
    print("\n  Loading AFFECTS_AIRCRAFT relationships...")
    records = read_csv("rels_event_aircraft.csv")
    query = """
    UNWIND $batch AS row
    MATCH (m:MaintenanceEvent {event_id: row[':START_ID(MaintenanceEvent)']})
    MATCH (a:Aircraft {aircraft_id: row[':END_ID(Aircraft)']})
    CREATE (m)-[:AFFECTS_AIRCRAFT]->(a)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} AFFECTS_AIRCRAFT relationships.")

    # HAS_REMOVAL: Aircraft -> Removal
    print("\n  Loading HAS_REMOVAL relationships...")
    records = read_csv("rels_aircraft_removal.csv")
    query = """
    UNWIND $batch AS row
    MATCH (a:Aircraft {aircraft_id: row[':START_ID(Aircraft)']})
    MATCH (r:Removal {removal_id: row[':END_ID(Removal)']})
    CREATE (a)-[:HAS_REMOVAL]->(r)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} HAS_REMOVAL relationships.")

    # REMOVED_COMPONENT: Removal -> Component
    print("\n  Loading REMOVED_COMPONENT relationships...")
    records = read_csv("rels_component_removal.csv")
    query = """
    UNWIND $batch AS row
    MATCH (r:Removal {removal_id: row[':START_ID(Removal)']})
    MATCH (c:Component {component_id: row[':END_ID(Component)']})
    CREATE (r)-[:REMOVED_COMPONENT]->(c)
    """
    run_in_batches(driver, records, query)
    print(f"  [OK] Loaded {len(records)} REMOVED_COMPONENT relationships.")


# =============================================================================
# SUMMARY
# =============================================================================

def print_summary(driver):
    """Print a summary of loaded data."""
    print("\n" + "=" * 60)
    print("LOAD COMPLETE - Summary")
    print("=" * 60)

    with driver.session() as session:
        # Count nodes
        node_counts = session.run("""
            CALL {
                MATCH (n:Aircraft) RETURN 'Aircraft' as label, count(n) as count
                UNION ALL
                MATCH (n:System) RETURN 'System' as label, count(n) as count
                UNION ALL
                MATCH (n:Component) RETURN 'Component' as label, count(n) as count
                UNION ALL
                MATCH (n:Sensor) RETURN 'Sensor' as label, count(n) as count
                UNION ALL
                MATCH (n:Airport) RETURN 'Airport' as label, count(n) as count
                UNION ALL
                MATCH (n:Flight) RETURN 'Flight' as label, count(n) as count
                UNION ALL
                MATCH (n:Delay) RETURN 'Delay' as label, count(n) as count
                UNION ALL
                MATCH (n:MaintenanceEvent) RETURN 'MaintenanceEvent' as label, count(n) as count
                UNION ALL
                MATCH (n:Removal) RETURN 'Removal' as label, count(n) as count
            }
            RETURN label, count
            ORDER BY count DESC
        """).data()

        print("\nNode Counts:")
        for row in node_counts:
            print(f"  {row['label']}: {row['count']:,}")

        # Count relationships
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        print(f"\nTotal Relationships: {rel_count:,}")

    print("\n" + "=" * 60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main(clear_db: bool = False):
    """
    Run the Neo4j data loader.

    Args:
        clear_db: If True, clear the database before loading
    """
    print("\n" + "=" * 60)
    print("AIRCRAFT DIGITAL TWIN - NEO4J DATA LOADER")
    print("=" * 60)
    print(f"\nData source: {DATA_VOLUME_PATH}")
    print(f"Clear database: {clear_db}\n")

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"\n[FATAL] Failed to load configuration: {e}")
        print(f"\nEnsure Databricks Secrets are configured in scope '{SCOPE_NAME}'")
        print("Required secrets: uri, password")
        print("Optional secrets: username (defaults to 'neo4j')")
        return

    # Connect to Neo4j
    print(f"\nConnecting to Neo4j at {config['uri']}...")
    driver = GraphDatabase.driver(
        config["uri"],
        auth=(config["username"], config["password"])
    )

    try:
        # Verify connection
        start = time.time()
        driver.verify_connectivity()
        elapsed = (time.time() - start) * 1000
        print(f"  [OK] Connected in {elapsed:.0f}ms")

        # Clear database if requested
        if clear_db:
            clear_database(driver)

        # Create constraints and indexes
        create_constraints(driver)
        create_indexes(driver)

        # Load nodes
        print("\n" + "=" * 60)
        print("LOADING NODES")
        print("=" * 60)
        load_aircraft(driver)
        load_systems(driver)
        load_components(driver)
        load_sensors(driver)
        load_airports(driver)
        load_flights(driver)
        load_delays(driver)
        load_maintenance_events(driver)
        load_removals(driver)

        # Load relationships
        load_relationships(driver)

        # Print summary
        print_summary(driver)

    except Exception as e:
        print(f"\n[FATAL] Error: {e}")
        raise
    finally:
        driver.close()

    print("\n" + "=" * 60)
    print("LOADER COMPLETE")
    print("=" * 60)


# =============================================================================
# EXECUTE
# =============================================================================

if __name__ == "__main__":
    # When run directly, clear and reload
    main(clear_db=True)
else:
    # When run via %run or exec(), also execute main
    # Pass clear_db=True to start fresh
    main(clear_db=True)
