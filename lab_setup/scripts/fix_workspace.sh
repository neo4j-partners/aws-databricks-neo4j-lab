#!/usr/bin/env bash
#
# fix_workspace.sh — Provision a Databricks classic-compute workspace on AWS
#
# This script automates the creation of all AWS and Databricks resources needed
# to run a Databricks workspace with classic (EC2-based) compute. Serverless
# workspaces do not support classic clusters, so a new workspace must be
# provisioned with a cross-account IAM role and an S3 root storage bucket.
#
# Prerequisites:
#   - AWS CLI configured with a profile that has IAM and S3 permissions
#   - Databricks CLI configured with an account-level profile (OAuth login)
#   - The cross-account IAM role for Databricks must already exist (or this
#     script will create one)
#
# Usage:
#   ./fix_workspace.sh
#
# Environment variables (override defaults):
#   AWS_PROFILE_NAME          - AWS CLI profile (default: oneblink)
#   DATABRICKS_ACCOUNT_PROFILE - Databricks account CLI profile (default: account-admin)
#   DATABRICKS_ACCOUNT_ID     - Your Databricks account ID
#   AWS_ACCOUNT_ID            - Your AWS account ID
#   AWS_REGION                - Region for bucket and workspace (default: us-east-1)
#   WORKSPACE_NAME            - Name for the new workspace (default: workshop-classic)
#   CROSS_ACCOUNT_ROLE_NAME   - Name of the cross-account IAM role for compute
#   INSTANCE_PROFILE_ARN      - Instance profile ARN to register for cluster nodes
#   INSTANCE_PROFILE_ROLE_ARN - IAM role ARN backing the instance profile
#
set -euo pipefail

###############################################################################
# Configuration — edit these or set as environment variables before running
###############################################################################

AWS_PROFILE_NAME="${AWS_PROFILE_NAME:-oneblink}"
DATABRICKS_ACCOUNT_PROFILE="${DATABRICKS_ACCOUNT_PROFILE:-account-admin}"
DATABRICKS_ACCOUNT_ID="${DATABRICKS_ACCOUNT_ID:-efc239ab-17d3-4ac0-a427-f85b68acb5fd}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-975049952699}"
AWS_REGION="${AWS_REGION:-us-east-1}"
WORKSPACE_NAME="${WORKSPACE_NAME:-workshop-classic}"

# Derived names — can be overridden
BUCKET_NAME="${BUCKET_NAME:-databricks-workspace-root-${AWS_ACCOUNT_ID}}"
CROSS_ACCOUNT_ROLE_NAME="${CROSS_ACCOUNT_ROLE_NAME:-databricks-cross-account-role}"
STORAGE_ROLE_NAME="${STORAGE_ROLE_NAME:-databricks-storage-role}"
STORAGE_CONFIG_NAME="${STORAGE_CONFIG_NAME:-databricks-root-storage}"

# Instance profile for cluster nodes (optional — registered after workspace creation)
INSTANCE_PROFILE_ARN="${INSTANCE_PROFILE_ARN:-arn:aws:iam::${AWS_ACCOUNT_ID}:instance-profile/workshop-node-1-Profile-5XrqT7CtJW5W}"
INSTANCE_PROFILE_ROLE_ARN="${INSTANCE_PROFILE_ROLE_ARN:-arn:aws:iam::${AWS_ACCOUNT_ID}:role/workshop-node-1-Role-Mr7yatmC2Kla}"

# The Databricks production AWS account and Unity Catalog master role.
# These are constants published by Databricks.
DATABRICKS_AWS_ACCOUNT="414351767826"
UC_MASTER_ROLE="arn:aws:iam::${DATABRICKS_AWS_ACCOUNT}:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL"

###############################################################################
# Helper functions
###############################################################################

info()  { echo "==> $*"; }
error() { echo "ERROR: $*" >&2; exit 1; }

# Check that a CLI tool is available
require() {
  command -v "$1" >/dev/null 2>&1 || error "'$1' is required but not found in PATH"
}

###############################################################################
# Preflight checks
###############################################################################

require aws
require databricks
require python3

info "AWS Profile:        ${AWS_PROFILE_NAME}"
info "Databricks Profile: ${DATABRICKS_ACCOUNT_PROFILE}"
info "AWS Account:        ${AWS_ACCOUNT_ID}"
info "Databricks Account: ${DATABRICKS_ACCOUNT_ID}"
info "Region:             ${AWS_REGION}"
info "Bucket:             ${BUCKET_NAME}"
echo ""

