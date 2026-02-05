#!/bin/bash
# Full Databricks environment setup for the Neo4j workshop.
#
# Creates (or reuses) a compute cluster, installs libraries, uploads data files,
# and creates lakehouse tables — all in one script.
#
# The Neo4j Spark Connector requires Dedicated (Single User) access mode —
# shared access modes are not supported.
# See: https://neo4j.com/docs/spark/current/databricks/
#
# Usage:
#   ./setup_databricks.sh [catalog.schema.volume] [user-email] [cluster-name]
#
# All arguments are optional:
#   catalog.schema.volume  Target volume (default: aws-databricks-neo4j-lab.lab-schema.lab-volume)
#   user-email             Cluster owner (default: auto-detected from CLI auth)
#   cluster-name           Cluster to create or reuse (default: "Small Spark 4.0")
#
# Examples:
#   ./setup_databricks.sh                                                              # all defaults
#   ./setup_databricks.sh aws-databricks-neo4j-lab.lab-schema.lab-volume               # explicit volume
#   ./setup_databricks.sh test_catalog.test_schema.test_volume ryan.knight@neo4j.com   # volume + user
#   ./setup_databricks.sh test_catalog.test_schema.test_volume ryan.knight@neo4j.com "My Workshop"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ──────────────────────────────────────────────
# Parse arguments
# ──────────────────────────────────────────────
VOLUME_FULL="${1:-aws-databricks-neo4j-lab.lab-schema.lab-volume}"
IFS='.' read -r CATALOG VOLUME_SCHEMA VOLUME <<< "${VOLUME_FULL}"

if [ -z "${CATALOG}" ] || [ -z "${VOLUME_SCHEMA}" ] || [ -z "${VOLUME}" ]; then
    echo "Error: Volume must be in format catalog.schema.volume"
    echo "Example: ./setup_databricks.sh test_catalog.test_schema.test_volume"
    exit 1
fi

USER_ARG="${2:-}"
CLUSTER_NAME="${3:-Small Spark 4.0}"

# ──────────────────────────────────────────────
# Cluster configuration
# ──────────────────────────────────────────────
SPARK_VERSION="17.3.x-cpu-ml-scala2.13"   # 17.3 LTS ML (Spark 4.0.0, Scala 2.13)
NODE_TYPE="Standard_D4ds_v5"               # 16 GB Memory, 4 Cores (Azure)
RUNTIME_ENGINE="PHOTON"                    # Photon acceleration
AUTOTERMINATION_MINUTES=30

# ──────────────────────────────────────────────
# Libraries
# ──────────────────────────────────────────────
NEO4J_SPARK_CONNECTOR="org.neo4j:neo4j-connector-apache-spark_2.13:5.3.10_for_spark_3"

PYPI_PACKAGES=(
    "neo4j==6.1.0"
    "databricks-agents>=1.2.0"
    "langgraph==1.0.7"
    "langchain-openai==1.1.7"
    "pydantic==2.12.5"
    "langchain-core>=1.2.0"
    "databricks-langchain>=0.11.0"
    "dspy>=3.0.4"
    "neo4j-graphrag>=1.13.0"
    "beautifulsoup4>=4.12.0"
    "sentence_transformers"
)

# ──────────────────────────────────────────────
# Data / script paths
# ──────────────────────────────────────────────
DATA_DIR="${SCRIPT_DIR}/aircraft_digital_twin_data"
PY_SCRIPT="${SCRIPT_DIR}/create_lakehouse_tables.py"
VOLUME_PATH="dbfs:/Volumes/${CATALOG}/${VOLUME_SCHEMA}/${VOLUME}"

# Files to exclude from upload (documentation, not workshop data)
EXCLUDE="README_LARGE_DATASET.md|ARCHITECTURE.md"

# ──────────────────────────────────────────────
# 1. Pre-flight checks
# ──────────────────────────────────────────────
if ! command -v databricks &> /dev/null; then
    echo "Error: Databricks CLI not found. Install with:"
    echo "  pip install databricks-cli"
    echo "  databricks auth login --host https://your-workspace.cloud.databricks.com"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq not found. Install with:"
    echo "  brew install jq       # macOS"
    echo "  apt-get install jq    # Linux"
    exit 1
fi

if [ ! -d "${DATA_DIR}" ]; then
    echo "Error: Data directory not found: ${DATA_DIR}"
    exit 1
fi

if [ ! -f "${PY_SCRIPT}" ]; then
    echo "Error: Python script not found: ${PY_SCRIPT}"
    exit 1
fi

# ──────────────────────────────────────────────
# 2. Resolve single-user identity
# ──────────────────────────────────────────────
if [ -n "${USER_ARG}" ]; then
    SINGLE_USER="${USER_ARG}"
