# populate-aircraft-db

Standalone CLI tool that loads the Aircraft Digital Twin dataset into a Neo4j Aura instance. Handles the full pipeline: CSV data loading, maintenance manual chunking, OpenAI embedding generation, and LLM-powered entity extraction.

## Quick Start

```bash
cd lab_setup/populate_aircraft_db

# Create .env with your Neo4j credentials
cat > .env <<EOF
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
OPENAI_API_KEY=sk-...          # required for embed/extract commands only
EOF

# Install and run
uv sync
uv run populate-aircraft-db load --clean
```

## Commands

| Command | Description |
|---------|-------------|
| `load [--clean]` | Load all nodes and relationships from CSV files |
| `embed [--clean] [--chunk-size N] [--chunk-overlap N]` | Chunk maintenance manuals, generate OpenAI embeddings, create vector/fulltext indexes |
| `extract [--clean] [--limit N] [--document DOC_ID]` | Extract structured entities (fault codes, part numbers, etc.) from chunks using OpenAI |
| `verify` | Print node and relationship counts (read-only) |
| `clean` | Delete all nodes and relationships |

### Typical full-load sequence

```bash
uv run populate-aircraft-db load --clean
uv run populate-aircraft-db embed
uv run populate-aircraft-db extract
```

## Configuration

Settings are loaded from a `.env` file in the project root or from environment variables.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEO4J_URI` | yes | - | Connection URI (e.g. `neo4j+s://...`) |
| `NEO4J_USERNAME` | no | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | yes | - | Neo4j password |
| `OPENAI_API_KEY` | for embed/extract | - | OpenAI API key |
| `OPENAI_EMBEDDING_MODEL` | no | `text-embedding-3-small` | Embedding model |
| `OPENAI_EMBEDDING_DIMENSIONS` | no | `1536` | Embedding dimensions |
| `OPENAI_EXTRACTION_MODEL` | no | `gpt-4o-mini` | Chat model for entity extraction |

## What Gets Loaded

### `load` -- Operational graph (from CSVs)

**9 node types:** Aircraft, System, Component, Sensor, Airport, Flight, Delay, MaintenanceEvent, Removal

**12 relationship types:** HAS_SYSTEM, HAS_COMPONENT, HAS_SENSOR, HAS_EVENT, OPERATES_FLIGHT, DEPARTS_FROM, ARRIVES_AT, HAS_DELAY, AFFECTS_SYSTEM, AFFECTS_AIRCRAFT, HAS_REMOVAL, REMOVED_COMPONENT

CSV files are read from `lab_setup/aircraft_digital_twin_data/`.

### `embed` -- Document chunks with embeddings

Processes three maintenance manuals (A320-200, A321neo, B737-800) into Document and Chunk nodes with a NEXT_CHUNK chain. Generates OpenAI embeddings and creates:

- **Vector index:** `maintenanceChunkEmbeddings` on `Chunk.embedding`
- **Fulltext index:** `maintenanceChunkText` on `Chunk.text`

### `extract` -- Structured entities from manuals

Uses OpenAI to extract five entity types from chunks:

- **FaultCode** -- fault codes with severity levels and immediate actions
- **PartNumber** -- part numbers with component names and ATA references
- **OperatingLimit** -- parameter limits per operating regime and aircraft type
- **MaintenanceTask** -- scheduled tasks with intervals and personnel requirements
- **ATAChapter** -- ATA chapter references

Entities are deduplicated across chunks and cross-linked to the operational graph (e.g. Sensor -[:HAS_LIMIT]-> OperatingLimit, MaintenanceEvent -[:CLASSIFIED_AS]-> FaultCode).
