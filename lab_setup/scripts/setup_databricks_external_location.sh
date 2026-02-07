#!/bin/bash
#
# Setup Databricks External Location for Unity Catalog
# Based on: https://docs.databricks.com/aws/en/connect/unity-catalog/cloud-storage/s3/s3-external-location-manual
#
# This script creates:
#   1. IAM role with trust policy for Unity Catalog
#   2. IAM policies for S3 access and file events
#   3. Storage credential in Databricks
#   4. External location in Databricks
#
# Prerequisites:
#   - AWS CLI configured with appropriate permissions (iam:CreateRole, iam:CreatePolicy, iam:AttachRolePolicy)
#   - Databricks CLI configured with a profile that has CREATE STORAGE CREDENTIAL and CREATE EXTERNAL LOCATION privileges
#   - jq installed for JSON parsing
#   - .env file with configuration (copy from .env.example)
#
# Usage:
#   cp .env.example .env  # First time only - edit .env with your values
#   ./setup_databricks_external_location.sh
#

set -e

#------------------------------------------------------------------------------
# Get script directory (for finding .env file)
#------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#------------------------------------------------------------------------------
# Load configuration from .env file
#------------------------------------------------------------------------------
load_env() {
    local env_file="${SCRIPT_DIR}/.env"

    if [ ! -f "$env_file" ]; then
        echo "ERROR: .env file not found at: $env_file"
        echo ""
        echo "Please create a .env file by copying the example:"
        echo "  cp ${SCRIPT_DIR}/.env.example ${SCRIPT_DIR}/.env"
        echo ""
        echo "Then edit .env with your configuration values."
        exit 1
    fi

    # Load .env file (only export valid variable assignments, ignore comments)
    set -a
    # shellcheck source=/dev/null
    source "$env_file"
    set +a
}

# Load environment variables from .env
load_env

#------------------------------------------------------------------------------
# Configuration defaults (can be overridden by .env)
#------------------------------------------------------------------------------

# AWS Configuration
AWS_CLI_PROFILE="${AWS_CLI_PROFILE:-oneblink}"
AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"  # Will be auto-detected if empty

# S3 Bucket Configuration
S3_BUCKET_NAME="${S3_BUCKET_NAME:-}"
S3_PREFIX="${S3_PREFIX:-}"

# IAM Role Configuration
IAM_ROLE_NAME="${IAM_ROLE_NAME:-databricks-unity-catalog-access}"

# Databricks Configuration
DATABRICKS_PROFILE="${DATABRICKS_PROFILE:-oneblink}"
STORAGE_CREDENTIAL_NAME="${STORAGE_CREDENTIAL_NAME:-my-s3-storage-credential}"
EXTERNAL_LOCATION_NAME="${EXTERNAL_LOCATION_NAME:-my-s3-external-location}"

# Optional settings
KMS_KEY_ARN="${KMS_KEY_ARN:-}"
ENABLE_FILE_EVENTS="${ENABLE_FILE_EVENTS:-true}"
READ_ONLY="${READ_ONLY:-false}"

# Unity Catalog Master Role ARN (DO NOT CHANGE unless using GovCloud)
UNITY_CATALOG_MASTER_ROLE="${UNITY_CATALOG_MASTER_ROLE:-arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL}"

#------------------------------------------------------------------------------
# Color output helpers
#------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

#------------------------------------------------------------------------------
# Prerequisite checks
#------------------------------------------------------------------------------
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check required configuration
    if [ -z "$S3_BUCKET_NAME" ] || [ "$S3_BUCKET_NAME" = "your-bucket-name" ]; then
        log_error "S3_BUCKET_NAME is not configured in .env file."
        log_info "Please edit ${SCRIPT_DIR}/.env and set S3_BUCKET_NAME to your bucket name."
        exit 1
    fi

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check Databricks CLI
    if ! command -v databricks &> /dev/null; then
        log_error "Databricks CLI is not installed. Please install it first."
        log_info "Install with: pip install databricks-cli"
        exit 1
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it first."
        log_info "Install with: brew install jq (macOS) or apt-get install jq (Linux)"
        exit 1
    fi

    # Verify AWS credentials
    if ! aws sts get-caller-identity --profile "$AWS_CLI_PROFILE" &> /dev/null; then
        log_error "AWS credentials not configured for profile '$AWS_CLI_PROFILE'."
        log_info "Please run: aws configure --profile $AWS_CLI_PROFILE"
        exit 1
    fi

    # Auto-detect AWS Account ID if not provided
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_CLI_PROFILE" --query Account --output text)
        log_info "Auto-detected AWS Account ID: $AWS_ACCOUNT_ID"
    fi

    # Verify Databricks CLI profile
    if ! databricks auth env --profile "$DATABRICKS_PROFILE" &> /dev/null; then
        log_warn "Databricks profile '$DATABRICKS_PROFILE' may not be configured."
        log_info "Continuing anyway - configure with: databricks configure --profile $DATABRICKS_PROFILE"
    fi

    log_success "Prerequisites check passed"
}