else
    echo "Detecting current Databricks user..."
    SINGLE_USER=$(databricks current-user me --output json | jq -r '.userName')
    if [ -z "${SINGLE_USER}" ] || [ "${SINGLE_USER}" = "null" ]; then
        echo "Error: Could not detect current user. Pass email as second argument:"
        echo "  $0 <catalog.schema.volume> user@example.com"
        exit 1
    fi
fi

echo "=========================================="
echo "Databricks Environment Setup"
echo "=========================================="
echo "Volume:   ${CATALOG}.${VOLUME_SCHEMA}.${VOLUME}"
echo "Cluster:  ${CLUSTER_NAME}"
echo "Runtime:  ${SPARK_VERSION} + ${RUNTIME_ENGINE}"
echo "Node:     ${NODE_TYPE} (single node)"
echo "User:     ${SINGLE_USER}"
echo "Timeout:  ${AUTOTERMINATION_MINUTES} min"
echo "=========================================="
echo ""

# ──────────────────────────────────────────────
# 3. Resolve or create cluster
# ──────────────────────────────────────────────
echo "Looking for existing cluster \"${CLUSTER_NAME}\"..."
CLUSTERS_JSON=$(databricks clusters list --output json)
EXISTING=$(echo "${CLUSTERS_JSON}" | jq -r --arg name "${CLUSTER_NAME}" '[.[] | select(.cluster_name == $name)] | .[0]')
EXISTING_ID=$(echo "${EXISTING}" | jq -r '.cluster_id // empty')
EXISTING_STATE=$(echo "${EXISTING}" | jq -r '.state // empty')

if [ -n "${EXISTING_ID}" ]; then
    CLUSTER_ID="${EXISTING_ID}"
    echo "  Found: ${CLUSTER_ID} (state: ${EXISTING_STATE})"

    if [ "${EXISTING_STATE}" = "TERMINATED" ]; then
        echo "  Starting cluster..."
        databricks clusters start "${CLUSTER_ID}"
    elif [ "${EXISTING_STATE}" = "RUNNING" ]; then
        echo "  Cluster is already running."
    fi
else
    echo "  Not found — creating new cluster..."

    CLUSTER_JSON=$(cat <<EOF
{
  "cluster_name": "${CLUSTER_NAME}",
  "spark_version": "${SPARK_VERSION}",
  "node_type_id": "${NODE_TYPE}",
  "driver_node_type_id": "${NODE_TYPE}",
  "num_workers": 0,
  "data_security_mode": "SINGLE_USER",
  "single_user_name": "${SINGLE_USER}",
  "runtime_engine": "${RUNTIME_ENGINE}",
  "autotermination_minutes": ${AUTOTERMINATION_MINUTES},
  "spark_conf": {
    "spark.databricks.cluster.profile": "singleNode",
    "spark.master": "local[*]"
  },
  "custom_tags": {
    "ResourceClass": "SingleNode"
  }
}
EOF
)

    CREATE_RESPONSE=$(databricks clusters create --json "${CLUSTER_JSON}")
    CLUSTER_ID=$(echo "${CREATE_RESPONSE}" | jq -r '.cluster_id')

    if [ -z "${CLUSTER_ID}" ] || [ "${CLUSTER_ID}" = "null" ]; then
        echo "Error: Failed to create cluster."
        echo "${CREATE_RESPONSE}"
        exit 1
    fi

    echo "  Created: ${CLUSTER_ID}"
fi
echo ""

# ──────────────────────────────────────────────
# 4. Wait for cluster to reach RUNNING state
# ──────────────────────────────────────────────
echo "Waiting for cluster to start..."

MAX_WAIT=600   # 10 minutes
INTERVAL=15
ELAPSED=0

while [ ${ELAPSED} -lt ${MAX_WAIT} ]; do
    STATE=$(databricks clusters get "${CLUSTER_ID}" --output json | jq -r '.state')
    echo "  State: ${STATE} (${ELAPSED}s elapsed)"

    case "${STATE}" in
        RUNNING)
            echo ""
            echo "Cluster is running."
            break
            ;;
        TERMINATED|ERROR|UNKNOWN)
            echo "Error: Cluster entered unexpected state: ${STATE}"
            databricks clusters get "${CLUSTER_ID}" --output json | jq '.state_message'
            exit 1
            ;;
        *)
            sleep ${INTERVAL}
            ELAPSED=$((ELAPSED + INTERVAL))
            ;;
    esac
done

if [ ${ELAPSED} -ge ${MAX_WAIT} ]; then
    echo "Error: Timed out waiting for cluster to start (${MAX_WAIT}s)."
    echo "Check cluster status manually:"
    echo "  databricks clusters get ${CLUSTER_ID}"
    exit 1
