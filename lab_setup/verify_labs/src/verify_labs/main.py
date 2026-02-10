"""CLI entry point: verify-labs."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from .config import Settings
from .connection import check_data_exists, connect
from .lab5_queries import ALL_QUERIES, NOTEBOOK_01, NOTEBOOK_02
from .query_runner import QuerySpec, display_result, display_summary, run_query

app = typer.Typer(help="Verify Neo4j data loaded by workshop lab notebooks.")
console = Console()


def _load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        console.print("Ensure NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD are set in lab_setup/.env")
        raise typer.Exit(code=1) from exc


@app.command()
def check() -> None:
    """Quick connectivity test — verify connection and that data exists."""
    settings = _load_settings()
    with connect(settings) as driver:
        if not check_data_exists(driver):
            raise typer.Exit(code=1)


@app.command()
def lab5(
    notebook: Annotated[
        str | None,
        typer.Option("-n", "--notebook", help="Filter by notebook: '01' or '02'"),
    ] = None,
) -> None:
    """Run Lab 5 verification queries against Neo4j."""
    queries: list[QuerySpec]
    if notebook == "01":
        queries = NOTEBOOK_01
    elif notebook == "02":
        queries = NOTEBOOK_02
    elif notebook is None:
        queries = ALL_QUERIES
    else:
        console.print(f"[red]Unknown notebook '{notebook}'. Use '01' or '02'.[/red]")
        raise typer.Exit(code=1)

    console.rule(f"[bold]Lab 5 Verification — {len(queries)} queries[/bold]")

    settings = _load_settings()
    with connect(settings) as driver:
        results = []
        for spec in queries:
            result = run_query(driver, spec)
            display_result(result)
            results.append(result)

        display_summary(results)

    if any(not r.passed for r in results):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