# Verify AWS credentials
info "Verifying AWS credentials..."
CALLER_ACCOUNT=$(AWS_PROFILE="${AWS_PROFILE_NAME}" aws sts get-caller-identity \
  --query 'Account' --output text 2>/dev/null) \
  || error "AWS credentials not valid for profile '${AWS_PROFILE_NAME}'"

if [[ "${CALLER_ACCOUNT}" != "${AWS_ACCOUNT_ID}" ]]; then
  error "AWS account mismatch: expected ${AWS_ACCOUNT_ID}, got ${CALLER_ACCOUNT}"
fi

# Verify Databricks account-level auth
info "Verifying Databricks account credentials..."
databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account workspaces list >/dev/null 2>&1 \
  || error "Databricks account CLI not authenticated. Run: databricks auth login --host https://accounts.cloud.databricks.com --account-id ${DATABRICKS_ACCOUNT_ID} --profile ${DATABRICKS_ACCOUNT_PROFILE}"

###############################################################################
# Step 1: Create the cross-account IAM role (if it doesn't already exist)
#
# This role is assumed by Databricks' control plane to make AWS API calls
# (EC2 RunInstances, TerminateInstances, EBS, VPC, STS) on behalf of the
# workspace. It is the "credential configuration" in Databricks terms.
###############################################################################

info "Checking for cross-account IAM role '${CROSS_ACCOUNT_ROLE_NAME}'..."
if AWS_PROFILE="${AWS_PROFILE_NAME}" aws iam get-role --role-name "${CROSS_ACCOUNT_ROLE_NAME}" >/dev/null 2>&1; then
  info "Cross-account role already exists, ensuring permissions are up to date..."
else
  info "Creating cross-account IAM role '${CROSS_ACCOUNT_ROLE_NAME}'..."

  # Trust policy: allows Databricks' AWS account to assume this role
  # using our Databricks account ID as the external ID.
  AWS_PROFILE="${AWS_PROFILE_NAME}" aws iam create-role \
    --role-name "${CROSS_ACCOUNT_ROLE_NAME}" \
    --assume-role-policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${DATABRICKS_AWS_ACCOUNT}:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "${DATABRICKS_ACCOUNT_ID}"
        }
      }
    }
  ]
}
EOF
)" >/dev/null

  info "Cross-account role created."
fi

