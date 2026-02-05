#!/bin/bash
# Creates lakehouse Delta Lake tables from CSV files in a Databricks Volume
# Uses the Statement Execution API via `databricks api post`
# Usage: ./create_lakehouse_tables.sh [catalog]
# Example: ./create_lakehouse_tables.sh aws-databricks-neo4j-lab

set -euo pipefail

CATALOG="${1:-aws-databricks-neo4j-lab}"
SCHEMA="lab-schema"
VOLUME="lab-volume"
LAKEHOUSE_SCHEMA="lakehouse"
VOLUME_PATH="/Volumes/${CATALOG}/${SCHEMA}/${VOLUME}"

echo "=========================================="
echo "Create Lakehouse Tables"
echo "=========================================="
echo "Catalog:  ${CATALOG}"
echo "Schema:   ${LAKEHOUSE_SCHEMA}"
echo "Source:   ${VOLUME_PATH}"
echo "=========================================="

# Check prerequisites
if ! command -v databricks &> /dev/null; then
    echo "Error: Databricks CLI not found."
    exit 1
fi
if ! command -v jq &> /dev/null; then
    echo "Error: jq not found. Install with: brew install jq"
    exit 1
fi

# Find first SQL warehouse
echo ""
echo "Finding SQL warehouse..."
WAREHOUSE_JSON=$(databricks warehouses list --output json)
WAREHOUSE_ID=$(echo "${WAREHOUSE_JSON}" | jq -r '.[0].id // empty')
WAREHOUSE_NAME=$(echo "${WAREHOUSE_JSON}" | jq -r '.[0].name // empty')

if [ -z "${WAREHOUSE_ID}" ]; then
    echo "Error: No SQL warehouses found. Create one in the Databricks UI."
    exit 1
fi
echo "  Using: ${WAREHOUSE_NAME} (${WAREHOUSE_ID})"

