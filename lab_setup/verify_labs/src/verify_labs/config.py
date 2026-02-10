"""Configuration: load Neo4j credentials from lab_setup/.env."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved once at import time — stable regardless of cwd.
_PKG_DIR = Path(__file__).resolve().parent
_ENV_FILE = _PKG_DIR.parent.parent.parent / ".env"  # reaches lab_setup/


class Settings(BaseSettings):
    """Neo4j connection settings loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr

    @model_validator(mode="after")
    def _check_uri_scheme(self) -> Settings:
        if not self.neo4j_uri.startswith(
            ("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://", "bolt+ssc://")
        ):
            raise ValueError(
                f"NEO4J_URI must start with a valid scheme "
                f"(neo4j+s://, bolt+s://, etc.), got: {self.neo4j_uri}"
            )
        return self