# Always apply the permissions policy to ensure it has the full set of
# required actions. Databricks validates these at workspace creation time
# and will reject credentials that are missing VPC/networking permissions.
#
# This is the Databricks-managed VPC policy which includes:
#   - EC2 instance lifecycle (RunInstances, TerminateInstances, etc.)
#   - EBS volume management (CreateVolume, AttachVolume, DeleteVolume)
#   - VPC networking (CreateVpc, CreateSubnet, CreateInternetGateway,
#     CreateNatGateway, CreateRouteTable, AllocateAddress, etc.)
#   - Fleet and launch template management
#   - Security group management
#   - Spot instance support (including service-linked role for Spot)
#   - iam:PassRole for the instance profile role (required to attach
#     instance profiles to EC2 instances launched by Databricks)
#
# A common pitfall is having only the EC2/EBS actions without the VPC
# actions, which causes credential validation failure with:
#   "Failed credentials validation checks: Create Internet Gateway,
#    Create VPC, Delete VPC, Allocate Address, ..."
info "Applying cross-account permissions policy..."
AWS_PROFILE="${AWS_PROFILE_NAME}" aws iam put-role-policy \
  --role-name "${CROSS_ACCOUNT_ROLE_NAME}" \
  --policy-name DatabricksCrossAccountPolicy \
  --policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2andVPCManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:AllocateAddress",
        "ec2:AssociateDhcpOptions",
        "ec2:AssociateIamInstanceProfile",
        "ec2:AssociateRouteTable",
        "ec2:AssignPrivateIpAddresses",
        "ec2:AttachInternetGateway",
        "ec2:AttachVolume",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:CancelSpotInstanceRequests",
        "ec2:CreateDhcpOptions",
        "ec2:CreateFleet",
        "ec2:CreateInternetGateway",
        "ec2:CreateLaunchTemplate",
        "ec2:CreateLaunchTemplateVersion",
        "ec2:CreateNatGateway",
        "ec2:CreatePlacementGroup",
        "ec2:CreateRoute",
        "ec2:CreateRouteTable",
        "ec2:CreateSecurityGroup",
        "ec2:CreateSubnet",
        "ec2:CreateTags",
        "ec2:CreateVolume",
        "ec2:CreateVpc",
        "ec2:CreateVpcEndpoint",
        "ec2:DeleteDhcpOptions",
        "ec2:DeleteFleets",
        "ec2:DeleteInternetGateway",
        "ec2:DeleteLaunchTemplate",
        "ec2:DeleteLaunchTemplateVersions",
        "ec2:DeleteNatGateway",
        "ec2:DeletePlacementGroup",
        "ec2:DeleteRoute",
        "ec2:DeleteRouteTable",
        "ec2:DeleteSecurityGroup",
        "ec2:DeleteSubnet",
        "ec2:DeleteTags",
        "ec2:DeleteVolume",
        "ec2:DeleteVpc",
        "ec2:DeleteVpcEndpoints",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeFleetHistory",
        "ec2:DescribeFleetInstances",
        "ec2:DescribeFleets",
        "ec2:DescribeIamInstanceProfileAssociations",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeInstances",
        "ec2:DescribeInternetGateways",
        "ec2:DescribeLaunchTemplates",
        "ec2:DescribeLaunchTemplateVersions",
        "ec2:DescribeNatGateways",
        "ec2:DescribeNetworkAcls",
        "ec2:DescribePlacementGroups",
        "ec2:DescribePrefixLists",
        "ec2:DescribeReservedInstancesOfferings",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSpotInstanceRequests",
        "ec2:DescribeSpotPriceHistory",
        "ec2:DescribeSubnets",
        "ec2:DescribeVolumes",
        "ec2:DescribeVpcAttribute",
        "ec2:DescribeVpcs",
        "ec2:DetachInternetGateway",
        "ec2:DetachVolume",
        "ec2:DisassociateIamInstanceProfile",
        "ec2:DisassociateRouteTable",
        "ec2:GetLaunchTemplateData",
        "ec2:GetSpotPlacementScores",
        "ec2:ModifyFleet",
        "ec2:ModifyLaunchTemplate",
        "ec2:ModifyVpcAttribute",
        "ec2:ReleaseAddress",
        "ec2:ReplaceIamInstanceProfileAssociation",
        "ec2:RequestSpotInstances",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RunInstances",
        "ec2:TerminateInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SpotServiceLinkedRole",
      "Effect": "Allow",
      "Action": [
        "iam:CreateServiceLinkedRole",
        "iam:PutRolePolicy"
      ],
      "Resource": "arn:aws:iam::*:role/aws-service-role/spot.amazonaws.com/AWSServiceRoleForEC2Spot",
      "Condition": {
        "StringLike": {
          "iam:AWSServiceName": "spot.amazonaws.com"
        }
      }
    },
    {
      "Sid": "PassInstanceProfileRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "${INSTANCE_PROFILE_ROLE_ARN}"
    },
    {
      "Sid": "SelfAssume",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${CROSS_ACCOUNT_ROLE_NAME}"
    }
  ]
}
EOF
)"

info "Cross-account permissions policy applied."

CROSS_ACCOUNT_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${CROSS_ACCOUNT_ROLE_NAME}"

###############################################################################
# Step 2: Create the S3 root storage bucket
#
# This bucket stores workspace data (DBFS root, notebooks, logs, etc.).
# Databricks' production account is granted access via a bucket policy,
# scoped to our Databricks account ID.
###############################################################################

info "Checking for S3 bucket '${BUCKET_NAME}'..."
if AWS_PROFILE="${AWS_PROFILE_NAME}" aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
  info "Bucket already exists, skipping creation."
else
  info "Creating S3 bucket '${BUCKET_NAME}' in ${AWS_REGION}..."

  # us-east-1 does not accept a LocationConstraint (it's the default)
  if [[ "${AWS_REGION}" == "us-east-1" ]]; then
    AWS_PROFILE="${AWS_PROFILE_NAME}" aws s3api create-bucket \
      --bucket "${BUCKET_NAME}" \
      --region "${AWS_REGION}" >/dev/null
  else
    AWS_PROFILE="${AWS_PROFILE_NAME}" aws s3api create-bucket \
      --bucket "${BUCKET_NAME}" \
      --region "${AWS_REGION}" \
      --create-bucket-configuration LocationConstraint="${AWS_REGION}" >/dev/null
  fi

  info "Bucket created."
fi

