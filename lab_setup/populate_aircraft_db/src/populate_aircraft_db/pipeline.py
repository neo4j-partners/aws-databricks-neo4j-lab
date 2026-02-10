"""SimpleKGPipeline-based document enrichment: chunking, embedding, and entity extraction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neo4j import Driver

# Labels for extracted entity nodes (used by clear/verify logic).
EXTRACTED_LABELS = ["FaultCode", "PartNumber", "OperatingLimit", "MaintenanceTask", "ATAChapter"]

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
# Dimension-aware embedder wrapper
# ---------------------------------------------------------------------------


class DimensionAwareOpenAIEmbeddings:
    """OpenAIEmbeddings subclass that always passes ``dimensions`` to the API.

    The ``TextChunkEmbedder`` component calls ``embed_query(text)`` without
    a ``dimensions`` kwarg, so we override to inject it.
    """

    def __init__(self, dimensions: int, **kwargs: Any) -> None:
        from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings

        self._inner = OpenAIEmbeddings(**kwargs)
        self._dimensions = dimensions

    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        return self._inner.embed_query(text, dimensions=self._dimensions, **kwargs)

    async def async_embed_query(self, text: str, **kwargs: Any) -> list[float]:
        # OpenAIEmbeddings doesn't have a native async, but the pipeline may
        # call async_embed_query via the TextChunkEmbedder. Fall back to sync
        # in a thread so we don't block the event loop.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.embed_query(text, **kwargs)
        )


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------


def _create_pipeline(
    driver: Driver,
    *,
    provider: str,
    openai_api_key: str | None,
    anthropic_api_key: str | None,
    llm_model: str,
    embedding_model: str,
    embedding_dimensions: int,
    chunk_size: int,
    chunk_overlap: int,
):
    """Build a ``SimpleKGPipeline`` configured for maintenance-manual enrichment."""
    from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
    from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import (
        FixedSizeSplitter,
    )

    from .schema import build_extraction_schema

    # --- LLM ---
    if provider == "openai":
        from neo4j_graphrag.llm.openai_llm import OpenAILLM

        llm = OpenAILLM(
            model_name=llm_model,
            model_params={"temperature": 0, "response_format": {"type": "json_object"}},
            api_key=openai_api_key,
        )
    elif provider == "anthropic":
        from neo4j_graphrag.llm.anthropic_llm import AnthropicLLM

        llm = AnthropicLLM(
            model_name=llm_model,
            model_params={"max_tokens": 4096},
            api_key=anthropic_api_key,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}")

    # --- Embedder ---
    embedder = DimensionAwareOpenAIEmbeddings(
        dimensions=embedding_dimensions,
        model=embedding_model,
        api_key=openai_api_key,
    )

    # --- Text splitter ---
    splitter = FixedSizeSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        approximate=True,
    )

    # --- Schema ---
    schema = build_extraction_schema()

    return SimpleKGPipeline(
        llm=llm,
        driver=driver,
        embedder=embedder,  # type: ignore[arg-type]
        schema=schema,
        text_splitter=splitter,
        from_pdf=False,
        on_error="IGNORE",
        perform_entity_resolution=True,
    )


# ---------------------------------------------------------------------------
# Document processing
# ---------------------------------------------------------------------------


def process_all_documents(
    driver: Driver,
    data_dir: Path,
    *,
    provider: str,
    openai_api_key: str | None,
    anthropic_api_key: str | None,
    llm_model: str,
    embedding_model: str,
    embedding_dimensions: int,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """Run the SimpleKGPipeline over every maintenance manual."""
    pipeline = _create_pipeline(
        driver,
        provider=provider,
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key,
        llm_model=llm_model,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    async def _run_all():
        for meta in DOCUMENTS:
            print(f"\nProcessing: {meta.filename}")
            filepath = data_dir / meta.filename
            text = filepath.read_text(encoding="utf-8").strip()
            print(f"  Read {len(text):,} characters.")
            await pipeline.run_async(
                text=text,
                document_metadata={
                    "documentId": meta.document_id,
                    "aircraftType": meta.aircraft_type,
                    "title": meta.title,
                    "type": "maintenance_manual",
                },
            )
            print(f"  [OK] Pipeline complete for {meta.document_id}")

    asyncio.run(_run_all())


# ---------------------------------------------------------------------------
# Cross-links to existing operational graph
# ---------------------------------------------------------------------------


def link_to_existing_graph(driver: Driver) -> None:
    """Create relationships between extracted entities and existing graph nodes."""

    # FaultCode -[:CLASSIFIED_UNDER]-> ATAChapter (via ataChapter property)
    records, _, _ = driver.execute_query("""
        MATCH (fc:FaultCode) WHERE fc.ataChapter IS NOT NULL AND fc.ataChapter <> ''
        MATCH (ata:ATAChapter {name: fc.ataChapter})
        MERGE (fc)-[:CLASSIFIED_UNDER]->(ata)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} FaultCode -[:CLASSIFIED_UNDER]-> ATAChapter")

    # MaintenanceEvent -[:CLASSIFIED_AS]-> FaultCode
    records, _, _ = driver.execute_query("""
        MATCH (me:MaintenanceEvent) WHERE me.fault IS NOT NULL AND me.fault <> ''
        MATCH (fc:FaultCode {name: me.fault})
        MERGE (me)-[:CLASSIFIED_AS]->(fc)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} MaintenanceEvent -[:CLASSIFIED_AS]-> FaultCode")

    # PartNumber -[:CLASSIFIED_UNDER]-> ATAChapter
    records, _, _ = driver.execute_query("""
        MATCH (pn:PartNumber) WHERE pn.ataReference IS NOT NULL AND pn.ataReference <> ''
        WITH pn, split(pn.ataReference, '-')[0] AS chapter
        MATCH (ata:ATAChapter {name: chapter})
        MERGE (pn)-[:CLASSIFIED_UNDER]->(ata)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} PartNumber -[:CLASSIFIED_UNDER]-> ATAChapter")

    # Component -[:IDENTIFIED_BY]-> PartNumber (name match)
    records, _, _ = driver.execute_query("""
        MATCH (c:Component)
        MATCH (pn:PartNumber)
        WHERE toLower(c.name) = toLower(pn.componentName)
        MERGE (c)-[:IDENTIFIED_BY]->(pn)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} Component -[:IDENTIFIED_BY]-> PartNumber")

    # Sensor -[:HAS_LIMIT]-> OperatingLimit (match sensor type to parameter, scoped by aircraft model)
    records, _, _ = driver.execute_query("""
        MATCH (a:Aircraft)-[:HAS_SYSTEM]->(sys:System)-[:HAS_SENSOR]->(s:Sensor)
        MATCH (ol:OperatingLimit {name: s.type, aircraftType: a.model})
        MERGE (s)-[:HAS_LIMIT]->(ol)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} Sensor -[:HAS_LIMIT]-> OperatingLimit")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def clear_enrichment_data(driver: Driver) -> None:
    """Delete all Document, Chunk, and extracted entity nodes (preserves operational graph)."""
    labels_to_clear = ["Document", "Chunk"] + EXTRACTED_LABELS
    deleted_total = 0

    print("Clearing enrichment data (Documents, Chunks, extracted entities)...")
    for label in labels_to_clear:
        while True:
            records, _, _ = driver.execute_query(
                f"MATCH (n:{label}) WITH n LIMIT 500 DETACH DELETE n RETURN count(*) AS deleted"
            )
            count = records[0]["deleted"]
            deleted_total += count
            if count == 0:
                break

    # Clean up __Entity__ and __KGBuilder__ labeled nodes left by the pipeline
    for label in ["__Entity__", "__KGBuilder__"]:
        while True:
            records, _, _ = driver.execute_query(
                f"MATCH (n:{label}) WITH n LIMIT 500 DETACH DELETE n RETURN count(*) AS deleted"
            )
            count = records[0]["deleted"]
            deleted_total += count
            if count == 0:
                break

    print(f"  [OK] Cleared {deleted_total} enrichment nodes.")
