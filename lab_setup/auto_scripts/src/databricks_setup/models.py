"""Shared domain models used across the databricks_setup package."""

from dataclasses import dataclass

from databricks.sdk.service.compute import State
from databricks.sdk.service.sql import StatementState


@dataclass
class SqlStep:
    """A labelled SQL statement."""

    description: str
    sql: str


@dataclass
class SqlResult:
    """Result of a SQL statement execution."""

    state: StatementState | None = None
    row_count: int = 0


@dataclass
class ClusterInfo:
    """Cluster lookup result."""

    cluster_id: str
    state: State


@dataclass
class LibraryCounts:
    """Aggregated library installation state counts."""

    total: int
    installed: int
    pending: int
    failed: int
