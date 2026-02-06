# Fix Workspace: Serverless → Classic Compute

## Problem

The Databricks workspace (account `975049952699`, deployment `dbc-3096acf4-2abc`) was provisioned in **serverless compute mode**. Serverless workspaces do not support classic EC2-based clusters — any attempt to create a cluster fails with a `dummy-arn` error because there is no cross-account IAM role associated with the workspace.

```
ValidationError: Value 'dummy-arn' at 'roleArn' failed to satisfy constraint:
Member must have length greater than or equal to 20
(Service: AWSSecurityTokenService; Status Code: 400; Error Code: ValidationError)
```

Updating the credential on a serverless workspace is not supported:

```
MALFORMED_REQUEST: Only workspace name, network connectivity config,
and custom tags update are supported for this workspace.
```

The solution is to create a **new workspace with classic compute enabled**, which requires both a credential configuration (cross-account IAM role) and a storage configuration (S3 root bucket + storage IAM role).

## What Was Done

### Step 1: Cross-Account IAM Role

A cross-account IAM role `databricks-cross-account-role` was created in AWS account `975049952699`. This role allows the Databricks control plane (account `414351767826`) to launch EC2 instances, manage EBS volumes, and make other AWS API calls on behalf of the workspace.

**Important**: The initial version of this role was missing VPC/networking permissions. Databricks validates the credential at workspace creation time and will reject it if permissions are incomplete. The validation checks for:

- `ec2:CreateInternetGateway`, `ec2:CreateVpc`, `ec2:DeleteVpc`
- `ec2:AllocateAddress`, `ec2:ReleaseAddress`
- `ec2:CreateRouteTable`, `ec2:DisassociateRouteTable`
- `ec2:DeleteNatGateway`, `ec2:DeleteVpcEndpoints`
- `ec2:CreateSubnet`, `ec2:DeleteSubnet`, `ec2:CreateRoute`, `ec2:DeleteRoute`
- `ec2:AttachInternetGateway`, `ec2:DetachInternetGateway`
- `ec2:CreateNatGateway`, `ec2:CreatePlacementGroup`, `ec2:CreateSecurityGroup`
- `ec2:AssociateDhcpOptions`, `ec2:AssociateRouteTable`, `ec2:ModifyVpcAttribute`

These are required because Databricks creates and manages a VPC in your account for the workspace (unless you provide a customer-managed VPC). The full permissions policy is in `fix_workspace.sh`.

This role was registered as a **Credential Configuration** in the Databricks Account Console:

| Name | Credential ID | Role ARN |
|------|---------------|----------|
| DatabricksCrossIAMRole | `c5a690dd-139c-4b63-a016-b1ae7521d3e2` | `arn:aws:iam::975049952699:role/databricks-cross-account-role` |

### Step 2: S3 Root Storage Bucket

Created S3 bucket `databricks-workspace-root-975049952699` in `us-east-1` with a bucket policy that:

- Grants Databricks production account (`414351767826`) read/write/list/delete access
- Conditions access on `aws:PrincipalTag/DatabricksAccountId` matching our account ID
- Denies DBFS access to the `unity-catalog/` prefix (separation of concerns)

### Step 3: Storage IAM Role

Created IAM role `databricks-storage-role` with:

- **Trust policy**: Allows the Unity Catalog master role (`arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL`) and itself to assume the role, with external ID set to the Databricks account ID
- **Permissions policy** (`DatabricksStorageAccess`): Grants S3 get/put/delete/list on the root bucket and `sts:AssumeRole` on itself

### Step 4: Storage Configuration

Registered the S3 bucket as a **Storage Configuration** in the Databricks Account Console:

| Name | Storage Config ID | Bucket |
|------|-------------------|--------|
| databricks-root-storage | `266fa5e2-0c06-4d9b-bf96-e15432e68110` | `databricks-workspace-root-975049952699` |

## Configuration Summary

| Resource | Value |
|----------|-------|
| AWS Account | `975049952699` |
| Databricks Account ID | `efc239ab-17d3-4ac0-a427-f85b68acb5fd` |
| Databricks CLI Account Profile | `account-admin` |
| Region | `us-east-1` |
| S3 Bucket | `databricks-workspace-root-975049952699` |
| Cross-Account Role | `arn:aws:iam::975049952699:role/databricks-cross-account-role` |
| Storage Role | `arn:aws:iam::975049952699:role/databricks-storage-role` |
| Credential Config ID | `c5a690dd-139c-4b63-a016-b1ae7521d3e2` |
| Storage Config ID | `266fa5e2-0c06-4d9b-bf96-e15432e68110` |

## Pitfall: Cross-Account Role Missing VPC Permissions

When first attempting to create the workspace, Databricks rejected the credential with:

```
MALFORMED_REQUEST: Failed credentials validation checks: Create Internet Gateway,
Create VPC, Delete VPC, Allocate Address, Release Address, Delete Nat Gateway,
Delete Vpc Endpoints, Create Route Table, Disassociate Route Table
```

The original role policy (created externally) only had EC2 instance and volume permissions — it was missing the full set of VPC/networking actions that Databricks needs to provision a managed VPC. The fix was to update the inline policy with the complete Databricks-managed VPC permission set. See `fix_workspace.sh` for the full policy.

## Next Steps

### 1. Create a New Classic Workspace

Use the Databricks Account API to create a new workspace with classic compute:

```bash
databricks --profile account-admin account workspaces create --json '{
  "workspace_name": "workshop-classic",
  "aws_region": "us-east-1",
  "credentials_id": "c5a690dd-139c-4b63-a016-b1ae7521d3e2",
  "storage_configuration_id": "266fa5e2-0c06-4d9b-bf96-e15432e68110"
}'
```

Wait for the workspace status to reach `RUNNING` (can take several minutes):

```bash
databricks --profile account-admin account workspaces get <WORKSPACE_ID>
```

### 2. Generate a PAT for the New Workspace

Once the workspace is running, log in to the new workspace URL and generate a Personal Access Token under User Settings → Developer → Access Tokens.

Update `~/.databrickscfg`:

```ini
[oneblink]
host  = https://<new-workspace-url>/
token = <new-pat>
```

### 3. Register the Instance Profile

Register the existing instance profile so cluster nodes can access AWS services (Bedrock, S3, etc.):

```bash
databricks --profile oneblink instance-profiles add \
  "arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W" \
  --iam-role-arn "arn:aws:iam::975049952699:role/workshop-node-1-Role-Mr7yatmC2Kla" \
  --skip-validation
```

### 4. Test Cluster Creation

```bash
databricks --profile oneblink clusters create --json '{
  "cluster_name": "iam-test",
  "spark_version": "17.3.x-cpu-ml-scala2.13",
  "node_type_id": "m5.xlarge",
  "num_workers": 0,
  "autotermination_minutes": 10,
  "data_security_mode": "SINGLE_USER",
  "aws_attributes": {
    "instance_profile_arn": "arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W",
    "ebs_volume_type": "GENERAL_PURPOSE_SSD",
    "ebs_volume_count": 1,
    "ebs_volume_size": 32
  }
}'
```

If the cluster reaches `RUNNING` state, the workspace is fully operational.

### 5. (Optional) Delete the Old Serverless Workspace

Once the new workspace is verified, the old serverless workspace can be removed:

```bash
databricks --profile account-admin account workspaces delete 7474658539773755
```

### 6. (Optional) Clean Up Unused Credentials

Remove credential configurations that are no longer needed:

```bash
databricks --profile account-admin account credentials delete <CREDENTIAL_ID>
```
