"""Configuration management for Databricks setup.

Loads configuration from environment variables, .env files, and CLI arguments.
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

    def get_node_type(self) -> str:
        """Get node type, auto-detecting based on cloud provider if not set."""
        if self.node_type:
            return self.node_type
        if self.cloud_provider == "azure":
            return "Standard_D4ds_v5"  # 16 GB Memory, 4 Cores
        return "m5.xlarge"  # AWS default: 16 GB Memory, 4 Cores


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
    def from_string(cls, volume_spec: str) -> VolumeConfig:
        """Parse 'catalog.schema.volume' format."""
        parts = volume_spec.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Volume must be in format 'catalog.schema.volume', got: {volume_spec}"
            )
        return cls(catalog=parts[0], schema=parts[1], volume=parts[2])

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
    user_email: str | None = None
    databricks_profile: str | None = None

    @classmethod
    def load(cls) -> Config:
        """Load configuration from environment and .env file."""
        default_env = Path(__file__).parent.parent.parent.parent / ".env"
        if default_env.exists():
            load_dotenv(default_env)

        config = cls()

        # Warehouse settings
        config.warehouse = WarehouseConfig.from_env()

        # Cluster settings from environment
        if val := os.getenv("CLUSTER_NAME"):
            config.cluster.name = val
        if val := os.getenv("SPARK_VERSION"):
            config.cluster.spark_version = val
        if val := os.getenv("AUTOTERMINATION_MINUTES"):
            config.cluster.autotermination_minutes = int(val)
        if val := os.getenv("RUNTIME_ENGINE"):
            config.cluster.runtime_engine = val
        if val := os.getenv("NODE_TYPE"):
            config.cluster.node_type = val
        if val := os.getenv("INSTANCE_PROFILE_ARN"):
            config.cluster.instance_profile_arn = val
        if val := os.getenv("CLOUD_PROVIDER"):
            config.cluster.cloud_provider = val.lower()

        # User settings
        if val := os.getenv("USER_EMAIL"):
            config.user_email = val

        # Databricks profile
        if val := os.getenv("DATABRICKS_PROFILE"):
            config.databricks_profile = val

        return config

    def prepare(
        self,
        volume: str | None = None,
        profile: str | None = None,
        resolve_user: bool = False,
        require_data_dir: bool = False,
    ) -> WorkspaceClient:
        """Finalize config and return a ready WorkspaceClient.

        Handles volume parsing, profile resolution, user detection,
        and data-directory validation — all the init logic that runs
        after ``load()`` but before the tracks start.

        Args:
            volume: Volume spec in 'catalog.schema.volume' format.
                    Parsed into ``self.volume`` when provided.
            profile: CLI-provided Databricks profile (overrides env).
            resolve_user: If True and ``user_email`` is unset, detect
                          the current workspace user.
            require_data_dir: If True, raise if ``data.data_dir`` is missing.

        Returns:
            An authenticated WorkspaceClient.
        """
        from .utils import get_current_user, get_workspace_client

        if volume is not None:
            self.volume = VolumeConfig.from_string(volume)

        effective_profile = profile or self.databricks_profile
        client = get_workspace_client(effective_profile)

        if resolve_user and not self.user_email:
            self.user_email = get_current_user(client)

        if require_data_dir and not self.data.data_dir.exists():
            raise RuntimeError(f"Data directory not found: {self.data.data_dir}")

        return client


@dataclass
class SetupResult:
    """Outcome of the two parallel setup tracks."""

    cluster_id: str | None = None
    tables_ok: bool | None = None

    @property
    def success(self) -> bool:
        """True unless the tables track explicitly failed."""
        return self.tables_ok is not False
