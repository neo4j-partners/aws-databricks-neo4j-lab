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
import concurrent.futures
from pathlib import Path

import mlflow.deployments
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings.base import Embedder
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter
from neo4j_graphrag.llm.base import LLMInterface
from neo4j_graphrag.llm.types import LLMResponse


# =============================================================================
# Default Model Configuration
# =============================================================================

DEFAULT_EMBEDDING_MODEL = "databricks-bge-large-en"
DEFAULT_LLM_MODEL = "databricks-meta-llama-3-3-70b-instruct"


# =============================================================================
# Databricks Embeddings
# =============================================================================

class DatabricksEmbeddings(Embedder):
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

def get_embedder(model_id: str = DEFAULT_EMBEDDING_MODEL) -> DatabricksEmbeddings:
    """Get embedder using Databricks Foundation Model APIs.

    Args:
        model_id: Databricks embedding endpoint name.
                  Default: databricks-bge-large-en (1024 dimensions)

    Returns:
        DatabricksEmbeddings configured for the specified model
    """
    return DatabricksEmbeddings(model_id=model_id)


def get_llm(model_id: str = DEFAULT_LLM_MODEL) -> DatabricksLLM:
    """Get LLM using Databricks Foundation Model APIs.

    Args:
        model_id: Databricks LLM endpoint name.
                  Default: databricks-meta-llama-3-3-70b-instruct

    Returns:
        DatabricksLLM configured for the specified model
    """
    return DatabricksLLM(model_id=model_id)


# =============================================================================
# Neo4j Connection
# =============================================================================

class Neo4jConnection:
    """Manages Neo4j database connection."""

    def __init__(self, uri: str, username: str, password: str):
        """Initialize and connect to Neo4j.

        Args:
            uri: Neo4j URI (e.g., "neo4j+s://xxxxxxxx.databases.neo4j.io")
            username: Neo4j username (typically "neo4j")
            password: Neo4j password
        """
        self.uri = uri
        self.username = username
        self.password = password
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
        records, _, _ = self.driver.execute_query("""
            MATCH (n) WHERE n:Document OR n:Chunk
            DETACH DELETE n
            RETURN count(n) as deleted
        """)
        count = records[0]["deleted"]
        print(f"Deleted {count} Document/Chunk nodes")
        return self

    def get_graph_stats(self):
        """Show current graph statistics."""
        records, _, _ = self.driver.execute_query("""
            MATCH (n)
            WITH labels(n) as nodeLabels
            UNWIND nodeLabels as label
            RETURN label, count(*) as count
            ORDER BY label
        """)
        print("=== Graph Statistics ===")
        for record in records:
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
    # Run in a separate thread to avoid "asyncio.run() cannot be called from
    # a running event loop" in Jupyter/Databricks environments.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(asyncio.run, splitter.run(text)).result()
    return [chunk.text for chunk in result.chunks]


# =============================================================================
# Embedding Configuration
# =============================================================================

# Databricks BGE and GTE models produce 1024-dimensional vectors
EMBEDDING_DIMENSIONS = 1024
