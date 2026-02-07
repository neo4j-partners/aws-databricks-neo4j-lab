# Databricks Workspace Setup Guide

This guide walks through setting up a Databricks workspace with classic compute on AWS, including all required IAM roles, S3 storage, and instance profiles.

## Prerequisites

| Resource | Value |
|----------|-------|
| AWS Account | `975049952699` |
| Databricks Account ID | `efc239ab-17d3-4ac0-a427-f85b68acb5fd` |
| Databricks CLI Account Profile | `account-admin` |
| Region | `us-east-1` |

## Step 1: Create the Cross-Account IAM Role

Create a cross-account IAM role (`databricks-cross-account-role`) in your AWS account. This role allows the Databricks control plane (account `414351767826`) to launch EC2 instances, manage EBS volumes, and make other AWS API calls on behalf of the workspace.

**Trust policy** — allows Databricks to assume the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::414351767826:root" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "sts:ExternalId": "efc239ab-17d3-4ac0-a427-f85b68acb5fd"
      }
    }
  }]
}
```

**Permissions policy** — must include the full set of EC2, VPC/networking, and IAM permissions. The required actions include:

- **EC2 compute**: `RunInstances`, `TerminateInstances`, `DescribeInstances`, `DescribeSpotPriceHistory`, etc.
- **EBS volumes**: `CreateVolume`, `DeleteVolume`, `AttachVolume`, `DetachVolume`, `DescribeVolumes`
- **VPC/networking** (required for Databricks-managed VPC):
  - `ec2:CreateVpc`, `ec2:DeleteVpc`, `ec2:ModifyVpcAttribute`
  - `ec2:CreateSubnet`, `ec2:DeleteSubnet`
  - `ec2:CreateInternetGateway`, `ec2:AttachInternetGateway`, `ec2:DetachInternetGateway`
  - `ec2:CreateNatGateway`, `ec2:DeleteNatGateway`
  - `ec2:CreateRouteTable`, `ec2:DisassociateRouteTable`, `ec2:CreateRoute`, `ec2:DeleteRoute`
  - `ec2:AllocateAddress`, `ec2:ReleaseAddress`
  - `ec2:CreateSecurityGroup`, `ec2:DeleteVpcEndpoints`
  - `ec2:AssociateDhcpOptions`, `ec2:AssociateRouteTable`
  - `ec2:CreatePlacementGroup`
- **IAM**: `iam:PassRole` on any instance profile roles used by clusters (see Step 5)
- **STS**: `sts:AssumeRole` for Spot instance requests

> Databricks validates the credential at workspace creation time and will reject it if VPC/networking permissions are missing. The full policy is in `fix_workspace.sh`. See also [Databricks: Create a cross-account IAM role](https://docs.databricks.com/en/administration-guide/account-settings-e2/credentials.html) for the canonical policy template.

Register the role as a **Credential Configuration** in the Databricks Account Console:

```bash
databricks --profile account-admin account credentials create --json '{
  "credentials_name": "DatabricksCrossIAMRole",
  "aws_credentials": {
    "sts_role": {
      "role_arn": "arn:aws:iam::975049952699:role/databricks-cross-account-role"
    }
  }
}'
```

Record the returned `credentials_id` (e.g., `c5a690dd-139c-4b63-a016-b1ae7521d3e2`).

## Step 2: Create the S3 Root Storage Bucket

Create an S3 bucket for workspace root storage:

```bash
AWS_PROFILE=oneblink aws s3api create-bucket \
  --bucket databricks-workspace-root-975049952699 \
  --region us-east-1
```

Apply a bucket policy that:

- Grants the Databricks production account (`414351767826`) read/write/list/delete access
- Conditions access on `aws:PrincipalTag/DatabricksAccountId` matching your account ID
- Denies DBFS access to the `unity-catalog/` prefix (separation of concerns)

## Step 3: Create the Storage IAM Role

Create IAM role `databricks-storage-role` with:

**Trust policy** — allows the Unity Catalog master role and self-assumption:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL"
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "sts:ExternalId": "efc239ab-17d3-4ac0-a427-f85b68acb5fd"
      }
    }
  }, {
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::975049952699:role/databricks-storage-role"
    },
    "Action": "sts:AssumeRole"
  }]
}
```

**Permissions policy** (`DatabricksStorageAccess`):

- S3 get/put/delete/list on the root bucket (`databricks-workspace-root-975049952699`)
- `sts:AssumeRole` on itself

Register the bucket as a **Storage Configuration**:

```bash
databricks --profile account-admin account storage create --json '{
  "storage_configuration_name": "databricks-root-storage",
  "root_bucket_info": {
    "bucket_name": "databricks-workspace-root-975049952699"
  }
}'
```