#------------------------------------------------------------------------------
# Validate S3 bucket
#------------------------------------------------------------------------------
validate_s3_bucket() {
    log_info "Validating S3 bucket: $S3_BUCKET_NAME"

    # Check bucket name for dots (not recommended)
    if [[ "$S3_BUCKET_NAME" == *.* ]]; then
        log_warn "Bucket name contains dots. Databricks recommends avoiding dot notation in bucket names."
    fi

    # Verify bucket exists
    if ! aws s3api head-bucket --bucket "$S3_BUCKET_NAME" --profile "$AWS_CLI_PROFILE" 2>/dev/null; then
        log_error "S3 bucket '$S3_BUCKET_NAME' does not exist or is not accessible."
        log_info "Please create the bucket first or check permissions."
        exit 1
    fi

    log_success "S3 bucket validated"
}

#------------------------------------------------------------------------------
# Create IAM role with initial trust policy
#------------------------------------------------------------------------------
create_iam_role() {
    log_info "Creating IAM role: $IAM_ROLE_NAME"

    # Check if role already exists
    if aws iam get-role --role-name "$IAM_ROLE_NAME" --profile "$AWS_CLI_PROFILE" &> /dev/null; then
        log_warn "IAM role '$IAM_ROLE_NAME' already exists. Skipping creation."
        return 0
    fi

    # Create initial trust policy with ONLY UC master role
    # Self-assume will be added when we update with the external ID
    # (Can't reference the role before it exists)
    TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "$UNITY_CATALOG_MASTER_ROLE"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "0000"
                }
            }
        }
    ]
}
EOF
)

    aws iam create-role \
        --role-name "$IAM_ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "IAM role for Databricks Unity Catalog access to S3" \
        --tags Key=Purpose,Value=DatabricksUnityCatalog \
        --profile "$AWS_CLI_PROFILE" \
        --output text

    log_success "IAM role created"

    # Wait for IAM role to propagate before it can be referenced in trust policies
    log_info "Waiting 10 seconds for IAM role to propagate..."
    sleep 10
}

#------------------------------------------------------------------------------
# Attach S3 access policy (inline)
#------------------------------------------------------------------------------
attach_s3_policy() {
    log_info "Attaching S3 access policy to role..."

    IAM_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${IAM_ROLE_NAME}"

    # Build the policy statements based on read-only setting
    local s3_actions
    if [ "$READ_ONLY" = "true" ]; then
        s3_actions='"s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket", "s3:GetBucketLocation"'
    else
        s3_actions='"s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetBucketLocation"'
    fi

    # Build KMS statement if needed
    local kms_statement=""
    if [ -n "$KMS_KEY_ARN" ]; then
        kms_statement=$(cat <<EOF
,
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:Encrypt",
                "kms:GenerateDataKey*"
            ],
            "Resource": ["$KMS_KEY_ARN"]
        }
EOF
)
    fi

    # Create the inline policy document
    S3_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [$s3_actions],
            "Resource": [
                "arn:aws:s3:::${S3_BUCKET_NAME}",
                "arn:aws:s3:::${S3_BUCKET_NAME}/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": "$IAM_ROLE_ARN"
        }$kms_statement
    ]
}
EOF
)

    # Attach inline policy to role
    aws iam put-role-policy \
        --role-name "$IAM_ROLE_NAME" \
        --policy-name "DatabricksS3Access" \
        --policy-document "$S3_POLICY" \
        --profile "$AWS_CLI_PROFILE"

    log_success "S3 access policy attached"
}

