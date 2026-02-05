"""Utilities for data loading, Neo4j operations, and Databricks AI services.

This module provides embedding generation using Databricks Foundation Model APIs
(hosted models like BGE and GTE) which are pre-deployed and ready to use.

Available Databricks Embedding Models:
- databricks-bge-large-en: 1024 dimensions, 512 token context
- databricks-gte-large-en: 1024 dimensions, 8192 token context

These models use OpenAI-compatible API format and are accessed via
the MLflow deployments client when running in Databricks.
"""

import asyncio
from pathlib import Path
from typing import Any

import mlflow.deployments
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings.base import Embeddings
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter
from neo4j_graphrag.llm.base import LLMInterface
from neo4j_graphrag.llm.types import LLMResponse
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load configuration from project root
_config_file = Path(__file__).parent.parent / "CONFIG.txt"
load_dotenv(_config_file)


# =============================================================================
# Configuration Classes
# =============================================================================

class Neo4jConfig(BaseSettings):
    """Neo4j configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    uri: str = Field(validation_alias="NEO4J_URI")
    username: str = Field(validation_alias="NEO4J_USERNAME")
    password: str = Field(validation_alias="NEO4J_PASSWORD")


class DatabricksConfig(BaseSettings):
    """Databricks configuration loaded from environment variables.

    For Databricks Foundation Model APIs (hosted models):
    - databricks-bge-large-en: 1024 dims, 512 token context, normalized
    - databricks-gte-large-en: 1024 dims, 8192 token context
    """

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    embedding_model_id: str = Field(
        default="databricks-bge-large-en",
        validation_alias="EMBEDDING_MODEL_ID"
    )
    llm_model_id: str = Field(
        default="databricks-meta-llama-3-3-70b-instruct",
        validation_alias="MODEL_ID"
    )


# =============================================================================
# Databricks Embeddings
# =============================================================================

class DatabricksEmbeddings(Embeddings):
    """Generate embeddings using Databricks Foundation Model APIs.

    Databricks provides pre-deployed embedding models as part of the
    Foundation Model APIs. These are ready to use without deployment.

    Available Models:
    - databricks-bge-large-en: 1024 dims, 512 token context
    - databricks-gte-large-en: 1024 dims, 8192 token context

    API Format (OpenAI-Compatible):
        Input:  {"input": ["text1", "text2"]}
        Output: {"data": [{"embedding": [0.1, ...]}, ...]}

    Example:
        >>> embedder = DatabricksEmbeddings(model_id="databricks-bge-large-en")
        >>> embedding = embedder.embed_query("test text")
        >>> len(embedding)
        1024
    """

    def __init__(self, model_id: str = "databricks-bge-large-en"):
        """Initialize the Databricks embeddings provider.

        Args:
            model_id: The Databricks Foundation Model endpoint name.
                      Default: databricks-bge-large-en (1024 dimensions)
        """
        self.model_id = model_id
        self._client = mlflow.deployments.get_deploy_client("databricks")

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single text string.

        Uses the MLflow deployments client to call the Databricks
        Foundation Model API with OpenAI-compatible format.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector (1024 dimensions)
        """
        response = self._client.predict(
            endpoint=self.model_id,
            inputs={"input": [text]},
        )
        return response["data"][0]["embedding"]


# =============================================================================
# Databricks LLM
# =============================================================================

