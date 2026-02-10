"""Upload workshop notebooks to a shared workspace folder.

Imports Jupyter notebooks and Python files into /Shared/aws-databricks-neo4j-lab/
so that workshop participants can browse and clone them into their own workspace.
"""

from __future__ import annotations

import base64
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.workspace import ImportFormat

from .config import NotebookConfig
from .log import log

# Workspace subdirectories that should be deleted before re-upload
# (to avoid stale artifacts from previous imports).
_DELETE_BEFORE_UPLOAD = {"neo4j_mcp_connection"}


def _delete_lab_subfolder(
    client: WorkspaceClient,
    workspace_folder: str,
    subfolder: str,
) -> None:
    """Recursively delete a lab subfolder from the workspace."""
    path = f"{workspace_folder}/{subfolder}"
    try:
        client.workspace.delete(path, recursive=True)
        log(f"  Deleted existing folder: {path}")
    except NotFound:
        pass


def _import_file(
    client: WorkspaceClient,
    local_path: Path,
    workspace_path: str,
) -> None:
    """Base64-encode a local file and import it into the workspace.

    Args:
        client: Databricks workspace client.
        local_path: Path to the local file.
        workspace_path: Destination path in the workspace.
    """
    content = base64.b64encode(local_path.read_bytes()).decode()
    fmt = ImportFormat.JUPYTER if local_path.suffix == ".ipynb" else ImportFormat.AUTO
    client.workspace.import_(
        path=workspace_path,
        format=fmt,
        content=content,
        overwrite=True,
    )


def upload_notebooks(client: WorkspaceClient, notebook_config: NotebookConfig) -> int:
    """Upload all lab notebooks to the shared workspace folder.

    Creates subdirectories for each lab and imports each file.

    Args:
        client: Databricks workspace client.
        notebook_config: Notebook upload configuration.

    Returns:
        Number of files uploaded.
    """
    log("Uploading notebooks to workspace...")
    log(f"  Target: {notebook_config.workspace_folder}")

    upload_files = notebook_config.get_upload_files()
    count = 0

    # Collect unique lab dirs to create
    lab_dirs = {lab_dir for _, lab_dir in upload_files}

    # Delete folders that need a clean re-import (e.g. neo4j_mcp_connection)
    for lab_dir in sorted(lab_dirs & _DELETE_BEFORE_UPLOAD):
        _delete_lab_subfolder(client, notebook_config.workspace_folder, lab_dir)

    for lab_dir in sorted(lab_dirs):
        folder = f"{notebook_config.workspace_folder}/{lab_dir}"
        client.workspace.mkdirs(folder)
        log(f"  Created folder: {folder}")

    for local_path, lab_dir in upload_files:
        workspace_path = f"{notebook_config.workspace_folder}/{lab_dir}/{local_path.name}"
        log(f"  Importing {lab_dir}/{local_path.name} ...")
        _import_file(client, local_path, workspace_path)
        count += 1

    log(f"  [green]Uploaded {count} file(s).[/green]")
    return count


def verify_notebook_upload(
    client: WorkspaceClient,
    notebook_config: NotebookConfig,
) -> list[str]:
    """List all objects in each lab subfolder and return their paths.

    Args:
        client: Databricks workspace client.
        notebook_config: Notebook upload configuration.

    Returns:
        List of workspace paths found.
    """
    log("Verifying notebook upload...")
    paths: list[str] = []

    lab_dirs = {lab_dir for _, lab_dir in notebook_config.get_upload_files()}
    for lab_dir in sorted(lab_dirs):
        folder = f"{notebook_config.workspace_folder}/{lab_dir}"
        try:
            for obj in client.workspace.list(folder):
                if obj.path:
                    paths.append(obj.path)
                    log(f"  {obj.path}")
        except NotFound:
            log(f"  [yellow]Folder not found: {folder}[/yellow]")

    log(f"  [green]Found {len(paths)} object(s) in workspace.[/green]")
    return paths


def get_workspace_folder_id(
    client: WorkspaceClient,
    folder_path: str,
) -> int | None:
    """Get the object_id of a workspace folder (needed for permissions API).

    Args:
        client: Databricks workspace client.
        folder_path: Absolute workspace path (e.g. "/Shared/my-folder").

    Returns:
        The object_id, or None if the folder does not exist.
    """
    try:
        status = client.workspace.get_status(folder_path)
        return status.object_id
    except NotFound:
        return None


def cleanup_notebooks(
    client: WorkspaceClient,
    notebook_config: NotebookConfig,
) -> None:
    """Delete the shared workspace folder and all its contents.

    Args:
        client: Databricks workspace client.
        notebook_config: Notebook upload configuration.
    """
    log(f"  Deleting workspace folder {notebook_config.workspace_folder} ...")
    try:
        client.workspace.delete(notebook_config.workspace_folder, recursive=True)
        log("    Done.")
    except NotFound:
        log("    Already deleted.")