#------------------------------------------------------------------------------
# Attach file events policy (inline, optional)
#------------------------------------------------------------------------------
attach_file_events_policy() {
    if [ "$ENABLE_FILE_EVENTS" != "true" ]; then
        log_info "Skipping file events policy (disabled)"
        return 0
    fi

    log_info "Attaching file events policy to role..."

    FILE_EVENTS_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ManagedFileEventsSetupStatement",
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketNotification",
                "s3:PutBucketNotification",
                "sns:ListSubscriptionsByTopic",
                "sns:GetTopicAttributes",
                "sns:SetTopicAttributes",
                "sns:CreateTopic",
                "sns:TagResource",
                "sns:Publish",
                "sns:Subscribe",
                "sqs:CreateQueue",
                "sqs:DeleteMessage",
                "sqs:ReceiveMessage",
                "sqs:SendMessage",
                "sqs:GetQueueUrl",
                "sqs:GetQueueAttributes",
                "sqs:SetQueueAttributes",
                "sqs:TagQueue",
                "sqs:ChangeMessageVisibility",
                "sqs:PurgeQueue"
            ],
            "Resource": [
                "arn:aws:s3:::$S3_BUCKET_NAME",
                "arn:aws:sqs:*:*:csms-*",
                "arn:aws:sns:*:*:csms-*"
            ]
        },
        {
            "Sid": "ManagedFileEventsListStatement",
            "Effect": "Allow",
            "Action": [
                "sqs:ListQueues",
                "sqs:ListQueueTags",
                "sns:ListTopics"
            ],
            "Resource": [
                "arn:aws:sqs:*:*:csms-*",
                "arn:aws:sns:*:*:csms-*"
            ]
        },
        {
            "Sid": "ManagedFileEventsTeardownStatement",
            "Effect": "Allow",
            "Action": [
                "sns:Unsubscribe",
                "sns:DeleteTopic",
                "sqs:DeleteQueue"
            ],
            "Resource": [
                "arn:aws:sqs:*:*:csms-*",
                "arn:aws:sns:*:*:csms-*"
            ]
        }
    ]
}
EOF
)

    # Attach inline policy to role
    aws iam put-role-policy \
        --role-name "$IAM_ROLE_NAME" \
        --policy-name "DatabricksFileEvents" \
        --policy-document "$FILE_EVENTS_POLICY" \
        --profile "$AWS_CLI_PROFILE"

    log_success "File events policy attached"
}

#------------------------------------------------------------------------------
# Create storage credential in Databricks
#------------------------------------------------------------------------------
create_storage_credential() {
    log_info "Creating storage credential in Databricks: $STORAGE_CREDENTIAL_NAME"

    IAM_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${IAM_ROLE_NAME}"

    # Check if storage credential already exists
    EXISTING_CRED=$(databricks storage-credentials get "$STORAGE_CREDENTIAL_NAME" \
        --profile "$DATABRICKS_PROFILE" \
        --output json 2>/dev/null || echo "")

    if [ -n "$EXISTING_CRED" ] && echo "$EXISTING_CRED" | jq -e '.name' &>/dev/null; then
        log_warn "Storage credential '$STORAGE_CREDENTIAL_NAME' already exists."
        EXTERNAL_ID=$(echo "$EXISTING_CRED" | jq -r '.aws_iam_role.external_id // empty')
        if [ -n "$EXTERNAL_ID" ]; then
            log_info "Using existing external ID: $EXTERNAL_ID"
            return 0
        fi
    fi

    # Create the storage credential
    log_info "Creating new storage credential with role: $IAM_ROLE_ARN"

    # Temporarily disable exit-on-error to capture the response even on failure
    set +e
    CRED_RESPONSE=$(databricks storage-credentials create \
        --json "{\"name\": \"$STORAGE_CREDENTIAL_NAME\", \"aws_iam_role\": {\"role_arn\": \"$IAM_ROLE_ARN\"}, \"comment\": \"Storage credential for S3 bucket $S3_BUCKET_NAME\"}" \
        --profile "$DATABRICKS_PROFILE" \
        --output json 2>&1)
    CRED_EXIT_CODE=$?
    set -e

    # Check for errors
    if [ $CRED_EXIT_CODE -ne 0 ] || echo "$CRED_RESPONSE" | jq -e '.error_code' &>/dev/null; then
        log_error "Failed to create storage credential"
        echo "$CRED_RESPONSE" | jq .
        exit 1
    fi

    # Extract the external ID
    EXTERNAL_ID=$(echo "$CRED_RESPONSE" | jq -r '.aws_iam_role.external_id')

    if [ -z "$EXTERNAL_ID" ] || [ "$EXTERNAL_ID" = "null" ]; then
        log_error "Failed to get external ID from storage credential response"
        echo "$CRED_RESPONSE"
        exit 1
    fi

    log_success "Storage credential created"
    log_info "External ID: $EXTERNAL_ID"
}

