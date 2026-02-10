# populate-aircraft-db

Standalone CLI tool that loads the Aircraft Digital Twin dataset into a Neo4j Aura instance. Handles the full pipeline: CSV data loading, and a single `enrich` command that uses `neo4j-graphrag`'s `SimpleKGPipeline` for maintenance manual chunking, OpenAI embedding generation, and LLM-powered entity extraction (OpenAI or Anthropic).

## Quick Start

```bash
cd lab_setup/populate_aircraft_db

# Create .env with your Neo4j credentials
cat > .env <<EOF
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
OPENAI_API_KEY=sk-...          # required for enrich (embeddings + extraction)
ANTHROPIC_API_KEY=sk-ant-...   # required for enrich (anthropic) only
LLM_PROVIDER=openai            # or "anthropic"
EOF

# Install and run
uv sync                              # OpenAI only
uv sync --extra anthropic            # include Anthropic support
uv run populate-aircraft-db load --clean
```

## Commands

| Command | Description |
|---------|-------------|
| `load [--clean]` | Load all nodes and relationships from CSV files |
| `enrich [--clean] [--chunk-size N] [--chunk-overlap N] [--provider NAME]` | Chunk maintenance manuals, generate embeddings, extract entities, and cross-link to operational graph (uses SimpleKGPipeline) |
| `verify` | Print node and relationship counts (read-only) |
| `clean` | Delete all nodes and relationships |

### Typical full-load sequence

```bash
uv run populate-aircraft-db load --clean
uv run populate-aircraft-db enrich                       # uses LLM_PROVIDER (default: openai)
uv run populate-aircraft-db enrich --provider anthropic  # override per-run
```

## Configuration

Settings are loaded from a `.env` file in the project root or from environment variables.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEO4J_URI` | yes | - | Connection URI (e.g. `neo4j+s://...`) |
| `NEO4J_USERNAME` | no | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | yes | - | Neo4j password |
| `OPENAI_API_KEY` | for enrich | - | OpenAI API key (always needed — embeddings use OpenAI) |
| `OPENAI_EMBEDDING_MODEL` | no | `text-embedding-3-small` | Embedding model |
| `OPENAI_EMBEDDING_DIMENSIONS` | no | `1536` | Embedding dimensions |
| `OPENAI_EXTRACTION_MODEL` | no | `gpt-4o-mini` | Chat model for entity extraction (OpenAI) |
| `LLM_PROVIDER` | no | `openai` | LLM provider for extraction: `openai` or `anthropic` |
| `ANTHROPIC_API_KEY` | for enrich (anthropic) | - | Anthropic API key |
| `ANTHROPIC_EXTRACTION_MODEL` | no | `claude-sonnet-4-5-20250929` | Chat model for entity extraction (Anthropic) |

## What Gets Loaded

### `load` -- Operational graph (from CSVs)

**9 node types:** Aircraft, System, Component, Sensor, Airport, Flight, Delay, MaintenanceEvent, Removal

**12 relationship types:** HAS_SYSTEM, HAS_COMPONENT, HAS_SENSOR, HAS_EVENT, OPERATES_FLIGHT, DEPARTS_FROM, ARRIVES_AT, HAS_DELAY, AFFECTS_SYSTEM, AFFECTS_AIRCRAFT, HAS_REMOVAL, REMOVED_COMPONENT

CSV files are read from `lab_setup/aircraft_digital_twin_data/`.

### `enrich` -- Document chunks, embeddings, and extracted entities

Uses `neo4j-graphrag`'s `SimpleKGPipeline` to process three maintenance manuals (A320-200, A321neo, B737-800):

1. **Chunking**: Splits text into ~800-character chunks with overlap
2. **Embedding**: Generates OpenAI embeddings stored on Chunk nodes
3. **Entity extraction**: Extracts five entity types using LLM:
   - **FaultCode** -- fault codes with severity levels and immediate actions
   - **PartNumber** -- part numbers with component names and ATA references
   - **OperatingLimit** -- parameter limits per operating regime and aircraft type
   - **MaintenanceTask** -- scheduled tasks with intervals and personnel requirements
   - **ATAChapter** -- ATA chapter references
4. **Entity resolution**: Deduplicates entities with matching `name` property (via APOC)
5. **Cross-linking**: Connects extracted entities to the operational graph (e.g. Sensor → OperatingLimit, MaintenanceEvent → FaultCode)

Creates indexes:
- **Vector index:** `maintenanceChunkEmbeddings` on `Chunk.embedding`
- **Fulltext index:** `maintenanceChunkText` on `Chunk.text`

**Note:** Entity resolution requires APOC, which is available on Neo4j Aura by default.
