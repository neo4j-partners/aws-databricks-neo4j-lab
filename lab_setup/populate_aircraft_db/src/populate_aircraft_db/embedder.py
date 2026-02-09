"""Document loading, chunking, embedding generation, and Neo4j storage."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path

from neo4j import Driver

BATCH_SIZE = 100

# ---------------------------------------------------------------------------
# Document metadata registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentMeta:
    filename: str
    document_id: str
    aircraft_type: str
    title: str


DOCUMENTS: list[DocumentMeta] = [
    DocumentMeta(
        filename="MAINTENANCE_A320.md",
        document_id="AMM-A320-2024-001",
        aircraft_type="A320-200",
        title="A320-200 Maintenance and Troubleshooting Manual",
    ),
    DocumentMeta(
        filename="MAINTENANCE_A321neo.md",
        document_id="AMM-A321neo-2024-001",
        aircraft_type="A321neo",
        title="A321neo Maintenance and Troubleshooting Manual",
    ),
    DocumentMeta(
        filename="MAINTENANCE_B737.md",
        document_id="AMM-B737-2024-001",
        aircraft_type="B737-800",
        title="B737-800 Maintenance and Troubleshooting Manual",
    ),
]

# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------


def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
    """Split text into chunks using neo4j-graphrag FixedSizeSplitter.

    Runs the async splitter in a thread to avoid event-loop conflicts.
    """
    from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import (
        FixedSizeSplitter,
    )

    splitter = FixedSizeSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        approximate=True,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(asyncio.run, splitter.run(text)).result()
    return [chunk.text for chunk in result.chunks]


# ---------------------------------------------------------------------------
# Neo4j operations
# ---------------------------------------------------------------------------


def clear_documents(driver: Driver) -> None:
    """Delete all Document and Chunk nodes in batches (preserves aircraft graph)."""
    print("Clearing Document/Chunk nodes...")
    deleted_total = 0
    while True:
        records, _, _ = driver.execute_query(
            "MATCH (n) WHERE n:Document OR n:Chunk "
            "WITH n LIMIT 500 DETACH DELETE n RETURN count(*) AS deleted"
        )
        count = records[0]["deleted"]
        deleted_total += count
        if count > 0:
            print(f"  Deleted {deleted_total} nodes so far...", end="\r")
        if count == 0:
            break
    print(f"\n  [OK] Cleared {deleted_total} Document/Chunk nodes.")


def create_document(driver: Driver, meta: DocumentMeta) -> None:
    """MERGE a Document node for the given metadata."""
    driver.execute_query(
        """
        MERGE (d:Document {documentId: $doc_id})
        SET d.type = $type,
            d.aircraftType = $aircraft_type,
            d.title = $title
        """,
        doc_id=meta.document_id,
        type="maintenance_manual",
        aircraft_type=meta.aircraft_type,
        title=meta.title,
    )
    print(f"  [OK] Document: {meta.document_id}")


def create_chunks_and_relationships(
    driver: Driver, meta: DocumentMeta, chunks: list[str]
) -> list[tuple[str, str]]:
    """Create Chunk nodes, FROM_DOCUMENT rels, and NEXT_CHUNK chain.

    Returns list of (element_id, text) pairs for embedding storage.
    """
    doc_id = meta.document_id
    total = len(chunks)

    # Build batch records
    batch_records = [
        {"doc_id": doc_id, "index": i, "text": chunk} for i, chunk in enumerate(chunks)
    ]

    # Create Chunk nodes + FROM_DOCUMENT rels in batches
    for i in range(0, total, BATCH_SIZE):
        batch = batch_records[i : i + BATCH_SIZE]
        driver.execute_query(
            """
            UNWIND $batch AS row
            MATCH (d:Document {documentId: row.doc_id})
            MERGE (c:Chunk {documentId: row.doc_id, index: row.index})
            SET c.text = row.text
            MERGE (c)-[:FROM_DOCUMENT]->(d)
            """,
            batch=batch,
        )
        progress = min(i + BATCH_SIZE, total)
        print(f"    Chunks: {progress}/{total}", end="\r")
    print()

    # Create NEXT_CHUNK chain
    chain_records = [
        {"doc_id": doc_id, "idx": i, "next_idx": i + 1} for i in range(total - 1)
    ]
    for i in range(0, len(chain_records), BATCH_SIZE):
        batch = chain_records[i : i + BATCH_SIZE]
        driver.execute_query(
            """
            UNWIND $batch AS row
            MATCH (c1:Chunk {documentId: row.doc_id, index: row.idx})
            MATCH (c2:Chunk {documentId: row.doc_id, index: row.next_idx})
            MERGE (c1)-[:NEXT_CHUNK]->(c2)
            """,
            batch=batch,
        )
    print(f"  [OK] {total} chunks created with NEXT_CHUNK chain.")

    # Retrieve element IDs for embedding storage
    records, _, _ = driver.execute_query(
        """
        MATCH (c:Chunk {documentId: $doc_id})
        RETURN elementId(c) AS eid, c.text AS text
        ORDER BY c.index
        """,
        doc_id=doc_id,
    )
    return [(r["eid"], r["text"]) for r in records]


def generate_and_store_embeddings(
    driver: Driver,
    chunk_data: list[tuple[str, str]],
    api_key: str,
    model: str,
    dimensions: int,
) -> None:
    """Generate embeddings via OpenAI and store them on Chunk nodes.

    Uses neo4j_graphrag.indexes.upsert_vectors which calls
    db.create.setNodeVectorProperty — the proper Neo4j vector storage API.
    """
    from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
    from neo4j_graphrag.indexes import upsert_vectors

    embedder = OpenAIEmbeddings(
        api_key=api_key,
        model=model,
    )

    total = len(chunk_data)
    ids: list[str] = []
    embeddings: list[list[float]] = []

    for i, (eid, text) in enumerate(chunk_data, 1):
        vector = embedder.embed_query(text, dimensions=dimensions)
        ids.append(eid)
        embeddings.append(vector)
        print(f"    Embedding: {i}/{total}", end="\r")
    print()

    upsert_vectors(
        driver=driver,
        ids=ids,
        embedding_property="embedding",
        embeddings=embeddings,
    )
    print(f"  [OK] {total} embeddings stored.")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def process_document(
    driver: Driver,
    data_dir: Path,
    meta: DocumentMeta,
    api_key: str,
    model: str,
    dimensions: int,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> None:
    """Full pipeline for one document: read, split, create nodes, embed, store."""
    print(f"\nProcessing: {meta.filename}")

    # Read
    text = (data_dir / meta.filename).read_text(encoding="utf-8").strip()
    print(f"  Read {len(text):,} characters.")

    # Split
    chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"  Split into {len(chunks)} chunks.")

    # Create Document + Chunks
    create_document(driver, meta)
    chunk_data = create_chunks_and_relationships(driver, meta, chunks)

    # Embed + Store
    print("  Generating embeddings...")
    generate_and_store_embeddings(driver, chunk_data, api_key, model, dimensions)