#------------------------------------------------------------------------------
# Update IAM role trust policy with external ID (make it self-assuming)
#------------------------------------------------------------------------------
update_trust_policy() {
    log_info "Updating IAM role trust policy with external ID..."

    if [ -z "$EXTERNAL_ID" ]; then
        log_error "External ID not set. Cannot update trust policy."
        exit 1
    fi

    IAM_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${IAM_ROLE_NAME}"

    # Create self-assuming trust policy with actual external ID
    UPDATED_TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "$UNITY_CATALOG_MASTER_ROLE"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "$EXTERNAL_ID"
                }
            }
        },
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "$IAM_ROLE_ARN"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "$EXTERNAL_ID"
                }
            }
        }
    ]
}
EOF
)

    aws iam update-assume-role-policy \
        --role-name "$IAM_ROLE_NAME" \
        --policy-document "$UPDATED_TRUST_POLICY" \
        --profile "$AWS_CLI_PROFILE"

    log_success "Trust policy updated with external ID (self-assuming enabled)"

    # Wait for IAM policy propagation
    # Note: AWS IAM changes can take up to 2 minutes to fully propagate
    log_info "Waiting 90 seconds for IAM policy propagation..."
    sleep 90
}

#------------------------------------------------------------------------------
# Create external location in Databricks
#------------------------------------------------------------------------------
create_external_location() {
    log_info "Creating external location in Databricks: $EXTERNAL_LOCATION_NAME"

    # Build S3 URL (ensure trailing slash for bucket root)
    if [ -n "$S3_PREFIX" ]; then
        S3_URL="s3://${S3_BUCKET_NAME}/${S3_PREFIX}"
    else
        S3_URL="s3://${S3_BUCKET_NAME}/"
    fi

    # Check if external location already exists
    EXISTING_LOC=$(databricks external-locations get "$EXTERNAL_LOCATION_NAME" \
        --profile "$DATABRICKS_PROFILE" \
        --output json 2>/dev/null || echo "")

    if [ -n "$EXISTING_LOC" ] && echo "$EXISTING_LOC" | jq -e '.name' &>/dev/null; then
        log_warn "External location '$EXTERNAL_LOCATION_NAME' already exists. Skipping creation."
        return 0
    fi

    # Create the external location using positional syntax
    log_info "Creating external location: $S3_URL"
    log_info "(This may take a minute while Databricks validates S3 access...)"

    # Retry loop - IAM propagation can take time
    MAX_RETRIES=5
    RETRY_DELAY=60

    for attempt in $(seq 1 $MAX_RETRIES); do
        log_info "Attempt $attempt of $MAX_RETRIES..."

        # Temporarily disable exit-on-error to capture the response even on failure
        set +e
        LOC_RESPONSE=$(databricks external-locations create \
            "$EXTERNAL_LOCATION_NAME" \
            "$S3_URL" \
            "$STORAGE_CREDENTIAL_NAME" \
            --comment "External location for S3 bucket $S3_BUCKET_NAME" \
            --profile "$DATABRICKS_PROFILE" \
            --output json 2>&1)
        CREATE_EXIT_CODE=$?
        set -e

        # Check for success - must have exit code 0 AND valid JSON with name field
        if [ $CREATE_EXIT_CODE -eq 0 ] && echo "$LOC_RESPONSE" | jq -e '.name' &>/dev/null; then
            log_success "External location created: $S3_URL"
            log_info "Location name: $EXTERNAL_LOCATION_NAME"
            return 0
        fi

        # If we have more retries, wait and try again
        if [ $attempt -lt $MAX_RETRIES ]; then
            log_warn "Creation failed, waiting ${RETRY_DELAY}s before retry..."
            if [ -n "$LOC_RESPONSE" ]; then
                log_info "Response: $LOC_RESPONSE"
            fi
            sleep $RETRY_DELAY
            continue
        fi

        # Final failure - no more retries
        log_error "Failed to create external location after $MAX_RETRIES attempts"
        if [ -n "$LOC_RESPONSE" ]; then
            echo "$LOC_RESPONSE"
        fi
        echo ""
        log_info "This usually means IAM propagation hasn't completed."
        log_info "Please wait a few minutes and run the script again."
        log_info "The script will skip already-created resources."
        exit 1
    done
}

