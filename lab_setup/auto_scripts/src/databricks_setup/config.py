"""Configuration management for Databricks setup.

Loads configuration from environment variables and .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


@dataclass
class ClusterConfig:
    """Cluster configuration settings."""

    name: str = "Small Spark 4.0"
    spark_version: str = "17.3.x-cpu-ml-scala2.13"  # 17.3 LTS ML (Spark 4.0.0)
    autotermination_minutes: int = 30
    runtime_engine: str = "STANDARD"  # or "PHOTON"
    node_type: str | None = None  # Auto-detected from cloud provider
    instance_profile_arn: str | None = None  # AWS instance profile for cluster nodes
    cloud_provider: str = "aws"

    @classmethod
    def from_env(cls) -> ClusterConfig:
        """Load cluster config from environment."""
        config = cls()
        if val := os.getenv("CLUSTER_NAME"):
            config.name = val
        if val := os.getenv("SPARK_VERSION"):
            config.spark_version = val
        if val := os.getenv("AUTOTERMINATION_MINUTES"):
            config.autotermination_minutes = int(val)
        if val := os.getenv("RUNTIME_ENGINE"):
            config.runtime_engine = val
        if val := os.getenv("NODE_TYPE"):
            config.node_type = val
        if val := os.getenv("INSTANCE_PROFILE_ARN"):
            config.instance_profile_arn = val
        if val := os.getenv("CLOUD_PROVIDER"):
            config.cloud_provider = val.lower()
        return config

    def get_node_type(self) -> str:
        """Get node type, auto-detecting based on cloud provider if not set."""
        if self.node_type:
            return self.node_type
        if self.cloud_provider == "azure":
            return "Standard_D4ds_v5"  # 16 GB Memory, 4 Cores
        return "m5.large"  # AWS default: 8 GB Memory, 2 Cores


@dataclass
class LibraryConfig:
    """Library installation configuration."""

    neo4j_spark_connector: str = "org.neo4j:neo4j-connector-apache-spark_2.13:5.3.10_for_spark_3"
    pypi_packages: list[str] = field(default_factory=lambda: [
        "neo4j==6.0.2",
        "databricks-agents>=1.2.0",
        "langgraph==1.0.5",
        "langchain-openai==1.1.2",
        "pydantic==2.12.5",
        "langchain-core>=1.2.0",
        "databricks-langchain>=0.11.0",
        "dspy>=3.0.4",
        "neo4j-graphrag>=1.13.0",
        "beautifulsoup4>=4.12.0",
        "sentence_transformers",
    ])


@dataclass
class VolumeConfig:
    """Unity Catalog volume configuration."""

    catalog: str = "aws-databricks-neo4j-lab"
    schema: str = "lab-schema"
    volume: str = "lab-volume"
    lakehouse_schema: str = "lakehouse"

    @classmethod
    def from_env(cls) -> VolumeConfig:
        """Load volume config from environment."""
        config = cls()
        if val := os.getenv("CATALOG_NAME"):
            config.catalog = val
        if val := os.getenv("VOLUME_SCHEMA"):
            config.schema = val
        if val := os.getenv("VOLUME_NAME"):
            config.volume = val
        if val := os.getenv("LAKEHOUSE_SCHEMA"):
            config.lakehouse_schema = val
        return config

    @property
    def full_path(self) -> str:
        """Return the full volume path for display."""
        return f"{self.catalog}.{self.schema}.{self.volume}"

    @property
    def dbfs_path(self) -> str:
        """Return the DBFS path for the volume."""
        return f"dbfs:/Volumes/{self.catalog}/{self.schema}/{self.volume}"

    @property
    def volumes_path(self) -> str:
        """Return the /Volumes path (for Spark SQL)."""
        return f"/Volumes/{self.catalog}/{self.schema}/{self.volume}"


@dataclass
class DataConfig:
    """Data file configuration."""

    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent.parent / "aircraft_digital_twin_data")
    excluded_files: tuple[str, ...] = ("README_LARGE_DATASET.md", "ARCHITECTURE.md")

    def get_upload_files(self) -> list[Path]:
        """Get list of files to upload (CSVs and MDs, excluding specified files)."""
        files = []
        for pattern in ("*.csv", "*.md"):
            for f in self.data_dir.glob(pattern):
                if f.name not in self.excluded_files:
                    files.append(f)
        return sorted(files)


@dataclass
class NotebookConfig:
    """Configuration for uploading workshop notebooks to the workspace."""

    workspace_folder: str = "/Shared/aws-databricks-neo4j-lab"
    upload_folder: str = "labs"
    repo_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent.parent,
    )
    lab_notebooks: tuple[tuple[str, tuple[str, ...], str], ...] = (
        ("Lab_5_Databricks_ETL_Neo4j", (
            "01_aircraft_etl_to_neo4j.ipynb",
            "02_load_neo4j_full.ipynb",
        ), "Lab_5_Databricks_ETL_Neo4j"),
        ("Lab_7_Semantic_Search", (
            "03_data_and_embeddings.ipynb",
            "04_graphrag_retrievers.ipynb",
            "05_hybrid_retrievers.ipynb",
            "data_utils.py",
        ), "Lab_7_Semantic_Search"),
        ("lab_setup/neo4j_mcp_connection", (
            "neo4j_mcp_agent.py",
            "neo4j-mcp-agent-deploy.ipynb",
            "neo4j-mcp-http-connection.ipynb",
        ), "neo4j_mcp_connection"),
    )

    @classmethod
    def from_env(cls) -> NotebookConfig:
        """Load notebook config from environment."""
        config = cls()
        if val := os.getenv("NOTEBOOK_WORKSPACE_FOLDER"):
            config.workspace_folder = val
        return config

    def get_upload_files(self) -> list[tuple[Path, str]]:
        """Return (local_path, workspace_subdir) pairs for all files to upload.

        Raises:
            FileNotFoundError: If any expected file is missing on disk.
        """
        files: list[tuple[Path, str]] = []
        for lab_dir, filenames, workspace_subdir in self.lab_notebooks:
            for name in filenames:
                local = self.repo_root / lab_dir / name
                if not local.exists():
                    raise FileNotFoundError(f"Expected notebook not found: {local}")
                files.append((local, workspace_subdir))
        return files


@dataclass
class WarehouseConfig:
    """SQL Warehouse configuration."""

    name: str = "Starter Warehouse"
    timeout_seconds: int = 600

    @classmethod
    def from_env(cls) -> WarehouseConfig:
        """Load warehouse config from environment."""
        config = cls()
        if val := os.getenv("WAREHOUSE_NAME"):
            config.name = val
        if val := os.getenv("WAREHOUSE_TIMEOUT"):
            config.timeout_seconds = int(val)
        return config


@dataclass
class Config:
    """Main configuration container."""

    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    library: LibraryConfig = field(default_factory=LibraryConfig)
    volume: VolumeConfig = field(default_factory=VolumeConfig)
    data: DataConfig = field(default_factory=DataConfig)
    warehouse: WarehouseConfig = field(default_factory=WarehouseConfig)
    notebook: NotebookConfig = field(default_factory=NotebookConfig)
    users_csv: Path | None = None
    user_email: str | None = None
    databricks_profile: str | None = None

    @classmethod
    def load(cls) -> Config:
        """Load configuration from environment and .env file."""
        default_env = Path(__file__).parent.parent.parent.parent / ".env"
        if default_env.exists():
            load_dotenv(default_env)

        config = cls()

        config.cluster = ClusterConfig.from_env()
        config.volume = VolumeConfig.from_env()
        config.warehouse = WarehouseConfig.from_env()
        config.notebook = NotebookConfig.from_env()

        # Users CSV path
        if val := os.getenv("USERS_CSV"):
            config.users_csv = Path(val)

        # User settings
        if val := os.getenv("USER_EMAIL"):
            config.user_email = val

        # Databricks profile
        if val := os.getenv("DATABRICKS_PROFILE"):
            config.databricks_profile = val

        return config

    def prepare(self) -> WorkspaceClient:
        """Finalize config and return a ready WorkspaceClient.

        Handles profile resolution, user detection, and data-directory
        validation — all the init logic that runs after ``load()`` but
        before the tracks start.

        Returns:
            An authenticated WorkspaceClient.
        """
        from .utils import get_current_user, get_workspace_client

        client = get_workspace_client(self.databricks_profile)

        if not self.user_email:
            self.user_email = get_current_user(client)

        if not self.data.data_dir.exists():
            raise RuntimeError(f"Data directory not found: {self.data.data_dir}")

        return client


@dataclass
class SetupResult:
    """Outcome of the setup tracks."""

    cluster_ok: bool = True
    tables_ok: bool = True
    notebooks_ok: bool = True
    lockdown_ok: bool = True

    @property
    def success(self) -> bool:
        """True unless any track failed."""
        return self.cluster_ok and self.tables_ok and self.notebooks_ok and self.lockdown_ok
