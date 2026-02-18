"""SimpleKGPipeline-based document enrichment: chunking, embedding, and entity extraction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neo4j import Driver
from neo4j_graphrag.embeddings.openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from neo4j_graphrag.experimental.components.text_splitters.base import TextSplitter
from neo4j_graphrag.experimental.components.types import TextChunks

# Labels for extracted entity nodes (used by clear/verify logic).
EXTRACTED_LABELS = ["OperatingLimit"]

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
# Context-aware text splitter
# ---------------------------------------------------------------------------


class ContextPrependingSplitter(TextSplitter):
    """Wraps a ``TextSplitter`` and prepends a context line to every chunk.

    **Why this is necessary:**  ``SimpleKGPipeline`` passes ``document_metadata``
    (which includes the aircraft type) only to the lexical graph builder for
    storage on ``Document`` nodes — it is never injected into the LLM extraction
    prompt.  The LLM sees only the raw chunk text.  After the inner splitter
    divides a 30 000-character maintenance manual into ~40 chunks of ~800
    characters, most chunks land deep in engine-specific sections where the
    engine designation (e.g. "LEAP-1A") dominates and the aircraft model
    (e.g. "A321neo") is never mentioned.  Without explicit context, the LLM
    confuses engine types for aircraft types, breaking downstream cross-links
    that match on ``OperatingLimit.aircraftType == Aircraft.model``.

    This wrapper solves the problem by delegating splitting to the inner
    splitter, then prepending a short context header to *every* resulting
    chunk so the LLM always has access to the document-level aircraft type.

    Set :attr:`context` before each call to ``pipeline.run_async()``.
    """

    def __init__(self, inner: TextSplitter, context: str = "") -> None:
        self.inner = inner
        self.context = context

    async def run(self, text: str) -> TextChunks:
        result = await self.inner.run(text)
        if self.context:
            for chunk in result.chunks:
                chunk.text = self.context + chunk.text
        return result


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


class DimensionAwareAzureOpenAIEmbeddings(AzureOpenAIEmbeddings):
    """AzureOpenAIEmbeddings that always passes ``dimensions`` to the API."""

    def __init__(self, dimensions: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._dimensions = dimensions

    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        return super().embed_query(text, dimensions=self._dimensions, **kwargs)


# ---------------------------------------------------------------------------
# Extraction prompt template
# ---------------------------------------------------------------------------

# Custom prompt that teaches the LLM domain reasoning for aircraft maintenance
# manuals.  Key improvements over the default ERExtractionTemplate:
#
# 1. Document context awareness — tells the LLM to look for a [DOCUMENT CONTEXT]
#    header (prepended to the text in process_all_documents) for the aircraft type.
# 2. Aircraft vs engine disambiguation — teaches the LLM that aircraft types are
#    airframe models, not engine designations.
# 3. Sensor parameter guidance — instructs the LLM to use the parameter names
#    from the document's sensor monitoring tables.
# 4. A concrete few-shot example showing correct extraction.
#
# Placeholders: {schema}, {examples}, {text} (required by ERExtractionTemplate).
# Literal braces must be doubled for Python str.format().

EXTRACTION_PROMPT = """\
You are an expert aviation engineer extracting structured operating-limit \
data from aircraft maintenance manuals to build a knowledge graph.

Your task: extract entities (nodes) and relationships from the input text \
according to the schema below.

Return result as JSON using this format:
{{"nodes": [{{"id": "0", "label": "OperatingLimit", "properties": {{"name": "EGT - A320-200", "parameterName": "EGT", "aircraftType": "A320-200", "unit": "°C", "maxValue": "695"}}}}],
"relationships": []}}

Use only the following node and relationship types:
{schema}

IMPORTANT RULES:

1. DOCUMENT CONTEXT: The input text starts with a [DOCUMENT CONTEXT] line \
that identifies the aircraft type and title. Use the aircraft type from this \
context line as the `aircraftType` property on every extracted entity.

2. AIRCRAFT TYPE vs ENGINE MODEL: The `aircraftType` property must be the \
airframe model (the aircraft you fly, e.g. A320-200, A321neo, B737-800), \
NOT the engine designation (e.g. V2500, LEAP-1A, CFM56-7B, PW1100G). \
Maintenance manuals are organized by aircraft type. Engine models appear \
throughout the text but they are components OF the aircraft, not the \
aircraft type itself.

3. PARAMETER NAMES: The `parameterName` should use the short sensor \
monitoring names from the document's sensor tables (e.g. EGT, Vibration, \
N1Speed, FuelFlow). Prefer concise sensor-style names over verbose \
descriptions.

4. ENTITY NAME FORMAT: The `name` property must follow the pattern \
"<parameterName> - <aircraftType>" (e.g. "EGT - A320-200"). This creates \
a unique identifier per parameter per aircraft type.

5. Only extract entities when the text contains specific numeric limits, \
thresholds, or operating ranges. Do not create entities for general \
descriptions without measurable values.

Assign a unique ID (string) to each node and reuse it for relationships.

Output rules:
- Return ONLY the JSON object, no additional text.
- Omit any backticks — output raw JSON.
- The JSON must be a single object, not wrapped in a list.
- Property names must be in double quotes.

{examples}

Input text:

{text}
"""


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------


def _create_pipeline(
    driver: Driver,
    *,
    provider: str,
    openai_api_key: str | None,
    anthropic_api_key: str | None,
    azure_api_key: str | None = None,
    azure_endpoint: str | None = None,
    azure_api_version: str | None = None,
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
                "max_completion_tokens": 2000,
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
    elif provider == "azure":
        from neo4j_graphrag.llm.openai_llm import AzureOpenAILLM

        llm = AzureOpenAILLM(
            model_name=llm_model,
            model_params={
                "max_completion_tokens": 2000,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=azure_api_version,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}")

    # --- Embedder ---
    if provider == "azure":
        embedder = DimensionAwareAzureOpenAIEmbeddings(
            dimensions=embedding_dimensions,
            model=embedding_model,
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=azure_api_version,
        )
    else:
        embedder = DimensionAwareOpenAIEmbeddings(
            dimensions=embedding_dimensions,
            model=embedding_model,
            api_key=openai_api_key,
        )

    # --- Text splitter (with per-chunk context injection) ---
    inner_splitter = FixedSizeSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        approximate=True,
    )
    splitter = ContextPrependingSplitter(inner_splitter)

    # --- Schema ---
    schema = build_extraction_schema()

    pipeline = SimpleKGPipeline(
        llm=llm,
        driver=driver,
        embedder=embedder,
        schema=schema,
        text_splitter=splitter,
        from_pdf=False,
        on_error="IGNORE",
        perform_entity_resolution=True,
        prompt_template=EXTRACTION_PROMPT,
    )
    return pipeline, splitter


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
    azure_api_key: str | None = None,
    azure_endpoint: str | None = None,
    azure_api_version: str | None = None,
    llm_model: str,
    embedding_model: str,
    embedding_dimensions: int,
    chunk_size: int,
    chunk_overlap: int,
    enrich_sample_size: int = 0,
) -> None:
    """Run the SimpleKGPipeline over every maintenance manual.

    When *enrich_sample_size* > 0 the input text for each document is truncated
    so that approximately that many chunks are produced.  Useful for quick test
    runs without processing the full manuals.
    """
    pipeline, splitter = _create_pipeline(
        driver,
        provider=provider,
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key,
        azure_api_key=azure_api_key,
        azure_endpoint=azure_endpoint,
        azure_api_version=azure_api_version,
        llm_model=llm_model,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Pre-compute max text length when sample size is set.
    # Each chunk beyond the first advances by (chunk_size - chunk_overlap) chars.
    if enrich_sample_size > 0:
        max_chars = chunk_size + (enrich_sample_size - 1) * (chunk_size - chunk_overlap)
    else:
        max_chars = 0  # 0 = unlimited

    async def _run_all():
        for meta in DOCUMENTS:
            print(f"\nProcessing: {meta.filename}")
            filepath = data_dir / meta.filename
            text = filepath.read_text(encoding="utf-8").strip()
            print(f"  Read {len(text):,} characters.")

            if max_chars and len(text) > max_chars:
                text = text[:max_chars]
                print(f"  Truncated to {max_chars:,} chars (~{enrich_sample_size} chunks).")

            # Update the splitter's context so every chunk the LLM sees starts
            # with the aircraft type.  The custom EXTRACTION_PROMPT instructs
            # the LLM to read this header.
            splitter.context = (
                f"[DOCUMENT CONTEXT] Aircraft Type: {meta.aircraft_type} | "
                f"Title: {meta.title}\n\n"
            )

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
    """Create relationships between enrichment data and the operational graph."""

    # Document -[:APPLIES_TO]-> Aircraft (via document metadata aircraftType)
    records, _, _ = driver.execute_query("""
        MATCH (d:Document) WHERE d.aircraftType IS NOT NULL
        MATCH (a:Aircraft {model: d.aircraftType})
        MERGE (d)-[:APPLIES_TO]->(a)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} Document -[:APPLIES_TO]-> Aircraft")

    # Sensor -[:HAS_LIMIT]-> OperatingLimit (match parameterName + aircraftType)
    records, _, _ = driver.execute_query("""
        MATCH (a:Aircraft)-[:HAS_SYSTEM]->(sys:System)-[:HAS_SENSOR]->(s:Sensor)
        MATCH (ol:OperatingLimit {parameterName: s.type, aircraftType: a.model})
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
        RETURN d.documentId AS doc, elementId(c) AS chunk_id, size(c.embedding) AS dims
        LIMIT {_SAMPLE_SIZE}
    """)
    print(f"\n  Chunks with embeddings -> Document ({len(rows)} samples):")
    for r in rows:
        print(f"    {r['chunk_id'][:12]}...  dims={r['dims']}  doc={r['doc']}")
    if not rows:
        print("    [WARN] No chunks with embeddings found!")

    # 2. OperatingLimit entities
    rows, _, _ = driver.execute_query(f"""
        MATCH (ol:OperatingLimit)
        RETURN ol.name AS name, ol.parameterName AS param, ol.aircraftType AS aircraft
        LIMIT {_SAMPLE_SIZE}
    """)
    print(f"\n  OperatingLimit entities ({len(rows)} samples):")
    for r in rows:
        print(f"    {r['name']}  param={r['param']}  aircraft={r['aircraft']}")
    if not rows:
        print("    [WARN] No OperatingLimit entities found!")

    # 3. Cross-links to operational graph
    queries = [
        ("Document -[:APPLIES_TO]-> Aircraft",
         f"MATCH (d:Document)-[:APPLIES_TO]->(a:Aircraft) RETURN d.title AS src, a.tail_number AS tgt LIMIT {_SAMPLE_SIZE}"),
        ("Sensor -[:HAS_LIMIT]-> OperatingLimit",
         f"MATCH (s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit) RETURN s.type AS src, ol.name AS tgt LIMIT {_SAMPLE_SIZE}"),
    ]
    print(f"\n  Cross-links to operational graph:")
    for label, query in queries:
        rows, _, _ = driver.execute_query(query)
        if rows:
            pairs = ", ".join(f"{r['src']}->{r['tgt']}" for r in rows)
            print(f"    {label}: {pairs}")
        else:
            print(f"    {label}: (none)")