Record the returned `storage_configuration_id` (e.g., `266fa5e2-0c06-4d9b-bf96-e15432e68110`).

## Step 4: Create the Workspace

Create a new workspace with classic compute using the credential and storage configurations from the previous steps:

```bash
databricks --profile account-admin account workspaces create --json '{
  "workspace_name": "workshop-classic",
  "aws_region": "us-east-1",
  "credentials_id": "c5a690dd-139c-4b63-a016-b1ae7521d3e2",
  "storage_configuration_id": "266fa5e2-0c06-4d9b-bf96-e15432e68110"
}'
```

Wait for the workspace to reach `RUNNING` state (can take several minutes):

```bash
databricks --profile account-admin account workspaces get <WORKSPACE_ID>
```

Once the workspace is running, log in to the workspace URL and generate a Personal Access Token under **User Settings → Developer → Access Tokens**.

Update `~/.databrickscfg`:

```ini
[oneblink]
host  = https://<new-workspace-url>/
token = <new-pat>
```

## Step 5: Register the Instance Profile

The instance profile gives cluster nodes access to AWS services (Bedrock, S3, etc.). The existing profile is:

| Resource | Value |
|----------|-------|
| Instance Profile ARN | `arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W` |
| Backing Role ARN | `arn:aws:iam::975049952699:role/workshop-node-1-Role-Mr7yatmC2Kla` |

The backing role's trust policy allows `ec2.amazonaws.com` to assume it (correct for Databricks nodes). Its inline policy (`WorkshopScopedAccess`) grants:

- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` on Anthropic/Amazon foundation models
- `bedrock-agentcore:*`
- ECR, CodeBuild, S3, CloudWatch Logs access for bedrock-agentcore resources
- `sts:GetCallerIdentity`

### Register the profile and grant PassRole

Register the instance profile in Databricks:

```bash
databricks --profile oneblink instance-profiles add \
  "arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W" \
  --iam-role-arn "arn:aws:iam::975049952699:role/workshop-node-1-Role-Mr7yatmC2Kla" \
  --skip-validation
```

Add `iam:PassRole` to the cross-account role so Databricks can attach the instance profile to EC2 instances:

```json
{
  "Sid": "PassInstanceProfileRole",
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::975049952699:role/workshop-node-1-Role-Mr7yatmC2Kla"
}
```

Add the instance profile ARN to `lab_setup/.env`:

```env
INSTANCE_PROFILE_ARN="arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W"
```

## Step 6: Test Cluster Creation

Create a test cluster to verify everything is working:

```bash
databricks --profile oneblink clusters create --json '{
  "cluster_name": "iam-test",
  "spark_version": "17.3.x-cpu-ml-scala2.13",
  "node_type_id": "m5.xlarge",
  "num_workers": 0,
  "autotermination_minutes": 10,
  "data_security_mode": "SINGLE_USER",
  "aws_attributes": {
    "availability": "ON_DEMAND",
    "first_on_demand": 1,
    "instance_profile_arn": "arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W",
    "ebs_volume_type": "GENERAL_PURPOSE_SSD",
    "ebs_volume_count": 1,
    "ebs_volume_size": 32
  }
}'
```

If the cluster reaches `RUNNING` state, the workspace is fully operational.

> Use `ON_DEMAND` availability with `first_on_demand: 1` for workshop environments. Spot instances (`SPOT_WITH_FALLBACK` with `first_on_demand: 0`) are unreliable — AWS can reclaim them at any time during a session.

## Configuration Reference

| Resource | Value |
|----------|-------|
| AWS Account | `975049952699` |
| Databricks Account ID | `efc239ab-17d3-4ac0-a427-f85b68acb5fd` |
| Region | `us-east-1` |
| S3 Root Bucket | `databricks-workspace-root-975049952699` |
| Cross-Account Role | `arn:aws:iam::975049952699:role/databricks-cross-account-role` |
| Storage Role | `arn:aws:iam::975049952699:role/databricks-storage-role` |
| Instance Profile | `arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W` |
| Instance Profile Role | `arn:aws:iam::975049952699:role/workshop-node-1-Role-Mr7yatmC2Kla` |
| Credential Config ID | `c5a690dd-139c-4b63-a016-b1ae7521d3e2` |
| Storage Config ID | `266fa5e2-0c06-4d9b-bf96-e15432e68110` |

## Cleanup (Optional)

Delete an old workspace:

```bash
databricks --profile account-admin account workspaces delete <WORKSPACE_ID>
```

Remove unused credential configurations:

```bash
databricks --profile account-admin account credentials delete <CREDENTIAL_ID>
```
