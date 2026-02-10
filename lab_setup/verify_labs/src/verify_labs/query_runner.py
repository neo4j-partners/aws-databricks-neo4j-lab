"""Reusable query runner: execute queries, display rich tables, summarise results."""

from __future__ import annotations

from dataclasses import dataclass, field

from neo4j import Driver
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class QuerySpec:
    """Describes a single verification query."""

    name: str
    description: str
    cypher: str
    notebook: str  # e.g. "01" or "02"
    min_rows: int = 1


@dataclass
class QueryResult:
    """Outcome of running a single QuerySpec."""

    spec: QuerySpec
    passed: bool = False
    row_count: int = 0
    rows: list[dict] = field(default_factory=list)
    error: str | None = None


def run_query(driver: Driver, spec: QuerySpec) -> QueryResult:
    """Execute *spec* and return a QueryResult."""
    result = QueryResult(spec=spec)
    try:
        records, _, _ = driver.execute_query(spec.cypher)
        result.rows = [dict(r) for r in records]
        result.row_count = len(result.rows)
        result.passed = result.row_count >= spec.min_rows
    except Exception as exc:
        result.error = str(exc)
        result.passed = False
    return result


def display_result(result: QueryResult) -> None:
    """Print a rich table for one query result."""
    badge = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
    console.print(
        f"\n{badge}  [bold]{result.spec.name}[/bold]  "
        f"(notebook {result.spec.notebook}) — {result.spec.description}"
    )

    if result.error:
        console.print(f"  [red]Error:[/red] {result.error}")
        return

    if not result.rows:
        console.print("  (no rows returned)")
        return

    # Build a rich table from the first ≤20 rows
    columns = list(result.rows[0].keys())
    table = Table(show_lines=False, pad_edge=False)
    for col in columns:
        table.add_column(col)
    for row in result.rows[:20]:
        table.add_row(*(str(row[c]) for c in columns))
    if result.row_count > 20:
        table.add_row(*["..." for _ in columns])

    console.print(table)
    console.print(f"  ({result.row_count} row(s))")


def display_summary(results: list[QueryResult]) -> None:
    """Print a final scorecard."""
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    colour = "green" if passed == total else "red"

    console.print()
    console.rule("[bold]Summary[/bold]")
    console.print(f"[{colour}]{passed}/{total} queries passed[/{colour}]")

    if passed < total:
        console.print("\n[red]Failed queries:[/red]")
        for r in results:
            if not r.passed:
                reason = r.error or f"expected >= {r.spec.min_rows} rows, got {r.row_count}"
                console.print(f"  - {r.spec.name}: {reason}")
