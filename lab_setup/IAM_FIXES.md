# IAM Configuration Investigation & Fixes

## Action Required: Fix Workspace Cross-Account Role

The Databricks workspace (AWS account `975049952699`, region `us-west-2`) cannot launch clusters because the **cross-account credential** is set to a placeholder value `dummy-arn` instead of a real IAM role ARN.

### What needs to happen

1. **Create a cross-account IAM role** in AWS account `975049952699` with:
   - A trust policy allowing Databricks' AWS account (`arn:aws:iam::414351767826:root`) to assume it
   - Permissions for EC2 (RunInstances, TerminateInstances, DescribeInstances), EBS volume management, VPC/security group access, and STS AssumeRole for Spot requests
   - See [Databricks: Create a cross-account IAM role](https://docs.databricks.com/en/administration-guide/account-settings-e2/credentials.html) for the full policy template

2. **Update the workspace credential** via one of:
   - **Databricks Account Console** → Cloud Resources → Credential configurations → update the cross-account role ARN
   - **Databricks Account API** → `PATCH /api/2.0/accounts/{account_id}/credentials/{credentials_id}` with the new role ARN

### How to verify the fix

```bash
databricks --profile oneblink clusters create --json '{
  "cluster_name": "iam-test",
  "spark_version": "17.3.x-cpu-ml-scala2.13",
  "node_type_id": "m5.xlarge",
  "num_workers": 0,
  "autotermination_minutes": 10,
  "data_security_mode": "SINGLE_USER",
  "aws_attributes": {
    "ebs_volume_type": "GENERAL_PURPOSE_SSD",
    "ebs_volume_count": 1,
    "ebs_volume_size": 32
  }
}'
```

If the cluster reaches `RUNNING` state, the cross-account role is working.

---

## Problem

Cluster creation failed immediately — the cluster would enter `PENDING` then `TERMINATED`:

```
Error: Cluster entered State.TERMINATED state: Attempt to launch cluster with invalid arguments.
databricks_error_message: The VM launch request to AWS failed, please check your configuration.
ValidationError: 1 validation error detected: Value 'dummy-arn' at 'roleArn' failed to satisfy
constraint: Member must have length greater than or equal to 20
(Service: AWSSecurityTokenService; Status Code: 400; Error Code: ValidationError)
```

## Investigation

### Step 1: Retrieved full error from cluster events

```bash
databricks --profile oneblink clusters events 0206-000614-8gzj5z4g --order DESC
```

The event log revealed `ADD_NODES_FAILED` with:
- `aws_api_error_code`: `ValidationError`
- `aws_error_message`: `Value 'dummy-arn' at 'roleArn' failed to satisfy constraint`

Key finding: The `roleArn` was literally the string `dummy-arn`. An STS AssumeRole call was failing because this isn't a real ARN.

### Step 2: Checked cluster configuration

```bash
databricks --profile oneblink clusters get 0206-000614-8gzj5z4g
```

Findings:
- `instance_profile_arn`: **NOT SET** — no instance profile attached to the cluster
- `availability`: `SPOT_WITH_FALLBACK` with `first_on_demand: 0` (all Spot)
- `zone_id`: `us-west-2c`
- `node_type_id`: `m5.xlarge`

### Step 3: Checked Databricks instance profile registry

```bash
databricks --profile oneblink instance-profiles list
```

Result: **Empty** — no instance profiles were registered in the workspace at all.

### Step 4: Found existing AWS instance profile

```bash
AWS_PROFILE=oneblink aws iam list-instance-profiles \
  --query 'InstanceProfiles[*].{Name:InstanceProfileName,Arn:Arn}' --output json
```

Found one profile: `workshop-node-1-Profile-5XrqT7CtJW5W`

```
Profile ARN: arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W
Role Name:   workshop-node-1-Role-Mr7yatmC2Kla
Role ARN:    arn:aws:iam::975049952699:role/workshop-node-1-Role-Mr7yatmC2Kla
```

### Step 5: Inspected the role's trust policy

```bash
AWS_PROFILE=oneblink aws iam get-role --role-name workshop-node-1-Role-Mr7yatmC2Kla \
  --query 'Role.AssumeRolePolicyDocument'
```

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ec2.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

Trust policy allows `ec2.amazonaws.com` to assume the role — correct for Databricks cluster nodes.

### Step 6: Inspected the role's permissions

```bash
AWS_PROFILE=oneblink aws iam list-attached-role-policies --role-name workshop-node-1-Role-Mr7yatmC2Kla
# Result: no managed policies attached

AWS_PROFILE=oneblink aws iam get-role-policy --role-name workshop-node-1-Role-Mr7yatmC2Kla \
  --policy-name WorkshopScopedAccess
```

Inline policy `WorkshopScopedAccess` grants:
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` on Anthropic/Amazon foundation models
- `bedrock-agentcore:*`
- ECR access for `bedrock-agentcore-*` repos
- CodeBuild access for `bedrock-agentcore-*` projects
- S3 access for `bedrock-agentcore-*` buckets
- IAM role creation for `AmazonBedrockAgentCoreSDK*`
- CloudWatch Logs for CodeBuild and bedrock-agentcore
- `sts:GetCallerIdentity`

### Step 7: Registered instance profile and retested

Registered the profile in Databricks and added it to the cluster's `aws_attributes`. Created a new cluster — **same `dummy-arn` error**.

Also tried switching from `SPOT_WITH_FALLBACK` to `ON_DEMAND` — **same error**.

### Step 8: Identified true root cause

The `dummy-arn` is **not** the instance profile. It's the **workspace-level cross-account IAM role** that the Databricks control plane uses to call AWS APIs (EC2 RunInstances, STS AssumeRole for Spot, etc.). This role is configured at the Databricks **account level** when the workspace is provisioned.

The error `(Spot)` suffix in the message indicates Databricks is trying to call `sts:AssumeRole` with `dummy-arn` to request Spot instances — this happens before the instance profile even matters.

## Root Cause

The Databricks workspace's **cross-account credential** has a placeholder `dummy-arn` instead of a real IAM role ARN. This is the role that Databricks' control plane assumes to make AWS API calls (launch EC2 instances, manage EBS volumes, etc.) on behalf of the workspace.

This is a workspace infrastructure configuration issue set at provisioning time — it cannot be fixed from the Databricks CLI or per-cluster settings.

## Fixes Applied

### Fix 1: Registered instance profile in Databricks (partial — necessary but not sufficient)

```bash
databricks --profile oneblink instance-profiles add \
  "arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W" \
  --iam-role-arn "arn:aws:iam::975049952699:role/workshop-node-1-Role-Mr7yatmC2Kla" \
  --skip-validation
```

### Fix 2: Added INSTANCE_PROFILE_ARN to .env and cluster creation code

Added to `lab_setup/.env`:

```env
INSTANCE_PROFILE_ARN="arn:aws:iam::975049952699:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W"
```

Updated `config.py` to read `INSTANCE_PROFILE_ARN` from environment.
Updated `cluster.py` to pass `instance_profile_arn` in `AwsAttributes`.

### Fix 3: Deleted stale clusters

```bash
databricks --profile oneblink clusters permanent-delete 0206-000614-8gzj5z4g  # Small Spark 4.0
databricks --profile oneblink clusters permanent-delete 0206-035735-tde9oc28  # Serverless
databricks --profile oneblink clusters permanent-delete 0206-040712-kgsqo6c0  # retry (also failed)
```

## Still Blocked: Workspace Cross-Account Role

The workspace credential (`dummy-arn`) must be fixed at the Databricks account level. See the **Action Required** section at the top of this document for the fix.