# Apply the bucket policy. This grants Databricks' AWS account read/write
# access conditioned on our Databricks account ID, and denies DBFS access
# to the unity-catalog/ prefix to enforce separation.
info "Applying bucket policy..."
AWS_PROFILE="${AWS_PROFILE_NAME}" aws s3api put-bucket-policy \
  --bucket "${BUCKET_NAME}" \
  --policy "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Grant Databricks Access",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${DATABRICKS_AWS_ACCOUNT}:root"
      },
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}/*",
        "arn:aws:s3:::${BUCKET_NAME}"
      ],
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/DatabricksAccountId": ["${DATABRICKS_ACCOUNT_ID}"]
        }
      }
    },
    {
      "Sid": "Prevent DBFS from accessing Unity Catalog metastore",
      "Effect": "Deny",
      "Principal": {
        "AWS": "arn:aws:iam::${DATABRICKS_AWS_ACCOUNT}:root"
      },
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}/unity-catalog/*"
      ]
    }
  ]
}
EOF
)"

###############################################################################
# Step 3: Create the storage IAM role
#
# This role is used by Databricks Unity Catalog to access the workspace's
# root S3 bucket. The trust policy allows the Unity Catalog master role
# (in Databricks' account) and the role itself (self-assume) to assume it.
# The external ID is set to our Databricks account ID for security.
###############################################################################

STORAGE_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${STORAGE_ROLE_NAME}"

info "Checking for storage IAM role '${STORAGE_ROLE_NAME}'..."
if AWS_PROFILE="${AWS_PROFILE_NAME}" aws iam get-role --role-name "${STORAGE_ROLE_NAME}" >/dev/null 2>&1; then
  info "Storage role already exists, updating trust policy..."
else
  info "Creating storage IAM role '${STORAGE_ROLE_NAME}'..."

  # Create the role with only the UC master role in the trust policy first,
  # because AWS rejects self-referencing principals on role creation.
  AWS_PROFILE="${AWS_PROFILE_NAME}" aws iam create-role \
    --role-name "${STORAGE_ROLE_NAME}" \
    --assume-role-policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "${UC_MASTER_ROLE}"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "${DATABRICKS_ACCOUNT_ID}"
        }
      }
    }
  ]
}
EOF
)" >/dev/null

  info "Storage role created."
fi

# Update the trust policy to add the self-assume principal.
# AWS requires the role to exist before it can reference itself.
info "Updating trust policy with self-assume..."
AWS_PROFILE="${AWS_PROFILE_NAME}" aws iam update-assume-role-policy \
  --role-name "${STORAGE_ROLE_NAME}" \
  --policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "${UC_MASTER_ROLE}",
          "${STORAGE_ROLE_ARN}"
        ]
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "${DATABRICKS_ACCOUNT_ID}"
        }
      }
    }
  ]
}
EOF
)"

# Attach a permissions policy granting S3 access to the root bucket
# and the ability to self-assume (required by Unity Catalog).
info "Attaching S3 permissions policy to storage role..."
AWS_PROFILE="${AWS_PROFILE_NAME}" aws iam put-role-policy \
  --role-name "${STORAGE_ROLE_NAME}" \
  --policy-name DatabricksStorageAccess \
  --policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}/*",
        "arn:aws:s3:::${BUCKET_NAME}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "${STORAGE_ROLE_ARN}"
    }
  ]
}
EOF
)"

###############################################################################
# Step 4: Register configurations in Databricks Account Console
#
# Create credential and storage configurations that reference the AWS
# resources above. These IDs are then used when creating the workspace.
###############################################################################

# Check if the credential configuration already exists
info "Checking for existing credential configuration..."
CREDENTIALS_ID=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account credentials list -o json 2>/dev/null \
  | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    if c.get('aws_credentials', {}).get('sts_role', {}).get('role_arn') == '${CROSS_ACCOUNT_ROLE_ARN}':
        print(c['credentials_id'])
        break
" 2>/dev/null || true)

if [[ -n "${CREDENTIALS_ID}" ]]; then
  info "Credential configuration already exists: ${CREDENTIALS_ID}"
else
  info "Creating credential configuration..."
  CREDENTIALS_ID=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account credentials create --json "{
    \"credentials_name\": \"${WORKSPACE_NAME}-credential\",
    \"aws_credentials\": {
      \"sts_role\": {
        \"role_arn\": \"${CROSS_ACCOUNT_ROLE_ARN}\"
      }
    }
  }" -o json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['credentials_id'])")
  info "Credential configuration created: ${CREDENTIALS_ID}"
fi

# Check if the storage configuration already exists
info "Checking for existing storage configuration..."
STORAGE_CONFIG_ID=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account storage list -o json 2>/dev/null \
  | python3 -c "
import json, sys
for s in json.load(sys.stdin):
    if s.get('root_bucket_info', {}).get('bucket_name') == '${BUCKET_NAME}':
        print(s['storage_configuration_id'])
        break
" 2>/dev/null || true)

if [[ -n "${STORAGE_CONFIG_ID}" ]]; then
  info "Storage configuration already exists: ${STORAGE_CONFIG_ID}"
else
  info "Creating storage configuration..."
  STORAGE_CONFIG_ID=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account storage create --json "{
    \"storage_configuration_name\": \"${STORAGE_CONFIG_NAME}\",
    \"root_bucket_info\": {
      \"bucket_name\": \"${BUCKET_NAME}\"
    }
  }" -o json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['storage_configuration_id'])")
  info "Storage configuration created: ${STORAGE_CONFIG_ID}"
fi

###############################################################################
# Step 5: Create the classic workspace
#
# This brings everything together — the credential and storage configurations
# are passed to Databricks, which provisions a workspace with classic EC2
# compute enabled.
###############################################################################

# Check if a workspace with this name already exists
info "Checking for existing workspace '${WORKSPACE_NAME}'..."
EXISTING_WS=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account workspaces list -o json 2>/dev/null \
  | python3 -c "
import json, sys
for w in json.load(sys.stdin):
    if w.get('workspace_name') == '${WORKSPACE_NAME}':
        print(w['workspace_id'])
        break
" 2>/dev/null || true)

if [[ -n "${EXISTING_WS}" ]]; then
  info "Workspace '${WORKSPACE_NAME}' already exists (ID: ${EXISTING_WS}), skipping creation."
  WORKSPACE_ID="${EXISTING_WS}"
else
  info "Creating workspace '${WORKSPACE_NAME}'..."
  WORKSPACE_ID=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account workspaces create --json "{
    \"workspace_name\": \"${WORKSPACE_NAME}\",
    \"aws_region\": \"${AWS_REGION}\",
    \"credentials_id\": \"${CREDENTIALS_ID}\",
    \"storage_configuration_id\": \"${STORAGE_CONFIG_ID}\"
  }" -o json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['workspace_id'])")
  info "Workspace creation initiated (ID: ${WORKSPACE_ID})"
fi

# Poll until the workspace is running (or fails)
info "Waiting for workspace to reach RUNNING state..."
for i in $(seq 1 60); do
  STATUS=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account workspaces get "${WORKSPACE_ID}" -o json 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('workspace_status','UNKNOWN'))")

  if [[ "${STATUS}" == "RUNNING" ]]; then
    WORKSPACE_URL=$(databricks --profile "${DATABRICKS_ACCOUNT_PROFILE}" account workspaces get "${WORKSPACE_ID}" -o json 2>/dev/null \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('deployment_name',''))")
    info "Workspace is RUNNING!"
    info "URL: https://${WORKSPACE_URL}.cloud.databricks.com"
    break
  elif [[ "${STATUS}" == "FAILED" || "${STATUS}" == "BANNED" ]]; then
    error "Workspace provisioning failed with status: ${STATUS}"
  fi

  echo "    Status: ${STATUS} (attempt ${i}/60, waiting 15s...)"
  sleep 15
done

if [[ "${STATUS}" != "RUNNING" ]]; then
  error "Timed out waiting for workspace to reach RUNNING state (last status: ${STATUS})"
fi

###############################################################################
# Done — print summary and next steps
###############################################################################

echo ""
echo "============================================================"
echo "  Workspace provisioned successfully!"
echo "============================================================"
echo ""
echo "  Workspace Name: ${WORKSPACE_NAME}"
echo "  Workspace ID:   ${WORKSPACE_ID}"
echo "  Workspace URL:  https://${WORKSPACE_URL}.cloud.databricks.com"
echo "  S3 Bucket:      ${BUCKET_NAME}"
echo "  Region:         ${AWS_REGION}"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Log in to https://${WORKSPACE_URL}.cloud.databricks.com"
echo "  2. Generate a Personal Access Token (Settings → Developer)"
echo "  3. Update ~/.databrickscfg with the new host and token"
echo "  4. Register the instance profile:"
echo ""
echo "     databricks --profile oneblink instance-profiles add \\"
echo "       \"${INSTANCE_PROFILE_ARN}\" \\"
echo "       --iam-role-arn \"${INSTANCE_PROFILE_ROLE_ARN}\" \\"
echo "       --skip-validation"
echo ""
echo "  5. Test cluster creation (see FIX_WORKSPACE.md)"
echo "============================================================"