fi

# ──────────────────────────────────────────────
# 5. Install libraries (skip if already installed)
# ──────────────────────────────────────────────
echo ""
echo "Checking library status..."

STATUS_JSON=$(databricks libraries cluster-status "${CLUSTER_ID}" --output json 2>/dev/null || echo "[]")
ALREADY_INSTALLED=$(echo "${STATUS_JSON}" | jq 'length')
ALREADY_PENDING=$(echo "${STATUS_JSON}" | jq '[.[] | select(.status != "INSTALLED")] | length')

if [ "${ALREADY_INSTALLED}" -gt 0 ] && [ "${ALREADY_PENDING}" -eq 0 ]; then
    echo "  ${ALREADY_INSTALLED} libraries already installed — skipping installation."
else
    echo "Installing libraries..."

    # Build the libraries JSON array
    LIBRARIES_JSON="["

    # Maven library (Neo4j Spark Connector)
    LIBRARIES_JSON+=$(cat <<EOF
  {
    "maven": {
      "coordinates": "${NEO4J_SPARK_CONNECTOR}"
    }
  }
EOF
)

    # PyPI libraries
    for pkg in "${PYPI_PACKAGES[@]}"; do
        LIBRARIES_JSON+=","
        LIBRARIES_JSON+=$(cat <<EOF
  {
    "pypi": {
      "package": "${pkg}"
    }
  }
EOF
)
    done

    LIBRARIES_JSON+="]"

    INSTALL_JSON=$(cat <<EOF
{
  "cluster_id": "${CLUSTER_ID}",
  "libraries": ${LIBRARIES_JSON}
}
EOF
)

    databricks libraries install --json "${INSTALL_JSON}"

    echo "Library installation started (installs asynchronously)."
    echo ""

    # ──────────────────────────────────────────────
    # 6. Poll library status until all are installed
    # ──────────────────────────────────────────────
    echo "Waiting for libraries to install..."

    LIB_MAX_WAIT=600
    LIB_ELAPSED=0

    while [ ${LIB_ELAPSED} -lt ${LIB_MAX_WAIT} ]; do
        sleep ${INTERVAL}
        LIB_ELAPSED=$((LIB_ELAPSED + INTERVAL))

        STATUS_JSON=$(databricks libraries cluster-status "${CLUSTER_ID}" --output json)

        TOTAL=$(echo "${STATUS_JSON}" | jq 'length')
        INSTALLED=$(echo "${STATUS_JSON}" | jq '[.[] | select(.status == "INSTALLED")] | length')
        PENDING=$(echo "${STATUS_JSON}" | jq '[.[] | select(.status == "PENDING" or .status == "RESOLVING" or .status == "INSTALLING")] | length')
        FAILED=$(echo "${STATUS_JSON}" | jq '[.[] | select(.status == "FAILED")] | length')

        echo "  ${INSTALLED}/${TOTAL} installed, ${PENDING} pending, ${FAILED} failed (${LIB_ELAPSED}s)"

        if [ "${PENDING}" -eq 0 ]; then
            break
        fi
    done
fi

# ──────────────────────────────────────────────
# 7. Report library status
# ──────────────────────────────────────────────
echo ""
echo "Library status:"

databricks libraries cluster-status "${CLUSTER_ID}" --output json \
    | jq -r '.[] | "\(.status)\t\(.library | to_entries[0] | .value | if .coordinates then .coordinates elif .package then .package else . end)"'

FINAL_FAILED=$(databricks libraries cluster-status "${CLUSTER_ID}" --output json \
    | jq '[.[] | select(.status == "FAILED")] | length')

echo ""
if [ "${FINAL_FAILED}" -gt 0 ]; then
    echo "WARNING: ${FINAL_FAILED} library(ies) failed to install."
    echo "Check details with:"
    echo "  databricks libraries cluster-status ${CLUSTER_ID}"
    echo ""
fi

# ──────────────────────────────────────────────
# 8. Upload data files to volume
# ──────────────────────────────────────────────
echo "=========================================="
echo "Uploading Data Files"
echo "=========================================="
echo "Source: ${DATA_DIR}"
echo "Target: ${VOLUME_PATH}"
echo ""

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
databricks fs ls "${VOLUME_PATH}"
echo "  Upload complete."

# ──────────────────────────────────────────────
# 9. Create lakehouse tables via Command Execution API
# ──────────────────────────────────────────────
echo ""
echo "=========================================="
echo "Creating Lakehouse Tables"
echo "=========================================="

