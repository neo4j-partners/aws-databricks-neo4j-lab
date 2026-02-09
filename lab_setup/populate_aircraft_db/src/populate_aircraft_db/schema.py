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
    ("Chunk", "documentId"),
]

# Constraints for entity types created by the `extract` command.
EXTRACTION_CONSTRAINTS: list[tuple[str, str]] = [
    ("FaultCode", "code"),
    ("PartNumber", "number"),
    ("OperatingLimit", "limitId"),
    ("MaintenanceTask", "taskId"),
    ("ATAChapter", "chapter"),
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
