#!/bin/bash
# Delete all workshop resources: volumes, schemas, and catalog
set -uo pipefail

# Accept optional catalog argument, otherwise use default
CATALOG="${1:-aws-databricks-neo4j-lab}"

echo "Current Databricks CLI user:"
databricks current-user me | jq -r '.userName // .user_name // "unknown"'

echo ""
echo "Deleting entire catalog '${CATALOG}' and everything inside it..."

# Iterate all schemas in the catalog, delete volumes in each, then delete the schema
echo ""
echo "Deleting schemas and their contents..."
schemas_json=$(databricks schemas list "${CATALOG}" --output json 2>&1)

for schema_full_name in $(echo "${schemas_json}" | jq -r '.[].full_name'); do
    schema_name=$(echo "${schema_full_name}" | cut -d. -f2)

    # Skip system schemas
    if [ "${schema_name}" = "information_schema" ] || [ "${schema_name}" = "default" ]; then
        echo "  Skipping system schema: ${schema_full_name}"
        continue
    fi

    # Delete volumes in this schema
    volumes_json=$(databricks volumes list "${CATALOG}" "${schema_name}" --output json 2>&1)
    if echo "${volumes_json}" | jq -e 'type == "array"' &>/dev/null; then
        for volume in $(echo "${volumes_json}" | jq -r '.[].name'); do
            echo "  Deleting volume: ${CATALOG}.${schema_name}.${volume}"
            databricks volumes delete "${CATALOG}.${schema_name}.${volume}"
        done
    fi

    echo "  Deleting schema: ${schema_full_name}"
    databricks schemas delete "${schema_full_name}"
done

# Delete the catalog
echo ""
echo "Deleting catalog: ${CATALOG}"
databricks catalogs delete "${CATALOG}" --force

echo ""
echo "Done. All workshop resources deleted."
