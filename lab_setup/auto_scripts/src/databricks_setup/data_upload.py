"""Data file upload to Databricks volumes.

Handles uploading CSV and other data files to Unity Catalog volumes.
"""

import time
from pathlib import Path

from databricks.sdk import WorkspaceClient

from .config import DataConfig, VolumeConfig
from .log import log
from .utils import print_header


def upload_file(
    client: WorkspaceClient,
    local_path: Path,
    volume_path: str,
) -> None:
    """Upload a single file to a Databricks volume.

    Args:
        client: Databricks workspace client.
        local_path: Path to the local file.
        volume_path: Target path in the volume (e.g., /Volumes/catalog/schema/volume/file.csv).
    """
    with open(local_path, "rb") as f:
        client.files.upload(volume_path, f, overwrite=True)


def upload_data_files(
    client: WorkspaceClient,
    data_config: DataConfig,
    volume_config: VolumeConfig,
) -> int:
    """Upload all data files to the Databricks volume.

    Args:
        client: Databricks workspace client.
        data_config: Data file configuration.
        volume_config: Volume configuration.

    Returns:
        Number of files uploaded.
    """
    print_header("Uploading Data Files")
    log(f"Source: {data_config.data_dir}")
    log(f"Target: {volume_config.dbfs_path}")
    log()

    files = data_config.get_upload_files()
    if not files:
        log("[yellow]No files found to upload.[/yellow]")
        return 0

    uploaded = 0
    total = len(files)
    for local_path in files:
        target_path = f"{volume_config.volumes_path}/{local_path.name}"
        log(f"  [{uploaded + 1}/{total}] Uploading: {local_path.name}")
        t0 = time.monotonic()
        upload_file(client, local_path, target_path)
        elapsed = time.monotonic() - t0
        uploaded += 1
        log(f"         Done ({elapsed:.1f}s)")

    log()
    log(f"[green]Uploaded {uploaded} files.[/green]")
    return uploaded


def verify_upload(
    client: WorkspaceClient,
    volume_config: VolumeConfig,
) -> list[str]:
    """Verify files were uploaded by listing the volume contents.

    Args:
        client: Databricks workspace client.
        volume_config: Volume configuration.

    Returns:
        List of file names in the volume.
    """
    log()
    log("Verifying upload...")

    files = client.files.list_directory_contents(volume_config.volumes_path)
    file_names = [f.name for f in files if f.name]

    for name in sorted(file_names):
        log(f"  {name}")

    log(f"  [green]Upload verified: {len(file_names)} files[/green]")
    return file_names
