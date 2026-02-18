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

# (index_name, label, [properties]) — fulltext indexes for sample queries.
FULLTEXT_INDEXES: list[tuple[str, str, list[str]]] = [
    ("maintenance_search", "MaintenanceEvent", ["fault", "corrective_action"]),
    ("delay_search", "Delay", ["cause"]),
    ("component_search", "Component", ["name", "type"]),
    ("document_search", "Document", ["title", "aircraftType"]),
]

# Constraints for entity types created by the `enrich` command.
# SimpleKGPipeline deduplicates on the `name` property.
EXTRACTION_CONSTRAINTS: list[tuple[str, str]] = [
    ("OperatingLimit", "name"),
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


def create_fulltext_indexes(driver: Driver) -> None:
    """Create fulltext indexes for sample demo queries (idempotent)."""
    for name, label, props in FULLTEXT_INDEXES:
        props_clause = ", ".join(f"n.{p}" for p in props)
        driver.execute_query(
            f"CREATE FULLTEXT INDEX {name} IF NOT EXISTS "
            f"FOR (n:{label}) ON EACH [{props_clause}]"
        )
        print(f"  [OK] Fulltext index: {name} on {label}({', '.join(props)})")


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

    Only extracts OperatingLimit entities.  Entity names are qualified
    with aircraft type (e.g. ``EGT - A320-200``) so that entity
    resolution does not merge limits from different aircraft.
    """
    from neo4j_graphrag.experimental.components.schema import (
        GraphSchema,
        NodeType,
        PropertyType,
    )

    node_types = [
        NodeType(
            label="OperatingLimit",
            description="An operating parameter limit for an aircraft system.",
            properties=[
                PropertyType(
                    name="name",
                    type="STRING",
                    description=(
                        "Unique identifier combining parameter and aircraft type, "
                        "e.g. 'EGT - A320-200', 'N1Speed - B737-800'. "
                        "Always append ' - <aircraft type>'."
                    ),
                ),
                PropertyType(
                    name="parameterName",
                    type="STRING",
                    description="Base parameter name matching sensor type, e.g. EGT, Vibration, N1Speed, FuelFlow",
                ),
                PropertyType(name="unit", type="STRING", description="Unit of measurement"),
                PropertyType(name="regime", type="STRING", description="Operating regime, e.g. takeoff, cruise"),
                PropertyType(name="minValue", type="STRING", description="Minimum value"),
                PropertyType(name="maxValue", type="STRING", description="Maximum value"),
                PropertyType(name="aircraftType", type="STRING", description="Aircraft type, e.g. A320-200"),
            ],
            additional_properties=False,
        ),
    ]

    return GraphSchema(
        node_types=tuple(node_types),
        relationship_types=(),
        patterns=(),
        additional_node_types=False,
        additional_relationship_types=False,
        additional_patterns=False,
    )