#------------------------------------------------------------------------------
# Validate the setup
#------------------------------------------------------------------------------
validate_setup() {
    log_info "Validating storage credential configuration..."

    # Build S3 URL for validation
    if [ -n "$S3_PREFIX" ]; then
        VALIDATE_URL="s3://${S3_BUCKET_NAME}/${S3_PREFIX}"
    else
        VALIDATE_URL="s3://${S3_BUCKET_NAME}/"
    fi

    # Validate storage credential using correct CLI syntax
    VALIDATION=$(databricks storage-credentials validate \
        --storage-credential-name "$STORAGE_CREDENTIAL_NAME" \
        --url "$VALIDATE_URL" \
        --profile "$DATABRICKS_PROFILE" \
        --output json 2>&1 || echo "")

    if [ -n "$VALIDATION" ]; then
        # Check for validation results
        if echo "$VALIDATION" | jq -e '.results' &>/dev/null; then
            # Check each result for failures
            FAILURES=$(echo "$VALIDATION" | jq -r '.results[] | select(.result != "PASS") | "\(.operation): \(.result) - \(.message // "no message")"' 2>/dev/null)
            if [ -z "$FAILURES" ]; then
                log_success "Storage credential validation passed (all operations)"
            else
                log_warn "Storage credential validation returned issues:"
                echo "$FAILURES"
            fi
        elif echo "$VALIDATION" | jq -e '.isValid' &>/dev/null; then
            IS_VALID=$(echo "$VALIDATION" | jq -r '.isValid')
            if [ "$IS_VALID" = "true" ]; then
                log_success "Storage credential validation passed"
            else
                log_warn "Storage credential validation failed"
            fi
        else
            log_info "Validation response:"
            echo "$VALIDATION" | jq '.' 2>/dev/null || echo "$VALIDATION"
        fi
    else
        log_warn "Could not validate storage credential (validation endpoint may not be available)"
    fi
}

#------------------------------------------------------------------------------
# Print summary
#------------------------------------------------------------------------------
print_summary() {
    IAM_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${IAM_ROLE_NAME}"

    echo ""
    echo "=============================================="
    echo -e "${GREEN}Setup Complete!${NC}"
    echo "=============================================="
    echo ""
    echo "Configuration: ${SCRIPT_DIR}/.env"
    echo ""
    echo "Resources Created:"
    echo "  AWS IAM Role: $IAM_ROLE_ARN"
    echo "    - Inline Policy: DatabricksS3Access"
    if [ "$ENABLE_FILE_EVENTS" = "true" ]; then
        echo "    - Inline Policy: DatabricksFileEvents"
    fi
    echo "  Databricks Storage Credential: $STORAGE_CREDENTIAL_NAME"
    echo "  Databricks External Location: $EXTERNAL_LOCATION_NAME"
    echo "  S3 Bucket: s3://${S3_BUCKET_NAME}${S3_PREFIX:+/$S3_PREFIX}"
    echo ""
    echo "Next Steps:"
    echo "  1. Grant permissions on the external location to users/groups"
    echo "  2. Create external tables or volumes using this location"
    echo ""
    echo "Example SQL to grant access:"
    echo "  GRANT READ FILES, WRITE FILES ON EXTERNAL LOCATION \`$EXTERNAL_LOCATION_NAME\` TO \`user@example.com\`;"
    echo ""
}

#------------------------------------------------------------------------------
# Main execution
#------------------------------------------------------------------------------
main() {
    echo "=============================================="
    echo "Databricks External Location Setup Script"
    echo "=============================================="
    echo ""
    echo "Configuration: ${SCRIPT_DIR}/.env"
    echo "AWS Profile: ${AWS_CLI_PROFILE}"
    echo "Databricks Profile: ${DATABRICKS_PROFILE}"
    echo "S3 Bucket: ${S3_BUCKET_NAME}${S3_PREFIX:+/$S3_PREFIX}"
    echo ""

    # Run all steps
    check_prerequisites
    validate_s3_bucket
    create_iam_role
    attach_s3_policy
    attach_file_events_policy
    create_storage_credential
    update_trust_policy
    create_external_location
    validate_setup
    print_summary
}

# Run main function
main "$@"
