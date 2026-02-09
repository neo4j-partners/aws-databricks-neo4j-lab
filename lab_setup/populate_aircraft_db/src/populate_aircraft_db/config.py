"""Configuration: load Neo4j credentials from .env and resolve data directory."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import DirectoryPath, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved once at import time — stable regardless of cwd.
_PKG_DIR = Path(__file__).resolve().parent
_ENV_FILE = _PKG_DIR.parent.parent / ".env"
_DATA_DIR = _PKG_DIR.parent.parent.parent / "aircraft_digital_twin_data"


class Settings(BaseSettings):
    """Neo4j connection settings loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
    )

    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr

    data_dir: DirectoryPath = _DATA_DIR  # type: ignore[assignment]

    # OpenAI embeddings — only required for the `embed` command.
    openai_api_key: Optional[SecretStr] = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    # OpenAI chat model — used by the `extract` command.
    openai_extraction_model: str = "gpt-4o-mini"

    @model_validator(mode="after")
    def _check_uri_scheme(self) -> Settings:
        if not self.neo4j_uri.startswith(("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")):
            raise ValueError(
                f"NEO4J_URI must start with a valid scheme (neo4j+s://, bolt+s://, etc.), got: {self.neo4j_uri}"
            )
        return self
