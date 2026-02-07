# Databricks Workspace Setup Scripts

This directory contains scripts for provisioning and managing a Databricks workspace on AWS with classic (EC2-based) compute.

## Overview

Serverless-only Databricks workspaces do not support classic clusters. If your workshop requires classic compute (e.g., instance profiles, custom cluster policies), you must provision a workspace backed by a cross-account IAM role and an S3 root storage bucket. The `fix_workspace.sh` script automates the entire process.

## Prerequisites

| Requirement | Details |
|---|---|
| **AWS CLI** | Configured with a profile that has IAM, S3, and STS permissions |
| **Databricks CLI** | v0.200+ with an account-level profile (OAuth or PAT) |
| **Python 3** | Used for JSON parsing in the script |
| **Databricks Account Admin** | You must be an account admin in your Databricks account |
| **AWS Account** | With available VPC and NAT gateway capacity in the target region |

### Authenticate the Databricks CLI (account level)

```bash
databricks auth login \
  --host https://accounts.cloud.databricks.com \
  --account-id <YOUR_DATABRICKS_ACCOUNT_ID> \
  --profile account-admin
```

## Scripts

| Script | Purpose |
|---|---|
| `fix_workspace.sh` | Provisions a classic-compute workspace (IAM roles, S3 bucket, Databricks configs) |
| `setup_databricks_external_location.sh` | Registers an external storage location in Unity Catalog |
| `cleanup_databricks_external_location.sh` | Removes an external storage location |

---

## Running `fix_workspace.sh`

### What It Does

The script automates five steps:

1. **Cross-account IAM role** -- Creates (or updates) a role that Databricks' control plane assumes to launch EC2 instances, manage VPCs, and attach EBS volumes in your AWS account.
2. **S3 root storage bucket** -- Creates a bucket for workspace data (DBFS root, notebooks, logs) and applies a bucket policy granting Databricks access.
3. **Storage IAM role** -- Creates a role for Unity Catalog to access the root bucket, with a trust policy referencing the Databricks UC master role.
4. **Databricks credential & storage configurations** -- Registers the IAM role and S3 bucket in the Databricks Account Console.
5. **Workspace creation** -- Creates the workspace and polls until it reaches `RUNNING` state.

### Environment Variables

Override any default by exporting the variable before running the script:

| Variable | Default | Description |
|---|---|---|
| `AWS_PROFILE_NAME` | `oneblink` | AWS CLI profile name |
| `DATABRICKS_ACCOUNT_PROFILE` | `account-admin` | Databricks CLI account-level profile |
| `DATABRICKS_ACCOUNT_ID` | *(set in script)* | Your Databricks account ID |
| `AWS_ACCOUNT_ID` | *(set in script)* | Your AWS account ID |
| `AWS_REGION` | `us-east-1` | AWS region for bucket and workspace |
| `WORKSPACE_NAME` | `workshop-classic` | Name for the new workspace |
| `BUCKET_NAME` | `databricks-workspace-root-<AWS_ACCOUNT_ID>` | S3 bucket name |
| `CROSS_ACCOUNT_ROLE_NAME` | `databricks-cross-account-role` | Cross-account IAM role name |
| `STORAGE_ROLE_NAME` | `databricks-storage-role` | Storage IAM role name |
| `INSTANCE_PROFILE_ARN` | *(set in script)* | Instance profile ARN for cluster nodes |
| `INSTANCE_PROFILE_ROLE_ARN` | *(set in script)* | IAM role ARN backing the instance profile |

### Quick Start

```bash
# Edit the defaults inside fix_workspace.sh or export overrides:
export AWS_PROFILE_NAME="my-aws-profile"
export DATABRICKS_ACCOUNT_ID="your-databricks-account-id"
export AWS_ACCOUNT_ID="123456789012"
export WORKSPACE_NAME="sandbox_workspace"

# Run the script
./lab_setup/scripts/fix_workspace.sh
```

The script is idempotent -- it checks for existing resources before creating them and can be re-run safely.

### Post-Creation Steps

After the workspace is running:

1. Log in to `https://<deployment-name>.cloud.databricks.com`
2. Generate a Personal Access Token (Settings > Developer)
3. Update `~/.databrickscfg` with the new workspace host and token
4. Register the instance profile:
   ```bash
   databricks --profile <workspace-profile> instance-profiles add \
     "<INSTANCE_PROFILE_ARN>" \
     --iam-role-arn "<INSTANCE_PROFILE_ROLE_ARN>" \
     --skip-validation
   ```

