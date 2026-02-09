"""Cluster management for Databricks setup.

Handles cluster creation, starting, waiting for ready state,
and per-user cluster lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import (
    AwsAttributes,
    AwsAvailability,
    DataSecurityMode,
    EbsVolumeType,
    RuntimeEngine,
    State,
)

from .config import ClusterConfig
from .log import log
from .models import ClusterInfo
from .users import cluster_name_for_user
from .utils import poll_until


def ensure_instance_profile_registered(
    client: WorkspaceClient,
    instance_profile_arn: str,
    iam_role_arn: str | None = None,
) -> None:
    """Check if an instance profile is registered in the workspace, and register it if not.

    Args:
        client: Databricks workspace client.
        instance_profile_arn: The ARN of the instance profile.
        iam_role_arn: Optional IAM role ARN backing the instance profile.
    """
    registered = {ip.instance_profile_arn for ip in client.instance_profiles.list()}

    if instance_profile_arn in registered:
        log(f"  Instance profile already registered: {instance_profile_arn}")
        return

    log(f"  Registering instance profile: {instance_profile_arn}")
    client.instance_profiles.add(
        instance_profile_arn=instance_profile_arn,
        iam_role_arn=iam_role_arn,
        skip_validation=True,
    )
    log("  Registered successfully.")


def find_cluster(client: WorkspaceClient, cluster_name: str) -> ClusterInfo | None:
    """Find an existing cluster by name.

    Returns:
        ClusterInfo if found, None otherwise.
    """
    clusters = client.clusters.list()
    for cluster in clusters:
        if cluster.cluster_name == cluster_name and cluster.cluster_id and cluster.state:
            return ClusterInfo(cluster_id=cluster.cluster_id, state=cluster.state)
    return None


def create_cluster(
    client: WorkspaceClient,
    config: ClusterConfig,
    user_email: str,
) -> str:
    """Create a new single-node cluster for the workshop.

    Args:
        client: Databricks workspace client.
        config: Cluster configuration.
        user_email: Email of the user who will own the cluster.

    Returns:
        The cluster ID of the created cluster.
    """
    node_type = config.get_node_type()

    # Base Spark configuration for single-node mode
    spark_conf = {
        "spark.databricks.cluster.profile": "singleNode",
        "spark.master": "local[*]",
    }

    custom_tags = {"ResourceClass": "SingleNode"}

    # AWS-specific configuration (EBS volumes + instance profile)
    aws_attributes = None
    if config.cloud_provider != "azure":
        aws_attributes = AwsAttributes(
            availability=AwsAvailability.ON_DEMAND,
            first_on_demand=1,
            ebs_volume_type=EbsVolumeType.GENERAL_PURPOSE_SSD,
            ebs_volume_count=1,
            ebs_volume_size=100,
            instance_profile_arn=config.instance_profile_arn,
        )

    runtime = RuntimeEngine.PHOTON if config.runtime_engine == "PHOTON" else RuntimeEngine.STANDARD

    log(f"Creating cluster '{config.name}'...")

    response = client.clusters.create(
        cluster_name=config.name,
        spark_version=config.spark_version,
        node_type_id=node_type,
        driver_node_type_id=node_type,
        num_workers=0,
        data_security_mode=DataSecurityMode.SINGLE_USER,
        single_user_name=user_email,
        runtime_engine=runtime,
        autotermination_minutes=config.autotermination_minutes,
        spark_conf=spark_conf,
        custom_tags=custom_tags,
        aws_attributes=aws_attributes,
    )

    if not response.cluster_id:
        raise RuntimeError("Failed to create cluster - no cluster ID returned")

    log(f"  Created: {response.cluster_id}")
    return response.cluster_id


def start_cluster(client: WorkspaceClient, cluster_id: str) -> None:
    """Start a terminated cluster."""
    log(f"  Starting cluster {cluster_id}...")
    client.clusters.start(cluster_id)


def wait_for_cluster_running(
    client: WorkspaceClient,
    cluster_id: str,
    timeout_seconds: int = 600,
) -> None:
    """Wait for a cluster to reach RUNNING state.

    Args:
        client: Databricks workspace client.
        cluster_id: ID of the cluster to wait for.
        timeout_seconds: Maximum time to wait.

    Raises:
        RuntimeError: If cluster enters an error state.
        TimeoutError: If timeout is reached.
    """
    log("Waiting for cluster to start...")

    def check_state() -> tuple[bool, State | None]:
        cluster = client.clusters.get(cluster_id)
        state = cluster.state
        log(f"  State: {state}")

        if state == State.RUNNING:
            return True, state
        if state in (State.TERMINATED, State.ERROR, State.UNKNOWN):
            msg = cluster.state_message or "Unknown error"
            raise RuntimeError(f"Cluster entered {state} state: {msg}")
        return False, state

    poll_until(check_state, timeout_seconds=timeout_seconds, description="cluster to start")
    log()
    log("[green]Cluster is running.[/green]")


def get_or_create_cluster(
    client: WorkspaceClient,
    config: ClusterConfig,
    user_email: str,
) -> str:
    """Get an existing cluster or create a new one.

    Args:
        client: Databricks workspace client.
        config: Cluster configuration.
        user_email: Email of the user who will own the cluster.

    Returns:
        The cluster ID.
    """
    # Ensure the instance profile is registered before creating/starting a cluster
    if config.instance_profile_arn and config.cloud_provider != "azure":
        ensure_instance_profile_registered(client, config.instance_profile_arn)

    log(f"Looking for existing cluster \"{config.name}\"...")

    info = find_cluster(client, config.name)

    if info:
        log(f"  Found: {info.cluster_id} (state: {info.state})")

        if info.state == State.TERMINATED:
            start_cluster(client, info.cluster_id)
        elif info.state == State.RUNNING:
            log("  Cluster is already running.")
        # For other states (PENDING, RESTARTING, etc.), we'll wait below
        return info.cluster_id

    log("  Not found - creating new cluster...")
    return create_cluster(client, config, user_email)


# ---------------------------------------------------------------------------
# Per-user cluster helpers
# ---------------------------------------------------------------------------

_USER_CLUSTER_PREFIX = "lab-"


@dataclass
class UserClusterInfo:
    """Summary of a per-user cluster."""

    cluster_id: str
    cluster_name: str
    state: State
    assigned_user: str


def create_user_cluster(
    client: WorkspaceClient,
    config: ClusterConfig,
    user_email: str,
) -> str:
    """Create (or reuse) a per-user cluster named ``lab-<prefix>``.

    Uses :func:`get_or_create_cluster` under the hood with a copy of
    *config* whose name is set to the per-user cluster name.

    Args:
        client: Databricks workspace client.
        config: Base cluster configuration (name will be overridden).
        user_email: Email of the user who will own the cluster.

    Returns:
        The cluster ID.
    """
    from dataclasses import replace

    name = cluster_name_for_user(user_email)
    user_config = replace(config, name=name)
    return get_or_create_cluster(client, user_config, user_email)


def delete_cluster(client: WorkspaceClient, cluster_id: str) -> None:
    """Permanently delete a cluster."""
    log(f"  Deleting cluster {cluster_id}...")
    client.clusters.permanent_delete(cluster_id)
    log("    Done.")


def find_user_clusters(client: WorkspaceClient) -> list[UserClusterInfo]:
    """Find all clusters whose name starts with ``lab-``.

    Returns:
        List of :class:`UserClusterInfo` for matching clusters.
    """
    results: list[UserClusterInfo] = []
    for c in client.clusters.list():
        if (
            c.cluster_name
            and c.cluster_name.startswith(_USER_CLUSTER_PREFIX)
            and c.cluster_id
            and c.state
        ):
            results.append(
                UserClusterInfo(
                    cluster_id=c.cluster_id,
                    cluster_name=c.cluster_name,
                    state=c.state,
                    assigned_user=c.single_user_name or "",
                )
            )
    return results
