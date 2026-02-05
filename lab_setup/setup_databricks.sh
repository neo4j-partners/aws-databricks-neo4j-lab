#!/bin/bash
# Uploads data files to an existing Databricks Unity Catalog volume
# Usage: ./upload_databricks.sh <catalog.schema.volume>
# Example: ./upload_databricks.sh test_catalog.test_schema.test_volume

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <catalog.schema.volume>"
    echo "Example: $0 test_catalog.test_schema.test_volume"
    exit 1
fi

VOLUME_FULL="$1"

# Parse catalog.schema.volume
IFS='.' read -r CATALOG SCHEMA VOLUME <<< "${VOLUME_FULL}"

if [ -z "${CATALOG}" ] || [ -z "${SCHEMA}" ] || [ -z "${VOLUME}" ]; then
    echo "Error: Volume must be in format catalog.schema.volume"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/aircraft_digital_twin_data"
VOLUME_PATH="dbfs:/Volumes/${CATALOG}/${SCHEMA}/${VOLUME}"

echo "=========================================="
echo "Databricks Data Upload"
echo "=========================================="
echo "Volume: ${VOLUME_PATH}"
echo "Data:   ${DATA_DIR}"
echo "=========================================="

# Check if databricks CLI is available
if ! command -v databricks &> /dev/null; then
    echo "Error: Databricks CLI not found. Please install it first:"
    echo "  pip install databricks-cli"
    echo "  databricks configure"
    exit 1
fi

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "Error: Data directory not found: ${DATA_DIR}"
    exit 1
fi

echo ""
echo "Uploading data files..."
echo "-------------------------------------------"

# Files to exclude from upload (documentation, not workshop data)
EXCLUDE="README_LARGE_DATASET.md|ARCHITECTURE.md"

for file in "${DATA_DIR}"/*.csv "${DATA_DIR}"/*.md; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        if echo "${filename}" | grep -qE "^(${EXCLUDE})$"; then
            echo "  Skipping: ${filename}"
            continue
        fi
        echo "  Uploading: ${filename}"
        databricks fs cp "$file" "${VOLUME_PATH}/${filename}" --overwrite
    fi
done

echo ""
echo "Verifying upload..."
echo "-------------------------------------------"
echo "Files in ${VOLUME_PATH}:"
databricks fs ls "${VOLUME_PATH}"

echo ""
echo "Upload complete!"
