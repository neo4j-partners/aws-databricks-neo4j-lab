"""Library installation management for Databricks clusters.

Handles installing Maven and PyPI libraries on clusters.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import (
    Library,
    LibraryFullStatus,
    LibraryInstallStatus,
    MavenLibrary,
    PythonPyPiLibrary,
)
from rich.console import Console
from rich.table import Table

from .config import LibraryConfig
from .utils import poll_until

console = Console()


def get_library_status(
    client: WorkspaceClient,
    cluster_id: str,
) -> list[LibraryFullStatus]:
    """Get the installation status of all libraries on a cluster."""
    statuses = list(client.libraries.cluster_status(cluster_id))
    return statuses


def count_library_states(
    statuses: list[LibraryFullStatus],
) -> tuple[int, int, int, int]:
    """Count libraries by state.

    Returns:
        Tuple of (total, installed, pending, failed).
    """
    total = len(statuses)
    installed = sum(1 for s in statuses if s.status == LibraryInstallStatus.INSTALLED)
    pending = sum(
        1 for s in statuses
        if s.status in (
            LibraryInstallStatus.PENDING,
            LibraryInstallStatus.RESOLVING,
            LibraryInstallStatus.INSTALLING,
        )
    )
    failed = sum(1 for s in statuses if s.status == LibraryInstallStatus.FAILED)
    return total, installed, pending, failed


def install_libraries(
    client: WorkspaceClient,
    cluster_id: str,
    config: LibraryConfig,
) -> None:
    """Install Maven and PyPI libraries on a cluster.

    Args:
        client: Databricks workspace client.
        cluster_id: Target cluster ID.
        config: Library configuration.
    """
    console.print("Installing libraries...")

    libraries: list[Library] = []

    # Maven library (Neo4j Spark Connector)
    libraries.append(
        Library(maven=MavenLibrary(coordinates=config.neo4j_spark_connector))
    )

    # PyPI libraries
    for package in config.pypi_packages:
        libraries.append(Library(pypi=PythonPyPiLibrary(package=package)))

    client.libraries.install(cluster_id=cluster_id, libraries=libraries)

    console.print(f"  Requested installation of {len(libraries)} libraries")


def wait_for_libraries(
    client: WorkspaceClient,
    cluster_id: str,
    timeout_seconds: int = 600,
) -> list[LibraryFullStatus]:
    """Wait for all libraries to finish installing.

    Args:
        client: Databricks workspace client.
        cluster_id: Cluster ID.
        timeout_seconds: Maximum time to wait.

    Returns:
        Final library statuses.
    """
    console.print("Waiting for libraries to install...")

    def check_status() -> tuple[bool, list[LibraryFullStatus]]:
        statuses = get_library_status(client, cluster_id)
        total, installed, pending, failed = count_library_states(statuses)
        console.print(
            f"  {installed}/{total} installed, {pending} pending, {failed} failed"
        )
        return pending == 0, statuses

    return poll_until(
        check_status,
        timeout_seconds=timeout_seconds,
        description="library installation",
    )


def print_library_status(statuses: list[LibraryFullStatus]) -> None:
    """Print a table of library installation statuses."""
    console.print()
    console.print("[bold]Library status:[/bold]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Status", style="dim", width=12)
    table.add_column("Library")

    for status in statuses:
        lib = status.library
        if lib:
            if lib.maven:
                name = lib.maven.coordinates or "unknown"
            elif lib.pypi:
                name = lib.pypi.package or "unknown"
            else:
                name = str(lib)
        else:
            name = "unknown"

        status_style = ""
        if status.status == LibraryInstallStatus.INSTALLED:
            status_style = "green"
        elif status.status == LibraryInstallStatus.FAILED:
            status_style = "red"

        table.add_row(f"[{status_style}]{status.status}[/{status_style}]", name)

    console.print(table)


def ensure_libraries_installed(
    client: WorkspaceClient,
    cluster_id: str,
    config: LibraryConfig,
) -> None:
    """Ensure all required libraries are installed on the cluster.

    Skips installation if libraries are already present and installed.
    """
    console.print()
    console.print("Checking library status...")

    statuses = get_library_status(client, cluster_id)
    total, installed, pending, failed = count_library_states(statuses)

    if total > 0 and pending == 0:
        console.print(f"  {installed} libraries already installed - skipping installation.")
        print_library_status(statuses)
        return

    install_libraries(client, cluster_id, config)
    statuses = wait_for_libraries(client, cluster_id)
    print_library_status(statuses)

    _, _, _, failed = count_library_states(statuses)
    if failed > 0:
        console.print(f"[yellow]WARNING: {failed} library(ies) failed to install.[/yellow]")
