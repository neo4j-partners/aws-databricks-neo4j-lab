"""CLI entry point for populate-aircraft-db."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

import sys

import typer
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from .config import Settings
from .loader import clear_database, load_nodes, load_relationships, verify
from .schema import (
    create_constraints,
    create_embedding_indexes,
    create_extraction_constraints,
    create_indexes,
)

app = typer.Typer(
    name="populate-aircraft-db",
    help="Load the Aircraft Digital Twin dataset into a Neo4j Aura instance.",
    add_completion=False,
)


def _fmt_elapsed(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


@contextmanager
def _connect(settings: Settings) -> Generator[Driver, None, None]:
    """Create a Neo4j driver, verify connectivity, and close on exit."""
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password.get_secret_value()),
    )
    try:
        driver.verify_connectivity()
    except (ServiceUnavailable, OSError) as exc:
        driver.close()
        print(f"[FAIL] Cannot connect to {settings.neo4j_uri}")
        print(f"       {exc}")
        print("\nCheck that the Neo4j instance is running and reachable.")
        sys.exit(1)
    try:
        print("[OK] Connected.\n")
        yield driver
    finally:
        driver.close()


@app.command()
def load(
    clean: bool = typer.Option(False, "--clean", help="Clear the database before loading."),
) -> None:
    """Load all nodes and relationships into Neo4j."""
    settings = Settings()  # type: ignore[call-arg]
    start = time.monotonic()

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        if clean:
            clear_database(driver)
            print()

        print("Creating constraints...")
        create_constraints(driver)
        print("\nCreating indexes...")
        create_indexes(driver)
        print()

        load_nodes(driver, settings.data_dir)
        print()
        load_relationships(driver, settings.data_dir)

        verify(driver)

    elapsed = time.monotonic() - start
    print(f"\nDone in {_fmt_elapsed(elapsed)}.")


@app.command("verify")
def verify_cmd() -> None:
    """Print node and relationship counts (read-only)."""
    settings = Settings()  # type: ignore[call-arg]

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        verify(driver)


@app.command("clean")
def clean_cmd() -> None:
    """Clear all nodes and relationships from the database."""
    settings = Settings()  # type: ignore[call-arg]

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        clear_database(driver)

    print("\nDone.")


@app.command("embed")
def embed_cmd(
    clean: bool = typer.Option(False, "--clean", help="Clear existing Document/Chunk nodes first."),
    chunk_size: int = typer.Option(800, "--chunk-size", help="Characters per chunk."),
    chunk_overlap: int = typer.Option(100, "--chunk-overlap", help="Overlap between chunks."),
) -> None:
    """Load maintenance manuals, chunk, generate OpenAI embeddings, and store in Neo4j."""
    from .embedder import DOCUMENTS, clear_documents, process_document

    settings = Settings()  # type: ignore[call-arg]

    if settings.openai_api_key is None:
        raise typer.BadParameter(
            "OPENAI_API_KEY is required for the embed command. Set it in .env or as an env var."
        )

    api_key = settings.openai_api_key.get_secret_value()
    model = settings.openai_embedding_model
    dimensions = settings.openai_embedding_dimensions
    start = time.monotonic()

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        if clean:
            clear_documents(driver)
            print()

        print("Creating constraints and indexes...")
        create_constraints(driver)
        create_indexes(driver)

        for meta in DOCUMENTS:
            process_document(
                driver,
                settings.data_dir,
                meta,
                api_key=api_key,
                model=model,
                dimensions=dimensions,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

        print("\nCreating embedding indexes...")
        create_embedding_indexes(driver, dimensions)

        verify(driver)

    elapsed = time.monotonic() - start
    print(f"\nDone in {_fmt_elapsed(elapsed)}.")


@app.command("extract")
def extract_cmd(
    clean: bool = typer.Option(False, "--clean", help="Clear existing extracted entities first."),
    limit: int = typer.Option(0, "--limit", help="Max chunks to process (0 = all)."),
    document: str = typer.Option("", "--document", help="Only process chunks from this document ID."),
    provider: str = typer.Option(
        "",
        "--provider",
        help="LLM provider: 'openai' or 'anthropic' (overrides LLM_PROVIDER env var).",
    ),
) -> None:
    """Extract structured entities from maintenance manual chunks."""
    from .extractor import clear_extracted, make_llm_caller, run_extraction

    settings = Settings()  # type: ignore[call-arg]

    chosen_provider = provider or settings.llm_provider

    if chosen_provider == "openai":
        if settings.openai_api_key is None:
            raise typer.BadParameter(
                "OPENAI_API_KEY is required when using OpenAI. Set it in .env or as an env var."
            )
        api_key = settings.openai_api_key.get_secret_value()
        model = settings.openai_extraction_model
    elif chosen_provider == "anthropic":
        if settings.anthropic_api_key is None:
            raise typer.BadParameter(
                "ANTHROPIC_API_KEY is required when using Anthropic. "
                "Set it in .env or as an env var."
            )
        api_key = settings.anthropic_api_key.get_secret_value()
        model = settings.anthropic_extraction_model
    else:
        raise typer.BadParameter(f"Unknown provider: {chosen_provider!r}. Use 'openai' or 'anthropic'.")

    llm_call = make_llm_caller(chosen_provider, api_key, model)
    start = time.monotonic()

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        if clean:
            clear_extracted(driver)
            print()

        print("Creating constraints for extracted entities...")
        create_extraction_constraints(driver)
        print()

        run_extraction(
            driver,
            llm_call,
            model,
            limit=limit or None,
            document_id=document or None,
        )

        verify(driver)

    elapsed = time.monotonic() - start
    print(f"\nDone in {_fmt_elapsed(elapsed)}.")


if __name__ == "__main__":
    app()
