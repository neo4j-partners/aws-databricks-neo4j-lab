#!/bin/bash
#
# Cleanup Databricks External Location Resources
# Removes resources created by setup_databricks_external_location.sh
#
# Usage:
#   ./cleanup_databricks_external_location.sh
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
        exit 1
    fi

    set -a
    # shellcheck source=/dev/null
    source "$env_file"
    set +a
}

load_env

#------------------------------------------------------------------------------
# Configuration defaults (can be overridden by .env)
#------------------------------------------------------------------------------
AWS_CLI_PROFILE="${AWS_CLI_PROFILE:-oneblink}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
IAM_ROLE_NAME="${IAM_ROLE_NAME:-databricks-unity-catalog-access}"
DATABRICKS_PROFILE="${DATABRICKS_PROFILE:-oneblink}"
STORAGE_CREDENTIAL_NAME="${STORAGE_CREDENTIAL_NAME:-my-s3-storage-credential}"
EXTERNAL_LOCATION_NAME="${EXTERNAL_LOCATION_NAME:-my-s3-external-location}"

#------------------------------------------------------------------------------
# Color output helpers
#------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
# Delete External Location
#------------------------------------------------------------------------------
delete_external_location() {
    log_info "Deleting external location: $EXTERNAL_LOCATION_NAME"

    if databricks external-locations get "$EXTERNAL_LOCATION_NAME" \
        --profile "$DATABRICKS_PROFILE" &>/dev/null; then

        databricks external-locations delete "$EXTERNAL_LOCATION_NAME" \
            --profile "$DATABRICKS_PROFILE" \
            --force 2>/dev/null || true

        log_success "External location deleted"
    else
        log_warn "External location '$EXTERNAL_LOCATION_NAME' not found, skipping"
    fi
}

#------------------------------------------------------------------------------
# Delete Storage Credential
#------------------------------------------------------------------------------
delete_storage_credential() {
    log_info "Deleting storage credential: $STORAGE_CREDENTIAL_NAME"

    if databricks storage-credentials get "$STORAGE_CREDENTIAL_NAME" \
        --profile "$DATABRICKS_PROFILE" &>/dev/null; then

        databricks storage-credentials delete "$STORAGE_CREDENTIAL_NAME" \
            --profile "$DATABRICKS_PROFILE" \
            --force 2>/dev/null || true

        log_success "Storage credential deleted"
    else
        log_warn "Storage credential '$STORAGE_CREDENTIAL_NAME' not found, skipping"
    fi
}

#------------------------------------------------------------------------------
# Delete IAM Role and Policies
#------------------------------------------------------------------------------
delete_iam_role() {
    log_info "Deleting IAM role: $IAM_ROLE_NAME"

    # Check if role exists
    if ! aws iam get-role --role-name "$IAM_ROLE_NAME" \
        --profile "$AWS_CLI_PROFILE" &>/dev/null; then
        log_warn "IAM role '$IAM_ROLE_NAME' not found, skipping"
        return 0
    fi

    # Delete inline policies
    log_info "Removing inline policies..."

    POLICIES=$(aws iam list-role-policies \
        --role-name "$IAM_ROLE_NAME" \
        --profile "$AWS_CLI_PROFILE" \
        --query 'PolicyNames[]' \
        --output text 2>/dev/null || echo "")

    for policy in $POLICIES; do
        log_info "  Deleting policy: $policy"
        aws iam delete-role-policy \
            --role-name "$IAM_ROLE_NAME" \
            --policy-name "$policy" \
            --profile "$AWS_CLI_PROFILE" 2>/dev/null || true
    done

    # Detach managed policies
    log_info "Detaching managed policies..."

    ATTACHED=$(aws iam list-attached-role-policies \
        --role-name "$IAM_ROLE_NAME" \
        --profile "$AWS_CLI_PROFILE" \
        --query 'AttachedPolicies[].PolicyArn' \
        --output text 2>/dev/null || echo "")

    for policy_arn in $ATTACHED; do
        log_info "  Detaching policy: $policy_arn"
        aws iam detach-role-policy \
            --role-name "$IAM_ROLE_NAME" \
            --policy-arn "$policy_arn" \
            --profile "$AWS_CLI_PROFILE" 2>/dev/null || true
    done

    # Delete the role
    log_info "Deleting role..."
    aws iam delete-role \
        --role-name "$IAM_ROLE_NAME" \
        --profile "$AWS_CLI_PROFILE"

    log_success "IAM role deleted"
}

#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------
main() {
    echo "=============================================="
    echo "Databricks External Location Cleanup Script"
    echo "=============================================="
    echo ""
    echo "Configuration: ${SCRIPT_DIR}/.env"
    echo "AWS Profile: ${AWS_CLI_PROFILE}"
    echo "Databricks Profile: ${DATABRICKS_PROFILE}"
    echo ""
    echo "Resources to delete:"
    echo "  - External Location: $EXTERNAL_LOCATION_NAME"
    echo "  - Storage Credential: $STORAGE_CREDENTIAL_NAME"
    echo "  - IAM Role: $IAM_ROLE_NAME"
    echo ""

    # Confirm before proceeding
    read -p "Are you sure you want to delete these resources? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleanup cancelled"
        exit 0
    fi

    echo ""

    # Delete in reverse order of creation
    delete_external_location
    delete_storage_credential
    delete_iam_role

    echo ""
    echo "=============================================="
    echo -e "${GREEN}Cleanup Complete!${NC}"
    echo "=============================================="
}

main "$@"