# Execute a SQL statement via the Statement Execution API
# Arguments: $1 = SQL statement, $2 = description (optional)
# Returns: sets LAST_RESULT to the full JSON response
execute_sql() {
    local sql="$1"
    local desc="${2:-}"

    if [ -n "${desc}" ]; then
        printf "  %-50s" "${desc}..."
    fi

    # Escape the SQL for JSON: handle newlines and quotes
    local escaped_sql
    escaped_sql=$(printf '%s' "${sql}" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

    LAST_RESULT=$(databricks api post /api/2.0/sql/statements/ --json "{
        \"warehouse_id\": \"${WAREHOUSE_ID}\",
        \"statement\": ${escaped_sql},
        \"wait_timeout\": \"50s\"
    }" 2>&1)

    local status
    status=$(echo "${LAST_RESULT}" | jq -r '.status.state // "UNKNOWN"')

    # Poll if still pending/running
    while [ "${status}" = "PENDING" ] || [ "${status}" = "RUNNING" ]; do
        sleep 2
        local stmt_id
        stmt_id=$(echo "${LAST_RESULT}" | jq -r '.statement_id')
        LAST_RESULT=$(databricks api get "/api/2.0/sql/statements/${stmt_id}" 2>&1)
        status=$(echo "${LAST_RESULT}" | jq -r '.status.state // "UNKNOWN"')
    done

    if [ "${status}" = "SUCCEEDED" ]; then
        if [ -n "${desc}" ]; then
            echo "OK"
        fi
        return 0
    else
        local error
        error=$(echo "${LAST_RESULT}" | jq -r '.status.error.message // .message // "Unknown error"')
        if [ -n "${desc}" ]; then
            echo "FAILED"
        fi
        echo "    Error: ${error}"
        return 1
    fi
}

# --- Create lakehouse schema ---
echo ""
echo "Creating lakehouse schema..."
execute_sql \
    "CREATE SCHEMA IF NOT EXISTS \`${CATALOG}\`.\`${LAKEHOUSE_SCHEMA}\`" \
    "CREATE SCHEMA ${LAKEHOUSE_SCHEMA}"

# --- Create Delta Lake tables ---
echo ""
echo "Creating Delta Lake tables..."

execute_sql \
    "CREATE TABLE IF NOT EXISTS \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.aircraft USING DELTA AS SELECT * FROM csv.\`${VOLUME_PATH}/nodes_aircraft.csv\` OPTIONS (header = 'true', inferSchema = 'true')" \
    "CREATE TABLE aircraft"

execute_sql \
    "CREATE TABLE IF NOT EXISTS \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.systems USING DELTA AS SELECT * FROM csv.\`${VOLUME_PATH}/nodes_systems.csv\` OPTIONS (header = 'true', inferSchema = 'true')" \
    "CREATE TABLE systems"

execute_sql \
    "CREATE TABLE IF NOT EXISTS \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensors USING DELTA AS SELECT * FROM csv.\`${VOLUME_PATH}/nodes_sensors.csv\` OPTIONS (header = 'true', inferSchema = 'true')" \
    "CREATE TABLE sensors"

execute_sql \
    "CREATE TABLE IF NOT EXISTS \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensor_readings USING DELTA PARTITIONED BY (sensor_id) AS SELECT reading_id, sensor_id, to_timestamp(ts) as timestamp, CAST(value AS DOUBLE) as value FROM csv.\`${VOLUME_PATH}/nodes_readings.csv\` OPTIONS (header = 'true', inferSchema = 'true')" \
    "CREATE TABLE sensor_readings"

# --- Add table and column comments for Genie ---
echo ""
echo "Adding table/column comments for Genie..."

# Aircraft
execute_sql "COMMENT ON TABLE \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.aircraft IS 'Fleet of aircraft with tail numbers, models, and operators'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.aircraft.\`_id:ID(Aircraft)\` IS 'Unique aircraft identifier'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.aircraft.tail_number IS 'Aircraft registration/tail number (e.g., N95040A)'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.aircraft.model IS 'Aircraft model (e.g., B737-800, A320-200)'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.aircraft.operator IS 'Airline operator name'"

# Systems
execute_sql "COMMENT ON TABLE \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.systems IS 'Aircraft systems including engines, avionics, and hydraulics'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.systems.\`_id:ID(System)\` IS 'Unique system identifier'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.systems.type IS 'System type (Engine, Avionics, Hydraulics)'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.systems.name IS 'Human-readable system name'"

# Sensors
execute_sql "COMMENT ON TABLE \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensors IS 'Sensors installed on aircraft systems'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensors.\`_id:ID(Sensor)\` IS 'Unique sensor identifier'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensors.type IS 'Sensor type: EGT (Exhaust Gas Temperature in Celsius), Vibration (ips), N1Speed (RPM), FuelFlow (kg/s)'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensors.unit IS 'Unit of measurement'"

# Sensor readings
execute_sql "COMMENT ON TABLE \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensor_readings IS 'Hourly sensor readings over 90 days (July-September 2024)'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensor_readings.reading_id IS 'Unique reading identifier'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensor_readings.sensor_id IS 'Foreign key to sensors table'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensor_readings.timestamp IS 'Reading timestamp (hourly intervals)'"
execute_sql "COMMENT ON COLUMN \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensor_readings.value IS 'Sensor reading value in the sensor unit'"

echo "  Comments added."

# --- Verify row counts ---
echo ""
echo "Verifying row counts..."

execute_sql \
    "SELECT 'aircraft' as table_name, COUNT(*) as row_count FROM \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.aircraft UNION ALL SELECT 'systems', COUNT(*) FROM \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.systems UNION ALL SELECT 'sensors', COUNT(*) FROM \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensors UNION ALL SELECT 'sensor_readings', COUNT(*) FROM \`${CATALOG}\`.${LAKEHOUSE_SCHEMA}.sensor_readings" \
    "Row count query"

# Parse and display results
echo ""
echo "  Table                  Rows"
echo "  --------------------  ----------"
echo "${LAST_RESULT}" | jq -r '.result.data_array[]? | "  \(.[0] | . + " " * (20 - length))  \(.[1])"'

echo ""
echo "Lakehouse tables created successfully!"
