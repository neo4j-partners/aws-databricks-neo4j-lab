"""Cluster management for Databricks setup.

Handles cluster creation, starting, and waiting for ready state.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import (
    AwsAttributes,
    AwsAvailability,
    DataSecurityMode,
    EbsVolumeType,
    RuntimeEngine,
    State,
)
from rich.console import Console

from .config import ClusterConfig
from .models import ClusterInfo
from .utils import poll_until

console = Console()


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
        console.print(f"  Instance profile already registered: {instance_profile_arn}")
        return

    console.print(f"  Registering instance profile: {instance_profile_arn}")
    client.instance_profiles.add(
        instance_profile_arn=instance_profile_arn,
        iam_role_arn=iam_role_arn,
        skip_validation=True,
    )
    console.print("  Registered successfully.")


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

    console.print(f"Creating cluster '{config.name}'...")

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

    console.print(f"  Created: {response.cluster_id}")
    return response.cluster_id


def start_cluster(client: WorkspaceClient, cluster_id: str) -> None:
    """Start a terminated cluster."""
    console.print(f"  Starting cluster {cluster_id}...")
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
    console.print("Waiting for cluster to start...")

    def check_state() -> tuple[bool, State | None]:
        cluster = client.clusters.get(cluster_id)
        state = cluster.state
        console.print(f"  State: {state}")

        if state == State.RUNNING:
            return True, state
        if state in (State.TERMINATED, State.ERROR, State.UNKNOWN):
            msg = cluster.state_message or "Unknown error"
            raise RuntimeError(f"Cluster entered {state} state: {msg}")
        return False, state

    poll_until(check_state, timeout_seconds=timeout_seconds, description="cluster to start")
    console.print()
    console.print("[green]Cluster is running.[/green]")


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

    console.print(f"Looking for existing cluster \"{config.name}\"...")

    info = find_cluster(client, config.name)

    if info:
        console.print(f"  Found: {info.cluster_id} (state: {info.state})")

        if info.state == State.TERMINATED:
            start_cluster(client, info.cluster_id)
        elif info.state == State.RUNNING:
            console.print("  Cluster is already running.")
        # For other states (PENDING, RESTARTING, etc.), we'll wait below
        return info.cluster_id

    console.print("  Not found - creating new cluster...")
    return create_cluster(client, config, user_email)
