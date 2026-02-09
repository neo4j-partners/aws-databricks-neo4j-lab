"""Cleanup logic for tearing down workshop resources.

Deletes permissions grants, workshop group, lakehouse schema (with tables),
volume, volume schema, and catalog.  Leaves the compute cluster intact.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

from .config import VolumeConfig
from .log import log
from .permissions import cleanup_permissions
from .utils import print_header
from .warehouse import execute_sql


def _drop_lakehouse_schema(
    client: WorkspaceClient,
    warehouse_id: str,
    volume_config: VolumeConfig,
    timeout_seconds: int,
) -> None:
    """Drop the lakehouse schema and all its tables via SQL CASCADE."""
    target = f"`{volume_config.catalog}`.`{volume_config.lakehouse_schema}`"
    log(f"  Dropping lakehouse schema {target} ...")
    try:
        execute_sql(
            client,
            warehouse_id,
            f"DROP SCHEMA IF EXISTS {target} CASCADE",
            timeout_seconds,
        )
        log("    Done.")
    except RuntimeError as e:
        log(f"    [yellow]Skipped: {e}[/yellow]")


def _delete_volume(client: WorkspaceClient, volume_config: VolumeConfig) -> None:
    """Delete the Unity Catalog volume."""
    log(f"  Deleting volume {volume_config.full_path} ...")
    try:
        client.volumes.delete(name=volume_config.full_path)
        log("    Done.")
    except NotFound:
        log("    Already deleted.")


def _delete_schema(client: WorkspaceClient, volume_config: VolumeConfig) -> None:
    """Delete the volume schema."""
    full_name = f"{volume_config.catalog}.{volume_config.schema}"
    log(f"  Deleting schema {full_name} ...")
    try:
        client.schemas.delete(full_name=full_name)
        log("    Done.")
    except NotFound:
        log("    Already deleted.")


def _delete_catalog(client: WorkspaceClient, volume_config: VolumeConfig) -> None:
    """Delete the catalog (force cascades to any remaining contents)."""
    log(f"  Deleting catalog {volume_config.catalog} ...")
    try:
        client.catalogs.delete(name=volume_config.catalog, force=True)
        log("    Done.")
    except NotFound:
        log("    Already deleted.")


def run_cleanup(
    client: WorkspaceClient,
    warehouse_id: str,
    volume_config: VolumeConfig,
    timeout_seconds: int,
) -> None:
    """Delete lakehouse schema, volume, volume schema, and catalog.

    Each step is idempotent — already-deleted resources are skipped.

    Args:
        client: Databricks workspace client.
        warehouse_id: SQL Warehouse ID (for DROP SCHEMA CASCADE).
        volume_config: Volume configuration identifying the resources.
        timeout_seconds: Timeout per SQL statement.
    """
    print_header("Cleaning Up Workshop Resources")

    # Permissions must be cleaned up before the catalog is deleted,
    # because we cannot revoke grants on a catalog that no longer exists.
    cleanup_permissions(client, volume_config)

    _drop_lakehouse_schema(client, warehouse_id, volume_config, timeout_seconds)
    _delete_volume(client, volume_config)
    _delete_schema(client, volume_config)
    _delete_catalog(client, volume_config)

    log()
    log("[green]Cleanup complete.[/green]")
