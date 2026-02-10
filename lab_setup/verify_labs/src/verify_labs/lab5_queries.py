"""Cypher verification queries extracted from Lab 5 notebooks."""

from __future__ import annotations

from .query_runner import QuerySpec

# ── Notebook 01: 01_aircraft_etl_to_neo4j.ipynb ─────────────────────────────

NOTEBOOK_01: list[QuerySpec] = [
    QuerySpec(
        name="Node counts by label",
        description="Count nodes grouped by label (Aircraft, System, Component, …)",
        notebook="01",
        cypher="""\
MATCH (n)
RETURN labels(n)[0] AS NodeType, count(*) AS Count
ORDER BY NodeType""",
        min_rows=1,
    ),
    QuerySpec(
        name="Relationship counts by type",
        description="Count relationships grouped by type (HAS_SYSTEM, HAS_COMPONENT, …)",
        notebook="01",
        cypher="""\
MATCH ()-[r]->()
RETURN type(r) AS RelType, count(*) AS Count
ORDER BY RelType""",
        min_rows=1,
    ),
    QuerySpec(
        name="Aircraft hierarchy for N95040A",
        description="Systems and components for tail number N95040A",
        notebook="01",
        cypher="""\
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)
WHERE s.type IS NOT NULL AND s.name IS NOT NULL
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
RETURN a.tail_number AS Aircraft,
       a.model AS Model,
       s.name AS System,
       s.type AS SystemType,
       collect(c.name) AS Components
ORDER BY s.type, s.name""",
        min_rows=1,
    ),
    QuerySpec(
        name="Fleet by manufacturer",
        description="Aircraft count per manufacturer with model list",
        notebook="01",
        cypher="""\
MATCH (a:Aircraft)
RETURN a.manufacturer AS Manufacturer,
       count(a) AS AircraftCount,
       collect(a.model) AS Models
ORDER BY AircraftCount DESC""",
        min_rows=1,
    ),
    QuerySpec(
        name="Component distribution",
        description="Component count per type",
        notebook="01",
        cypher="""\
MATCH (c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC""",
        min_rows=1,
    ),
    QuerySpec(
        name="Complete aircraft hierarchy",
        description="Full hierarchy for N95040A (adapted from visualization query)",
        notebook="01",
        cypher="""\
MATCH (a:Aircraft {tail_number: 'N95040A'})-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)
WHERE s.type IS NOT NULL AND s.name IS NOT NULL AND c.name IS NOT NULL
RETURN a.tail_number AS Aircraft, s.name AS System, s.type AS SystemType,
       c.name AS Component, c.type AS ComponentType
ORDER BY s.type, s.name, c.name""",
        min_rows=1,
    ),
    QuerySpec(
        name="Compare aircraft by operator",
        description="Aircraft count per operator",
        notebook="01",
        cypher="""\
MATCH (a:Aircraft)
RETURN a.operator AS Operator, count(a) AS Count""",
        min_rows=1,
    ),
    QuerySpec(
        name="Engine components",
        description="Component types within Engine systems",
        notebook="01",
        cypher="""\
MATCH (s:System {type: 'Engine'})-[:HAS_COMPONENT]->(c:Component)
RETURN c.type AS ComponentType, count(c) AS Count
ORDER BY Count DESC""",
        min_rows=1,
    ),
]

# ── Notebook 02: 02_load_neo4j_full.ipynb ────────────────────────────────────

NOTEBOOK_02: list[QuerySpec] = [
    QuerySpec(
        name="Comprehensive node counts",
        description="Per-label node counts for all 9 labels via CALL subquery",
        notebook="02",
        cypher="""\
CALL () {
    MATCH (n:Aircraft) RETURN 'Aircraft' AS label, count(n) AS count
    UNION ALL
    MATCH (n:System) RETURN 'System' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Component) RETURN 'Component' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Sensor) RETURN 'Sensor' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Airport) RETURN 'Airport' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Flight) RETURN 'Flight' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Delay) RETURN 'Delay' AS label, count(n) AS count
    UNION ALL
    MATCH (n:MaintenanceEvent) RETURN 'MaintenanceEvent' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Removal) RETURN 'Removal' AS label, count(n) AS count
}
RETURN label, count
ORDER BY count DESC""",
        min_rows=9,
    ),
    QuerySpec(
        name="Total relationship count",
        description="Total number of relationships in the graph",
        notebook="02",
        cypher="""\
MATCH ()-[r]->() RETURN count(r) AS count""",
        min_rows=1,
    ),
    QuerySpec(
        name="Critical maintenance issues",
        description="Aircraft with critical-severity maintenance events",
        notebook="02",
        # NOTE: Notebook markdown uses 'Critical' but CSV data stores 'CRITICAL'.
        # We use the actual value so the query validates data presence.
        cypher="""\
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)-[:HAS_EVENT]->(m:MaintenanceEvent)
WHERE m.severity = 'CRITICAL' AND m.reported_at IS NOT NULL
RETURN a.tail_number AS TailNumber, s.name AS System, c.name AS Component,
       m.fault AS Fault, m.reported_at AS ReportedAt
ORDER BY m.reported_at DESC
LIMIT 10""",
        min_rows=1,
    ),
    QuerySpec(
        name="Flight delays by cause",
        description="Delay counts and average minutes grouped by cause",
        notebook="02",
        cypher="""\
MATCH (f:Flight)-[:HAS_DELAY]->(d:Delay)
RETURN d.cause AS Cause, count(*) AS Count, avg(d.minutes) AS AvgMinutes
ORDER BY Count DESC""",
        min_rows=1,
    ),
    QuerySpec(
        name="Component removal history",
        description="Recent component removals with aircraft and reason",
        notebook="02",
        cypher="""\
MATCH (a:Aircraft)-[:HAS_REMOVAL]->(r:Removal)-[:REMOVED_COMPONENT]->(c:Component)
WHERE r.removal_date IS NOT NULL
RETURN a.tail_number AS TailNumber, c.name AS Component, r.reason AS Reason,
       r.removal_date AS RemovalDate, r.tsn AS TSN, r.csn AS CSN
ORDER BY r.removal_date DESC
LIMIT 20""",
        min_rows=1,
    ),
]

ALL_QUERIES: list[QuerySpec] = NOTEBOOK_01 + NOTEBOOK_02