class DatabricksLLM(LLMInterface):
    """LLM interface using Databricks Foundation Model APIs.

    Supports Databricks-hosted LLM endpoints like:
    - databricks-meta-llama-3-3-70b-instruct
    - databricks-dbrx-instruct
    - databricks-mixtral-8x7b-instruct

    Uses MLflow deployments client for API calls.
    """

    def __init__(self, model_id: str = "databricks-meta-llama-3-3-70b-instruct"):
        """Initialize the Databricks LLM provider.

        Args:
            model_id: The Databricks Foundation Model endpoint name.
        """
        self.model_id = model_id
        self._client = mlflow.deployments.get_deploy_client("databricks")

    def invoke(self, input: str) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            input: The prompt text

        Returns:
            LLMResponse containing the generated text
        """
        response = self._client.predict(
            endpoint=self.model_id,
            inputs={
                "messages": [{"role": "user", "content": input}],
                "max_tokens": 2048,
            },
        )
        content = response["choices"][0]["message"]["content"]
        return LLMResponse(content=content)

    async def ainvoke(self, input: str) -> LLMResponse:
        """Async version of invoke (runs synchronously)."""
        return self.invoke(input)


# =============================================================================
# AI Services Factory Functions
# =============================================================================

def get_embedder() -> DatabricksEmbeddings:
    """Get embedder using Databricks Foundation Model APIs.

    Returns:
        DatabricksEmbeddings configured for BGE-large (1024 dimensions)
    """
    config = DatabricksConfig()
    return DatabricksEmbeddings(model_id=config.embedding_model_id)


def get_llm() -> DatabricksLLM:
    """Get LLM using Databricks Foundation Model APIs.

    Returns:
        DatabricksLLM configured from environment
    """
    config = DatabricksConfig()
    return DatabricksLLM(model_id=config.llm_model_id)


# =============================================================================
# Neo4j Connection
# =============================================================================

class Neo4jConnection:
    """Manages Neo4j database connection."""

    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """Initialize and connect to Neo4j.

        Args:
            uri: Neo4j URI. If not provided, reads from NEO4J_URI env var / CONFIG.txt.
            username: Neo4j username. If not provided, reads from NEO4J_USERNAME env var / CONFIG.txt.
            password: Neo4j password. If not provided, reads from NEO4J_PASSWORD env var / CONFIG.txt.
        """
        if uri and username and password:
            self.uri = uri
            self.username = username
            self.password = password
        else:
            config = Neo4jConfig()
            self.uri = uri or config.uri
            self.username = username or config.username
            self.password = password or config.password
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )

    def verify(self):
        """Verify the connection is working."""
        self.driver.verify_connectivity()
        print("Connected to Neo4j successfully!")
        return self

    def clear_chunks(self):
        """Remove all Document and Chunk nodes (preserves aircraft graph from Lab 5)."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n) WHERE n:Document OR n:Chunk
                DETACH DELETE n
                RETURN count(n) as deleted
            """)
            count = result.single()["deleted"]
            print(f"Deleted {count} Document/Chunk nodes")
        return self

    def get_graph_stats(self):
        """Show current graph statistics."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WITH labels(n) as nodeLabels
                UNWIND nodeLabels as label
                RETURN label, count(*) as count
                ORDER BY label
            """)
            print("=== Graph Statistics ===")
            for record in result:
                print(f"  {record['label']}: {record['count']}")
        return self

    def close(self):
        """Close the database connection."""
        self.driver.close()
        print("Connection closed.")


# =============================================================================
# Data Loading
# =============================================================================

# Default Volume path for workshop data
DEFAULT_VOLUME_PATH = "/Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume"


class DataLoader:
    """Handles loading text data from files (local or Unity Catalog Volume)."""

    def __init__(self, file_path: str):
        """Initialize with path to data file.

        Args:
            file_path: Path to the file. Can be:
                - Relative path (loaded from current directory)
                - Absolute local path
                - Volume path (e.g., /Volumes/catalog/schema/volume/file.md)
        """
        self.file_path = Path(file_path)
        self._text = None

    @property
    def text(self) -> str:
        """Load and return the text content from the file."""
        if self._text is None:
            self._text = self.file_path.read_text().strip()
        return self._text

    def get_metadata(self) -> dict:
        """Return metadata about the loaded file."""
        return {
            "path": str(self.file_path),
            "name": self.file_path.name,
            "size": len(self.text)
        }


class VolumeDataLoader:
    """Handles loading text data from Unity Catalog Volumes.

    Unity Catalog Volumes are accessible as file paths in Databricks:
    /Volumes/<catalog>/<schema>/<volume>/<file>

    Example:
        >>> loader = VolumeDataLoader("maintenance_manual.md")
        >>> text = loader.text
    """

    def __init__(self, file_name: str, volume_path: str = DEFAULT_VOLUME_PATH):
        """Initialize with file name and optional Volume path.

        Args:
            file_name: Name of the file in the Volume (e.g., "maintenance_manual.md")
            volume_path: Path to the Unity Catalog Volume.
                        Defaults to /Volumes/aws-databricks-neo4j-lab/lab-schema/lab-volume
        """
        self.volume_path = Path(volume_path)
        self.file_name = file_name
        self.file_path = self.volume_path / file_name
        self._text = None

    @property
    def text(self) -> str:
        """Load and return the text content from the Volume."""
        if self._text is None:
            self._text = self.file_path.read_text().strip()
        return self._text

    def get_metadata(self) -> dict:
        """Return metadata about the loaded file."""
        return {
            "path": str(self.file_path),
            "name": self.file_name,
            "volume": str(self.volume_path),
            "size": len(self.text)
        }


# =============================================================================
# Text Splitting
# =============================================================================

def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Split text into chunks using FixedSizeSplitter.

    Args:
        text: Text to split
        chunk_size: Maximum characters per chunk
        chunk_overlap: Characters to overlap between chunks

    Returns:
        List of chunk text strings
    """
    splitter = FixedSizeSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        approximate=True
    )
    result = asyncio.run(splitter.run(text))
    return [chunk.text for chunk in result.chunks]


# =============================================================================
# Embedding Configuration
# =============================================================================

# Databricks BGE and GTE models produce 1024-dimensional vectors
EMBEDDING_DIMENSIONS = 1024
