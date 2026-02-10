"""SimpleKGPipeline-based document enrichment: chunking, embedding, and entity extraction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neo4j import Driver
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings

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


class DimensionAwareOpenAIEmbeddings(OpenAIEmbeddings):
    """OpenAIEmbeddings that always passes ``dimensions`` to the API.

    The pipeline's ``TextChunkEmbedder`` calls ``embed_query(text)`` without
    a ``dimensions`` kwarg, so we override to inject it automatically.
    """

    def __init__(self, dimensions: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._dimensions = dimensions

    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        return super().embed_query(text, dimensions=self._dimensions, **kwargs)


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
            model_params={
                "max_tokens": 2000,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
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
        embedder=embedder,
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


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_SAMPLE_SIZE = 5


def validate_enrichment(driver: Driver) -> None:
    """Run sample queries to verify embeddings, entities, and cross-links."""

    print(f"\nValidation (sample size {_SAMPLE_SIZE}):")

    # 1. Chunks with embeddings linked to documents
    rows, _, _ = driver.execute_query(f"""
        MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
        WHERE c.embedding IS NOT NULL
        RETURN d.documentId AS doc, c.id AS chunk_id, size(c.embedding) AS dims
        LIMIT {_SAMPLE_SIZE}
    """)
    print(f"\n  Chunks with embeddings -> Document ({len(rows)} samples):")
    for r in rows:
        print(f"    {r['chunk_id'][:12]}...  dims={r['dims']}  doc={r['doc']}")
    if not rows:
        print("    [WARN] No chunks with embeddings found!")

    # 2. Extracted entities by label
    rows, _, _ = driver.execute_query(f"""
        UNWIND $labels AS label
        CALL (label) {{
            MATCH (n)
            WHERE label IN labels(n)
            RETURN n.name AS name, label AS entity_type
            LIMIT {_SAMPLE_SIZE}
        }}
        RETURN entity_type, collect(name)[..{_SAMPLE_SIZE}] AS samples
    """, labels=EXTRACTED_LABELS)
    print(f"\n  Extracted entities:")
    for r in rows:
        names = ", ".join(str(n) for n in r["samples"])
        print(f"    {r['entity_type']}: {names}")
    if not rows:
        print("    [WARN] No extracted entities found!")

    # 3. Entity-to-chunk links (FROM_CHUNK)
    rows, _, _ = driver.execute_query(f"""
        MATCH (e)-[:FROM_CHUNK]->(c:Chunk)
        WHERE any(l IN labels(e) WHERE l IN $labels)
        RETURN labels(e)[0] AS entity_type, e.name AS name, c.id AS chunk_id
        LIMIT {_SAMPLE_SIZE}
    """, labels=EXTRACTED_LABELS)
    print(f"\n  Entity -> Chunk links ({len(rows)} samples):")
    for r in rows:
        print(f"    {r['entity_type']}({r['name']}) -> Chunk({r['chunk_id'][:12]}...)")
    if not rows:
        print("    [WARN] No entity-to-chunk links found!")

    # 4. Cross-links to operational graph
    queries = [
        ("FaultCode -[:CLASSIFIED_UNDER]-> ATAChapter",
         f"MATCH (fc:FaultCode)-[:CLASSIFIED_UNDER]->(ata:ATAChapter) RETURN fc.name AS src, ata.name AS tgt LIMIT {_SAMPLE_SIZE}"),
        ("MaintenanceEvent -[:CLASSIFIED_AS]-> FaultCode",
         f"MATCH (me:MaintenanceEvent)-[:CLASSIFIED_AS]->(fc:FaultCode) RETURN me.event_id AS src, fc.name AS tgt LIMIT {_SAMPLE_SIZE}"),
        ("Sensor -[:HAS_LIMIT]-> OperatingLimit",
         f"MATCH (s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit) RETURN s.sensor_id AS src, ol.name AS tgt LIMIT {_SAMPLE_SIZE}"),
    ]
    print(f"\n  Cross-links to operational graph:")
    for label, query in queries:
        rows, _, _ = driver.execute_query(query)
        if rows:
            pairs = ", ".join(f"{r['src']}->{r['tgt']}" for r in rows)
            print(f"    {label}: {pairs}")
        else:
            print(f"    {label}: (none)")
