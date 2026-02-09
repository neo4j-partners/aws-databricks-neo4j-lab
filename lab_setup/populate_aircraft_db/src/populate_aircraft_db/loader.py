"""CSV reading, batched loading, database clearing, and verification."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from neo4j import Driver

BATCH_SIZE = 1000

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def read_csv(data_dir: Path, filename: str) -> list[dict[str, Any]]:
    """Read a CSV file and return a list of row dicts."""
    path = data_dir / filename
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _run_in_batches(driver: Driver, records: list[dict], query: str) -> None:
    """Execute a Cypher query over records in batches of BATCH_SIZE."""
    total = len(records)
    for i in range(0, total, BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        driver.execute_query(query, batch=batch)
        progress = min(i + BATCH_SIZE, total)
        print(f"  Progress: {progress}/{total} ({100 * progress // total}%)", end="\r")
    print()


# ---------------------------------------------------------------------------
# Node loading — matches notebook 02 Cypher exactly
# ---------------------------------------------------------------------------

_NODE_DEFINITIONS: list[tuple[str, str, str]] = [
    (
        "Aircraft",
        "nodes_aircraft.csv",
        """
        UNWIND $batch AS row
        MERGE (a:Aircraft {aircraft_id: row[':ID(Aircraft)']})
        SET a.tail_number = row['tail_number'],
            a.icao24 = row['icao24'],
            a.model = row['model'],
            a.manufacturer = row['manufacturer'],
            a.operator = row['operator']
        """,
    ),
    (
        "System",
        "nodes_systems.csv",
        """
        UNWIND $batch AS row
        MERGE (s:System {system_id: row[':ID(System)']})
        SET s.aircraft_id = row['aircraft_id'],
            s.type = row['type'],
            s.name = row['name']
        """,
    ),
    (
        "Component",
        "nodes_components.csv",
        """
        UNWIND $batch AS row
        MERGE (c:Component {component_id: row[':ID(Component)']})
        SET c.system_id = row['system_id'],
            c.type = row['type'],
            c.name = row['name']
        """,
    ),
    (
        "Sensor",
        "nodes_sensors.csv",
        """
        UNWIND $batch AS row
        MERGE (s:Sensor {sensor_id: row[':ID(Sensor)']})
        SET s.system_id = row['system_id'],
            s.type = row['type'],
            s.name = row['name'],
            s.unit = row['unit']
        """,
    ),
    (
        "Airport",
        "nodes_airports.csv",
        """
        UNWIND $batch AS row
        MERGE (a:Airport {airport_id: row[':ID(Airport)']})
        SET a.name = row['name'],
            a.city = row['city'],
            a.country = row['country'],
            a.iata = row['iata'],
            a.icao = row['icao'],
            a.lat = toFloat(row['lat']),
            a.lon = toFloat(row['lon'])
        """,
    ),
    (
        "Flight",
        "nodes_flights.csv",
        """
        UNWIND $batch AS row
        MERGE (f:Flight {flight_id: row[':ID(Flight)']})
        SET f.flight_number = row['flight_number'],
            f.aircraft_id = row['aircraft_id'],
            f.operator = row['operator'],
            f.origin = row['origin'],
            f.destination = row['destination'],
            f.scheduled_departure = row['scheduled_departure'],
            f.scheduled_arrival = row['scheduled_arrival']
        """,
    ),
    (
        "Delay",
        "nodes_delays.csv",
        """
        UNWIND $batch AS row
        MERGE (d:Delay {delay_id: row[':ID(Delay)']})
        SET d.cause = row['cause'],
            d.minutes = toInteger(row['minutes'])
        """,
    ),
    (
        "MaintenanceEvent",
        "nodes_maintenance.csv",
        """
        UNWIND $batch AS row
        MERGE (m:MaintenanceEvent {event_id: row[':ID(MaintenanceEvent)']})
        SET m.component_id = row['component_id'],
            m.system_id = row['system_id'],
            m.aircraft_id = row['aircraft_id'],
            m.fault = row['fault'],
            m.severity = row['severity'],
            m.reported_at = row['reported_at'],
            m.corrective_action = row['corrective_action']
        """,
    ),
    (
        "Removal",
        "nodes_removals.csv",
        """
        UNWIND $batch AS row
        MERGE (r:Removal {removal_id: row[':ID(RemovalEvent)']})
        SET r.component_id = row['component_id'],
            r.aircraft_id = row['aircraft_id'],
            r.removal_date = row['removal_date'],
            r.reason = row['RMV_REA_TX'],
            r.tsn = toFloat(row['time_since_install']),
            r.csn = toInteger(row['flight_cycles_at_removal'])
        """,
    ),
]

# ---------------------------------------------------------------------------
# Relationship loading — matches notebook 02 Cypher exactly
# ---------------------------------------------------------------------------

_REL_DEFINITIONS: list[tuple[str, str, str]] = [
    (
        "HAS_SYSTEM",
        "rels_aircraft_system.csv",
        """
        UNWIND $batch AS row
        MATCH (a:Aircraft {aircraft_id: row[':START_ID(Aircraft)']})
        MATCH (s:System {system_id: row[':END_ID(System)']})
        MERGE (a)-[:HAS_SYSTEM]->(s)
        """,
    ),
    (
        "HAS_COMPONENT",
        "rels_system_component.csv",
        """
        UNWIND $batch AS row
        MATCH (s:System {system_id: row[':START_ID(System)']})
        MATCH (c:Component {component_id: row[':END_ID(Component)']})
        MERGE (s)-[:HAS_COMPONENT]->(c)
        """,
    ),
    (
        "HAS_SENSOR",
        "rels_system_sensor.csv",
        """
        UNWIND $batch AS row
        MATCH (s:System {system_id: row[':START_ID(System)']})
        MATCH (sn:Sensor {sensor_id: row[':END_ID(Sensor)']})
        MERGE (s)-[:HAS_SENSOR]->(sn)
        """,
    ),
    (
        "HAS_EVENT",
        "rels_component_event.csv",
        """
        UNWIND $batch AS row
        MATCH (c:Component {component_id: row[':START_ID(Component)']})
        MATCH (m:MaintenanceEvent {event_id: row[':END_ID(MaintenanceEvent)']})
        MERGE (c)-[:HAS_EVENT]->(m)
        """,
    ),
    (
        "OPERATES_FLIGHT",
        "rels_aircraft_flight.csv",
        """
        UNWIND $batch AS row
        MATCH (a:Aircraft {aircraft_id: row[':START_ID(Aircraft)']})
        MATCH (f:Flight {flight_id: row[':END_ID(Flight)']})
        MERGE (a)-[:OPERATES_FLIGHT]->(f)
        """,
    ),
    (
        "DEPARTS_FROM",
        "rels_flight_departure.csv",
        """
        UNWIND $batch AS row
        MATCH (f:Flight {flight_id: row[':START_ID(Flight)']})
        MATCH (a:Airport {airport_id: row[':END_ID(Airport)']})
        MERGE (f)-[:DEPARTS_FROM]->(a)
        """,
    ),
    (
        "ARRIVES_AT",
        "rels_flight_arrival.csv",
        """
        UNWIND $batch AS row
        MATCH (f:Flight {flight_id: row[':START_ID(Flight)']})
        MATCH (a:Airport {airport_id: row[':END_ID(Airport)']})
        MERGE (f)-[:ARRIVES_AT]->(a)
        """,
    ),
    (
        "HAS_DELAY",
        "rels_flight_delay.csv",
        """
        UNWIND $batch AS row
        MATCH (f:Flight {flight_id: row[':START_ID(Flight)']})
        MATCH (d:Delay {delay_id: row[':END_ID(Delay)']})
        MERGE (f)-[:HAS_DELAY]->(d)
        """,
    ),
    (
        "AFFECTS_SYSTEM",
        "rels_event_system.csv",
        """
        UNWIND $batch AS row
        MATCH (m:MaintenanceEvent {event_id: row[':START_ID(MaintenanceEvent)']})
        MATCH (s:System {system_id: row[':END_ID(System)']})
        MERGE (m)-[:AFFECTS_SYSTEM]->(s)
        """,
    ),
    (
        "AFFECTS_AIRCRAFT",
        "rels_event_aircraft.csv",
        """
        UNWIND $batch AS row
        MATCH (m:MaintenanceEvent {event_id: row[':START_ID(MaintenanceEvent)']})
        MATCH (a:Aircraft {aircraft_id: row[':END_ID(Aircraft)']})
        MERGE (m)-[:AFFECTS_AIRCRAFT]->(a)
        """,
    ),
    (
        "HAS_REMOVAL",
        "rels_aircraft_removal.csv",
        """
        UNWIND $batch AS row
        MATCH (a:Aircraft {aircraft_id: row[':START_ID(Aircraft)']})
        MATCH (r:Removal {removal_id: row[':END_ID(RemovalEvent)']})
        MERGE (a)-[:HAS_REMOVAL]->(r)
        """,
    ),
    (
        "REMOVED_COMPONENT",
        "rels_component_removal.csv",
        """
        UNWIND $batch AS row
        MATCH (r:Removal {removal_id: row[':END_ID(RemovalEvent)']})
        MATCH (c:Component {component_id: row[':START_ID(Component)']})
        MERGE (r)-[:REMOVED_COMPONENT]->(c)
        """,
    ),
]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_nodes(driver: Driver, data_dir: Path) -> None:
    """Load all 9 node types from CSV files."""
    for label, filename, query in _NODE_DEFINITIONS:
        print(f"Loading {label} nodes...")
        records = read_csv(data_dir, filename)
        _run_in_batches(driver, records, query)
        print(f"  [OK] Loaded {len(records)} {label} nodes.")


def load_relationships(driver: Driver, data_dir: Path) -> None:
    """Load all 12 relationship types from CSV files."""
    for rel_type, filename, query in _REL_DEFINITIONS:
        print(f"Loading {rel_type} relationships...")
        records = read_csv(data_dir, filename)
        _run_in_batches(driver, records, query)
        print(f"  [OK] Loaded {len(records)} {rel_type} relationships.")


def clear_database(driver: Driver) -> None:
    """Delete all nodes and relationships in batches."""
    print("Clearing database...")
    deleted_total = 0
    while True:
        records, _, _ = driver.execute_query(
            "MATCH (n) WITH n LIMIT 500 DETACH DELETE n RETURN count(*) AS deleted"
        )
        count = records[0]["deleted"]
        deleted_total += count
        if count > 0:
            print(f"  Deleted {deleted_total} nodes so far...", end="\r")
        if count == 0:
            break
    print(f"\n  [OK] Database cleared ({deleted_total} nodes deleted).")


def verify(driver: Driver) -> None:
    """Print node counts per label and total relationship count."""
    node_counts, _, _ = driver.execute_query("""
        CALL () {
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
            UNION ALL
            MATCH (n:Document) RETURN 'Document' as label, count(n) as count
            UNION ALL
            MATCH (n:Chunk) RETURN 'Chunk' as label, count(n) as count
            UNION ALL
            MATCH (n:FaultCode) RETURN 'FaultCode' as label, count(n) as count
            UNION ALL
            MATCH (n:PartNumber) RETURN 'PartNumber' as label, count(n) as count
            UNION ALL
            MATCH (n:OperatingLimit) RETURN 'OperatingLimit' as label, count(n) as count
            UNION ALL
            MATCH (n:MaintenanceTask) RETURN 'MaintenanceTask' as label, count(n) as count
            UNION ALL
            MATCH (n:ATAChapter) RETURN 'ATAChapter' as label, count(n) as count
        }
        RETURN label, count
        ORDER BY count DESC
    """)

    print()
    print("=" * 50)
    print("Node Counts:")
    total_nodes = 0
    for row in node_counts:
        print(f"  {row['label']}: {row['count']:,}")
        total_nodes += row["count"]
    print(f"  ---------------------")
    print(f"  Total Nodes: {total_nodes:,}")

    rel_records, _, _ = driver.execute_query(
        "MATCH ()-[r]->() RETURN count(r) as count"
    )
    rel_count = rel_records[0]["count"]
    print(f"\nTotal Relationships: {rel_count:,}")
    print("=" * 50)