---

## Manual Workspace Creation (Account Console UI)

If you prefer the Databricks Account Console UI instead of the script, follow these steps.

### Step 1: Create the Cross-Account IAM Role

1. In the **AWS IAM Console**, create a new role:
   - Trusted entity: **Another AWS account**
   - Account ID: `414351767826` (Databricks production account)
   - Check **Require external ID** and enter your Databricks account ID
2. Attach an inline policy with EC2, EBS, and VPC permissions (see the full policy in `fix_workspace.sh` lines 166-285).
3. Note the **Role ARN** (e.g., `arn:aws:iam::975049952699:role/databricks-cross-account-role`).

### Step 2: Create the S3 Root Storage Bucket

1. Create an S3 bucket in your target region (e.g., `databricks-workspace-root-975049952699`).
2. Apply a bucket policy granting access to Databricks account `414351767826`, conditioned on your Databricks account ID. Include a deny statement for the `unity-catalog/` prefix.

### Step 3: Create the Storage IAM Role

1. Create an IAM role with a trust policy allowing:
   - The Databricks UC master role (`arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL`)
   - Self-assume (the role itself)
   - External ID set to your Databricks account ID
2. Attach an inline policy granting `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`, and `s3:GetBucketLocation` on the root bucket.

### Step 4: Create the Workspace

1. Go to the [Databricks Account Console](https://accounts.cloud.databricks.com) > **Workspaces** > **Create workspace**.
2. Fill in:
   - **Workspace name**: e.g., `sandbox_workspace`
   - **Region**: e.g., `N. Virginia (us-east-1)`
3. Under **Cloud resources**:
   - **Cloud credentials**: Select or add the cross-account role (e.g., `DatabricksCrossIAMRole`).

### Step 5: Add Cloud Storage

In the **Cloud storage** dropdown, select **Add new cloud storage**:

1. Choose **Set up Manually**.
2. Fill in:
   - **Storage configuration name**: e.g., `sandbox_storage`
   - **Bucket name**: The S3 bucket created in Step 2 (e.g., `databricks-workspace-root-975049952699`)
   - **IAM role ARN**: The storage role ARN from Step 3 (e.g., `arn:aws:iam::975049952699:role/databricks-storage-role`)
3. Click **Add cloud storage**, then **Create workspace**.

Databricks provisions the workspace. This typically completes within 5-10 minutes.

---

## Architecture

```
Databricks Control Plane (414351767826)
        |
        | sts:AssumeRole (ExternalId = Databricks Account ID)
        v
Cross-Account IAM Role (your AWS account)
        |
        | ec2:RunInstances, ec2:CreateVpc, ...
        v
  EC2 Compute Instances
        |
        | iam:PassRole -> Instance Profile Role
        v
   S3 Root Bucket (workspace data, DBFS, logs)
```

Unity Catalog uses a separate trust chain:

```
UC Master Role (414351767826)
        |
        | sts:AssumeRole (ExternalId = Databricks Account ID)
        v
Storage IAM Role (your AWS account)
        |
        | s3:GetObject, s3:PutObject, s3:DeleteObject, s3:ListBucket
        v
   S3 Root Bucket /unity-catalog/ prefix
```

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| Credential validation fails with VPC errors | Cross-account policy missing VPC/networking actions | Use the full policy from `fix_workspace.sh` (includes `CreateVpc`, `CreateSubnet`, `CreateInternetGateway`, etc.) |
| `sts:AssumeRole` denied | SCP blocking cross-account assume or wrong external ID | Verify SCP allowlists `sts:AssumeRole`; check external ID matches your Databricks account ID |
| Workspace stuck in PROVISIONING | AWS resource limits or IAM propagation delay | Wait up to 15 minutes; check AWS Service Quotas for VPC/NAT limits |
| Instance profile not available in cluster UI | Profile not registered with workspace | Run `databricks instance-profiles add` (see Post-Creation Steps) |

## References

- [Create a workspace with manual AWS configurations](https://docs.databricks.com/aws/en/admin/workspace/create-uc-workspace)
- [Create a classic workspace](https://docs.databricks.com/aws/en/admin/workspace/create-workspace)
- [Configure S3 access with an instance profile](https://docs.databricks.com/aws/en/connect/storage/tutorial-s3-instance-profile)
- [Databricks + AWS automated infrastructure setup](https://www.databricks.com/blog/databricks-and-aws-partner-simplify-infrastructure-setup)
