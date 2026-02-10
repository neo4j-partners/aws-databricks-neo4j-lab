# Proposal: Additional Entity Extraction

The current `enrich` pipeline only extracts **OperatingLimit** nodes from the maintenance manuals. The manuals contain significantly more structured data that could cross-link to the operational graph and improve agent question-answering.

## Proposed New Entity Types

### 1. FaultCode (high value)

Every manual has fault code tables (Section 7) and detailed troubleshooting sections (Section 4) with structured codes, severity levels, and ATA chapter references.

**Example data in manuals:**
- `ENG-OVH-001` — Overheat Condition, CRITICAL/MAJOR/MINOR, ATA 72
- `ENG-VIB-002` (A320) / `ENG-VIB-001` (A321neo) — Vibration Exceedance
- `ENG-SDR-001` (B737) — Sensor Drift

**Schema properties:** `name`, `code`, `description`, `severity`, `ataChapter`, `immediateAction`, `aircraftType`

**Cross-links to operational graph:**
- `MaintenanceEvent -[:MATCHES_FAULT]-> FaultCode` — match on `MaintenanceEvent.fault` containing the fault description
- `FaultCode -[:AFFECTS_SYSTEM_TYPE]-> System` — match on ATA chapter to system type

**Demo value:** An agent could answer *"What's the troubleshooting procedure for this maintenance event?"* by traversing from a MaintenanceEvent to its matching FaultCode, then to the source Chunk for the full procedure text.

### 2. MaintenanceTask (high value)

Section 9 of each manual has inspection schedule tables with task names, intervals, durations, and personnel requirements.

**Example data in manuals:**
- Fan blade visual inspection — 500 FH, 1.0 hr, 1 mechanic (A320)
- Borescope - HPT — 2,500 FH, 3.0 hr, 1 specialist (A320)
- Composite fan blade inspection — 750 FH, 1.0 hr (A321neo)
- Oil filter inspection — 500 FH (B737)

**Schema properties:** `name`, `intervalFH`, `intervalCalendar`, `durationHrs`, `personnelCount`, `systemType`, `aircraftType`

**Cross-links to operational graph:**
- `Component -[:REQUIRES_TASK]-> MaintenanceTask` — match on component/system type
- `MaintenanceTask -[:FROM_CHUNK]-> Chunk` — provenance (automatic via SimpleKGPipeline)

**Demo value:** An agent could answer *"What inspections are due for aircraft AC1002's engine components?"* by traversing Aircraft -> System -> Component -> MaintenanceTask.

### 3. SeverityThreshold (medium value)

Each fault code section defines specific numeric thresholds that determine severity classification per aircraft type.

**Example data in manuals:**
- A320 EGT: CRITICAL > 695°C, MAJOR 650-680°C, MINOR trending high
- A321neo Vibration: CRITICAL > 4.0 ips (N1), WARNING 3.0-4.0 ips, CAUTION 2.0-3.0 ips
- B737 Sensor Drift: CRITICAL > 10%, MAJOR 5-10%, MINOR < 5%

**Schema properties:** `name`, `parameterName`, `severityLevel`, `minValue`, `maxValue`, `unit`, `action`, `aircraftType`

**Cross-links to operational graph:**
- `Sensor -[:HAS_THRESHOLD]-> SeverityThreshold` — match on parameterName + aircraftType (same pattern as OperatingLimit)

**Demo value:** Complements OperatingLimit by adding severity-graded thresholds. An agent could answer *"Is this EGT reading critical or just a caution?"*

### 4. ComponentSpec (medium value)

Section 3 of each manual lists components with part numbers, ATA references, and descriptions.

**Example data in manuals:**
- Fan Module: V25-FM-2100, ATA 72-21 (A320)
- Fan Module: LEAP-FM-1A32-100, ATA 72-21 (A321neo)
- Fan Module: CFM-FM-7B26-100, ATA 72-21 (B737)

**Schema properties:** `name`, `partNumber`, `ataReference`, `componentType`, `aircraftType`

**Cross-links to operational graph:**
- `Component -[:HAS_SPEC]-> ComponentSpec` — match on component type + aircraft model

**Demo value:** An agent could answer *"What's the part number for the HPT on the A321neo?"*

## Implementation Priority

| Entity Type | Cross-link value | Extraction reliability | Effort |
|---|---|---|---|
| **FaultCode** | High — links to MaintenanceEvent | High — structured tables | Low — add to schema |
| **MaintenanceTask** | High — links to Component/System | High — structured tables | Low — add to schema |
| **SeverityThreshold** | Medium — extends OperatingLimit | Medium — scattered in prose | Medium |
| **ComponentSpec** | Medium — links to Component | High — structured tables | Low — add to schema |

## Suggested First Step

Add **FaultCode** and **MaintenanceTask** to `schema.py:build_extraction_schema()` and the corresponding cross-link Cypher to `pipeline.py:link_to_existing_graph()`. These two entity types have the highest demo value because they create new traversal paths from the operational graph (MaintenanceEvent, Component) into the knowledge graph.

---

# Known Data Mismatches

## Sensor Type vs Manual Parameter Names

**Status: FIXED** — Manuals updated to use CSV sensor type names consistently.

| CSV Sensor `type` | Manual parameter name | Match? |
|---|---|---|
| `EGT` | EGT | exact |
| `Vibration` | Vibration | exact |
| `N1Speed` | N1Speed | exact |
| `FuelFlow` | FuelFlow | exact |
