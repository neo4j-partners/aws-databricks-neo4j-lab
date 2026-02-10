"""Constraint and index definitions for the Aircraft Digital Twin graph."""

from __future__ import annotations

from neo4j import Driver

# (label, property) pairs — one uniqueness constraint each.
CONSTRAINTS: list[tuple[str, str]] = [
    ("Aircraft", "aircraft_id"),
    ("System", "system_id"),
    ("Component", "component_id"),
    ("Sensor", "sensor_id"),
    ("Airport", "airport_id"),
    ("Flight", "flight_id"),
    ("Delay", "delay_id"),
    ("MaintenanceEvent", "event_id"),
    ("Removal", "removal_id"),
    ("Document", "documentId"),
]

# (label, property) pairs — property indexes for common lookups.
INDEXES: list[tuple[str, str]] = [
    ("MaintenanceEvent", "severity"),
    ("Flight", "aircraft_id"),
    ("Removal", "aircraft_id"),
]

# Constraints for entity types created by the `enrich` command.
# SimpleKGPipeline deduplicates on the `name` property.
EXTRACTION_CONSTRAINTS: list[tuple[str, str]] = [
    ("FaultCode", "name"),
    ("PartNumber", "name"),
    ("OperatingLimit", "name"),
    ("MaintenanceTask", "name"),
    ("ATAChapter", "name"),
]


def create_constraints(driver: Driver) -> None:
    """Create uniqueness constraints (idempotent)."""
    for label, prop in CONSTRAINTS:
        driver.execute_query(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )
        print(f"  [OK] Constraint: {label}.{prop}")


def create_indexes(driver: Driver) -> None:
    """Create property indexes (idempotent)."""
    for label, prop in INDEXES:
        index_name = f"idx_{label.lower()}_{prop.lower()}"
        driver.execute_query(
            f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
        )
        print(f"  [OK] Index: {label}.{prop}")


def create_extraction_constraints(driver: Driver) -> None:
    """Create uniqueness constraints for extracted entity types (idempotent)."""
    for label, prop in EXTRACTION_CONSTRAINTS:
        driver.execute_query(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )
        print(f"  [OK] Constraint: {label}.{prop}")


def create_embedding_indexes(driver: Driver, dimensions: int) -> None:
    """Create vector and fulltext indexes for Chunk embeddings (idempotent).

    Imports neo4j_graphrag lazily so that other commands don't require it.
    """
    from neo4j_graphrag.indexes import create_vector_index, create_fulltext_index

    create_vector_index(
        driver,
        name="maintenanceChunkEmbeddings",
        label="Chunk",
        embedding_property="embedding",
        dimensions=dimensions,
        similarity_fn="cosine",
    )
    print("  [OK] Vector index: maintenanceChunkEmbeddings")

    create_fulltext_index(
        driver,
        name="maintenanceChunkText",
        label="Chunk",
        node_properties=["text"],
    )
    print("  [OK] Fulltext index: maintenanceChunkText")


def build_extraction_schema():
    """Build a GraphSchema for SimpleKGPipeline entity extraction.

    Entity types use ``name`` as primary identifier (SimpleKGPipeline's
    entity resolver deduplicates on ``name``).
    """
    from neo4j_graphrag.experimental.components.schema import (
        GraphSchema,
        NodeType,
        PropertyType,
        RelationshipType,
    )

    node_types = [
        NodeType(
            label="FaultCode",
            description="An aircraft fault or failure code from maintenance manuals.",
            properties=[
                PropertyType(name="name", type="STRING", description="Fault code identifier, e.g. ENG-OVH-001"),
                PropertyType(name="description", type="STRING", description="Brief description of the fault"),
                PropertyType(name="severityLevels", type="LIST", description="Severity levels e.g. CRITICAL, MAJOR, MINOR"),
                PropertyType(name="ataChapter", type="STRING", description="ATA chapter number"),
                PropertyType(name="immediateAction", type="STRING", description="Recommended immediate action"),
            ],
            additional_properties=False,
        ),
        NodeType(
            label="PartNumber",
            description="An aircraft part or component number from maintenance manuals.",
            properties=[
                PropertyType(name="name", type="STRING", description="Part number, e.g. V25-FM-2100"),
                PropertyType(name="componentName", type="STRING", description="Name of the component"),
                PropertyType(name="ataReference", type="STRING", description="ATA reference, e.g. 72-01"),
            ],
            additional_properties=False,
        ),
        NodeType(
            label="OperatingLimit",
            description="An operating parameter limit for an aircraft system.",
            properties=[
                PropertyType(name="name", type="STRING", description="Parameter name, e.g. EGT"),
                PropertyType(name="unit", type="STRING", description="Unit of measurement"),
                PropertyType(name="regime", type="STRING", description="Operating regime, e.g. takeoff, cruise"),
                PropertyType(name="minValue", type="STRING", description="Minimum value"),
                PropertyType(name="maxValue", type="STRING", description="Maximum value"),
                PropertyType(name="aircraftType", type="STRING", description="Aircraft type, e.g. A320-200"),
            ],
            additional_properties=False,
        ),
        NodeType(
            label="MaintenanceTask",
            description="A scheduled or unscheduled maintenance task.",
            properties=[
                PropertyType(name="name", type="STRING", description="Task ID or short description"),
                PropertyType(name="description", type="STRING", description="Full task description"),
                PropertyType(name="interval", type="STRING", description="Maintenance interval value"),
                PropertyType(name="intervalUnit", type="STRING", description="Interval unit, e.g. FH, months, days"),
                PropertyType(name="durationHours", type="STRING", description="Duration in hours"),
                PropertyType(name="personnelCount", type="STRING", description="Number of personnel required"),
                PropertyType(name="personnelType", type="STRING", description="Type of personnel, e.g. mechanic"),
            ],
            additional_properties=False,
        ),
        NodeType(
            label="ATAChapter",
            description="An ATA (Air Transport Association) chapter classification.",
            properties=[
                PropertyType(name="name", type="STRING", description="Chapter number, e.g. 72"),
                PropertyType(name="title", type="STRING", description="Chapter title, e.g. Engine"),
            ],
            additional_properties=False,
        ),
    ]

    relationship_types = [
        RelationshipType(
            label="CLASSIFIED_UNDER",
            description="Entity is classified under an ATA chapter.",
        ),
    ]

    patterns = [
        ("FaultCode", "CLASSIFIED_UNDER", "ATAChapter"),
        ("PartNumber", "CLASSIFIED_UNDER", "ATAChapter"),
    ]

    return GraphSchema(
        node_types=tuple(node_types),
        relationship_types=tuple(relationship_types),
        patterns=tuple(patterns),
        additional_node_types=False,
        additional_relationship_types=False,
        additional_patterns=False,
    )
