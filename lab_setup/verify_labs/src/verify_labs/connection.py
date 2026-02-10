"""Neo4j driver lifecycle and basic data-existence check."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

from neo4j import Driver, GraphDatabase
from rich.console import Console

from .config import Settings

console = Console()


@contextmanager
def connect(settings: Settings) -> Generator[Driver, None, None]:
    """Create a Neo4j driver, verify connectivity, yield it, then close."""
    console.print(f"Connecting to [bold]{settings.neo4j_uri}[/bold] ...")
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password.get_secret_value()),
    )
    start = time.time()
    driver.verify_connectivity()
    elapsed_ms = (time.time() - start) * 1000
    console.print(f"[green][OK][/green] Connected in {elapsed_ms:.0f}ms")
    try:
        yield driver
    finally:
        driver.close()


def check_data_exists(driver: Driver) -> bool:
    """Return True if the database contains at least one node."""
    records, _, _ = driver.execute_query("MATCH (n) RETURN count(n) AS cnt LIMIT 1")
    count = records[0]["cnt"]
    if count > 0:
        console.print(f"[green][OK][/green] Database contains {count:,} node(s)")
        return True
    console.print("[red][FAIL][/red] Database is empty — no nodes found")
    return False