echo "Creating execution context..."
CONTEXT_RESPONSE=$(databricks api post /api/1.2/contexts/create --json "{
    \"clusterId\": \"${CLUSTER_ID}\",
    \"language\": \"python\"
}" 2>&1)

CONTEXT_ID=$(echo "${CONTEXT_RESPONSE}" | jq -r '.id // empty')

if [ -z "${CONTEXT_ID}" ]; then
    echo "Error: Failed to create execution context."
    echo "${CONTEXT_RESPONSE}"
    exit 1
fi

echo "  Context ID: ${CONTEXT_ID}"

# Cleanup function to destroy the context on exit
cleanup() {
    if [ -n "${CONTEXT_ID:-}" ]; then
        echo ""
        echo "Destroying execution context..."
        databricks api post /api/1.2/contexts/destroy --json "{
            \"clusterId\": \"${CLUSTER_ID}\",
            \"contextId\": \"${CONTEXT_ID}\"
        }" > /dev/null 2>&1 || true
        echo "  Done."
    fi
}
trap cleanup EXIT

# Read the script and prepend sys.argv overrides
echo "Executing create_lakehouse_tables.py..."
PYTHON_CODE="import sys"$'\n'
PYTHON_CODE+="sys.argv = [\"create_lakehouse_tables.py\", \"${CATALOG}\", \"${VOLUME_SCHEMA}\", \"${VOLUME}\"]"$'\n\n'
PYTHON_CODE+=$(cat "${PY_SCRIPT}")

ESCAPED_CODE=$(printf '%s' "${PYTHON_CODE}" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

EXEC_RESPONSE=$(databricks api post /api/1.2/commands/execute --json "{
    \"clusterId\": \"${CLUSTER_ID}\",
    \"contextId\": \"${CONTEXT_ID}\",
    \"language\": \"python\",
    \"command\": ${ESCAPED_CODE}
}" 2>&1)

COMMAND_ID=$(echo "${EXEC_RESPONSE}" | jq -r '.id // empty')

if [ -z "${COMMAND_ID}" ]; then
    echo "Error: Failed to submit command."
    echo "${EXEC_RESPONSE}"
    exit 1
fi

echo "  Command ID: ${COMMAND_ID}"
echo ""
echo "Waiting for table creation to complete..."

CMD_MAX_WAIT=900   # 15 minutes
CMD_INTERVAL=10
CMD_ELAPSED=0

while [ ${CMD_ELAPSED} -lt ${CMD_MAX_WAIT} ]; do
    sleep ${CMD_INTERVAL}
    CMD_ELAPSED=$((CMD_ELAPSED + CMD_INTERVAL))

    CMD_STATUS=$(databricks api get "/api/1.2/commands/status?clusterId=${CLUSTER_ID}&contextId=${CONTEXT_ID}&commandId=${COMMAND_ID}" 2>&1)
    CMD_STATE=$(echo "${CMD_STATUS}" | jq -r '.status // "Unknown"')

    echo "  Status: ${CMD_STATE} (${CMD_ELAPSED}s elapsed)"

    case "${CMD_STATE}" in
        Finished|Cancelled|Error)
            break
            ;;
    esac
done

if [ ${CMD_ELAPSED} -ge ${CMD_MAX_WAIT} ]; then
    echo "Error: Timed out waiting for table creation (${CMD_MAX_WAIT}s)."
    exit 1
fi

# Show table creation results
RESULT_TYPE=$(echo "${CMD_STATUS}" | jq -r '.results.resultType // "unknown"')

if [ "${RESULT_TYPE}" = "text" ] || [ "${RESULT_TYPE}" = "table" ]; then
    echo ""
    echo "${CMD_STATUS}" | jq -r '.results.data // empty'
elif [ "${RESULT_TYPE}" = "error" ]; then
    echo ""
    echo "Table creation FAILED:"
    echo "${CMD_STATUS}" | jq -r '.results.summary // empty'
    echo "${CMD_STATUS}" | jq -r '.results.cause // empty'
    exit 1
fi

# ──────────────────────────────────────────────
# 10. Final summary
# ──────────────────────────────────────────────
echo ""
echo "=========================================="
echo "Setup Complete"
echo "=========================================="
echo "Cluster ID:   ${CLUSTER_ID}"
echo "Cluster Name: ${CLUSTER_NAME}"
echo "User:         ${SINGLE_USER}"
echo "Access Mode:  Dedicated (Single User)"
echo "Volume:       ${CATALOG}.${VOLUME_SCHEMA}.${VOLUME}"
echo "Lakehouse:    ${CATALOG}.lakehouse"
echo ""
echo "To check status later:"
echo "  databricks clusters get ${CLUSTER_ID}"
echo "  databricks libraries cluster-status ${CLUSTER_ID}"
