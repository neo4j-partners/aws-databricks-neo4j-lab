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
from rich.table import Table

from .config import LibraryConfig
from .log import log
from .models import LibraryCounts
from .utils import poll_until


def get_library_status(
    client: WorkspaceClient,
    cluster_id: str,
) -> list[LibraryFullStatus]:
    """Get the installation status of all libraries on a cluster."""
    statuses = list(client.libraries.cluster_status(cluster_id))
    return statuses


def count_library_states(
    statuses: list[LibraryFullStatus],
) -> LibraryCounts:
    """Count libraries by state.

    Returns:
        LibraryCounts with total, installed, pending, and failed tallies.
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
    return LibraryCounts(total=total, installed=installed, pending=pending, failed=failed)


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
    log("Installing libraries...")

    libraries: list[Library] = []

    # Maven library (Neo4j Spark Connector)
    libraries.append(
        Library(maven=MavenLibrary(coordinates=config.neo4j_spark_connector))
    )

    # PyPI libraries
    for package in config.pypi_packages:
        libraries.append(Library(pypi=PythonPyPiLibrary(package=package)))

    client.libraries.install(cluster_id=cluster_id, libraries=libraries)

    log(f"  Requested installation of {len(libraries)} libraries")


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
    log("Waiting for libraries to install...")

    def check_status() -> tuple[bool, list[LibraryFullStatus]]:
        statuses = get_library_status(client, cluster_id)
        counts = count_library_states(statuses)
        log(
            f"  {counts.installed}/{counts.total} installed, "
            f"{counts.pending} pending, {counts.failed} failed"
        )
        return counts.pending == 0, statuses

    return poll_until(
        check_status,
        timeout_seconds=timeout_seconds,
        description="library installation",
    )


def print_library_status(statuses: list[LibraryFullStatus]) -> None:
    """Print a table of library installation statuses."""
    log()
    log("[bold]Library status:[/bold]")

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

    log(table)


def ensure_libraries_installed(
    client: WorkspaceClient,
    cluster_id: str,
    config: LibraryConfig,
) -> None:
    """Ensure all required libraries are installed on the cluster.

    Skips installation if libraries are already present and installed.
    """
    log()
    log("Checking library status...")

    statuses = get_library_status(client, cluster_id)
    counts = count_library_states(statuses)

    if counts.total > 0 and counts.pending == 0:
        log(f"  {counts.installed} libraries already installed - skipping installation.")
        print_library_status(statuses)
        return

    install_libraries(client, cluster_id, config)
    statuses = wait_for_libraries(client, cluster_id)
    print_library_status(statuses)

    counts = count_library_states(statuses)
    if counts.failed > 0:
        log(f"[yellow]WARNING: {counts.failed} library(ies) failed to install.[/yellow]")
