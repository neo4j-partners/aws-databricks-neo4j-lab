"""Data file upload to Databricks volumes.

Handles uploading CSV and other data files to Unity Catalog volumes.
"""

from pathlib import Path

from databricks.sdk import WorkspaceClient
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import DataConfig, VolumeConfig
from .utils import print_header

console = Console()


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
    console.print(f"Source: {data_config.data_dir}")
    console.print(f"Target: {volume_config.dbfs_path}")
    console.print()

    files = data_config.get_upload_files()
    if not files:
        console.print("[yellow]No files found to upload.[/yellow]")
        return 0

    uploaded = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for local_path in files:
            task = progress.add_task(f"Uploading: {local_path.name}", total=1)

            target_path = f"{volume_config.volumes_path}/{local_path.name}"
            upload_file(client, local_path, target_path)
            uploaded += 1

            progress.update(task, completed=1)

    console.print()
    console.print(f"[green]Uploaded {uploaded} files.[/green]")
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
    console.print()
    console.print("Verifying upload...")

    files = client.files.list_directory_contents(volume_config.volumes_path)
    file_names = [f.name for f in files if f.name]

    for name in sorted(file_names):
        console.print(f"  {name}")

    console.print(f"  [green]Upload verified: {len(file_names)} files[/green]")
    return file_names
