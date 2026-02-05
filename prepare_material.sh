#!/bin/bash
# Prepares lab notebooks for Databricks import
# Creates a zip file containing only .ipynb files from Labs 5 and 6

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="${SCRIPT_DIR}/databricks_labs.zip"

# Remove existing zip if present
rm -f "$OUTPUT_FILE"

# Create zip with just the notebooks, preserving folder structure
cd "$SCRIPT_DIR"
zip -r "$OUTPUT_FILE" \
    Lab_5_Databricks_ETL_Neo4j/*.ipynb \
    Lab_6_Semantic_Search/*.ipynb

echo "Created: $OUTPUT_FILE"
echo "Contents:"
unzip -l "$OUTPUT_FILE"
