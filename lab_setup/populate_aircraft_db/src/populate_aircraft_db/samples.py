"""Sample queries showcasing the Aircraft Digital Twin knowledge graph."""

from __future__ import annotations

from neo4j import Driver

_W = 70
_EXTRACTED_LABELS = ["FaultCode", "PartNumber", "OperatingLimit", "MaintenanceTask", "ATAChapter"]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _header(title: str, description: str) -> None:
    print(f"\n{'=' * _W}")
    print(f"  {title}")
    print(f"{'=' * _W}")
    print(f"\n  {description}\n")


def _cypher(query: str) -> None:
    lines = query.strip().splitlines()
    indents = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    base = min(indents) if indents else 0
    print("  Cypher:")
    for ln in lines:
        print(f"    {ln[base:]}")
    print()


def _table(headers: list[str], rows: list[list], widths: list[int] | None = None) -> None:
    if not rows:
        print("  (no results)\n")
        return
    if widths is None:
        widths = []
        for i, h in enumerate(headers):
            col_max = len(h)
            for row in rows:
                col_max = max(col_max, len(str(row[i] if i < len(row) else "")))
            widths.append(min(col_max + 1, 50))
    print("  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  " + "  ".join("\u2500" * w for w in widths))
    for row in rows:
        cells = []
        for val, w in zip(row, widths):
            s = str(val) if val is not None else "\u2014"
            if len(s) > w:
                s = s[: w - 1] + "\u2026"
            cells.append(s.ljust(w))
        print("  " + "  ".join(cells))
    print()


def _val(v, max_len: int = 0) -> str:
    s = str(v) if v is not None else "\u2014"
    if max_len and len(s) > max_len:
        s = s[: max_len - 1] + "\u2026"
    return s


# ---------------------------------------------------------------------------
# 1. Aircraft Fleet
# ---------------------------------------------------------------------------

_FLEET_Q = """\
MATCH (a:Aircraft)
OPTIONAL MATCH (a)-[:HAS_SYSTEM]->(s:System)
OPTIONAL MATCH (s)-[:HAS_COMPONENT]->(c:Component)
WITH a, count(DISTINCT s) AS systems, count(DISTINCT c) AS components
RETURN a.tail_number AS tail, a.model AS model,
       a.manufacturer AS mfr, systems, components
ORDER BY a.tail_number"""


def _aircraft_fleet(driver: Driver) -> None:
    _header(
        "1. Aircraft Fleet Overview",
        "Each aircraft with its model, manufacturer, and system/component counts.",
    )
    _cypher(_FLEET_Q)
    rows, _, _ = driver.execute_query(_FLEET_Q)
    _table(
        ["Tail #", "Model", "Manufacturer", "Systems", "Components"],
        [[r["tail"], r["model"], r["mfr"], r["systems"], r["components"]] for r in rows],
    )


# ---------------------------------------------------------------------------
# 2. System-Component hierarchy
# ---------------------------------------------------------------------------

_HIERARCHY_Q = """\
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(s:System)-[:HAS_COMPONENT]->(c:Component)
WITH a, s, c ORDER BY s.name, c.name
WITH a, s, collect(c.name) AS comps ORDER BY s.name
WITH a, collect({system: s.name, components: comps}) AS systems
RETURN a.tail_number AS tail, a.model AS model, systems
LIMIT 1"""


def _system_hierarchy(driver: Driver) -> None:
    _header(
        "2. System \u2192 Component Hierarchy",
        "Full hierarchy for one aircraft showing Systems and their Components.",
    )
    _cypher(_HIERARCHY_Q)
    rows, _, _ = driver.execute_query(_HIERARCHY_Q)
    if not rows:
        print("  (no results)\n")
        return
    r = rows[0]
    print(f"  Aircraft {r['tail']} ({r['model']})")
    systems = r["systems"]
    for i, sys in enumerate(systems):
        last_sys = i == len(systems) - 1
        print(f"  {'└── ' if last_sys else '├── '}{sys['system']}")
        for j, comp in enumerate(sys["components"]):
            branch = "    " if last_sys else "│   "
            leaf = "└── " if j == len(sys["components"]) - 1 else "├── "
            print(f"  {branch}{leaf}{comp}")
    print()


# ---------------------------------------------------------------------------
# 3. Flight network
# ---------------------------------------------------------------------------

_FLIGHTS_Q = """\
MATCH (f:Flight)-[:DEPARTS_FROM]->(dep:Airport),
      (f)-[:ARRIVES_AT]->(arr:Airport)
WITH dep.code AS origin, arr.code AS dest, count(f) AS flights
RETURN origin, dest, flights
ORDER BY flights DESC
LIMIT 10"""


def _flight_operations(driver: Driver) -> None:
    _header(
        "3. Flight Operations \u2014 Top Routes",
        "Most frequent routes by flight count.",
    )
    _cypher(_FLIGHTS_Q)
    rows, _, _ = driver.execute_query(_FLIGHTS_Q)
    _table(
        ["Origin", "Dest", "Flights"],
        [[r["origin"], r["dest"], r["flights"]] for r in rows],
    )


# ---------------------------------------------------------------------------
# 4. Maintenance events
# ---------------------------------------------------------------------------

_MAINT_Q = """\
MATCH (a:Aircraft)-[:HAS_EVENT]->(me:MaintenanceEvent)
OPTIONAL MATCH (me)-[:AFFECTS_SYSTEM]->(s:System)
RETURN a.tail_number AS aircraft, me.event_id AS event,
       me.date AS date, me.type AS type, me.fault AS fault,
       s.name AS system
ORDER BY me.date DESC
LIMIT 10"""


def _maintenance_events(driver: Driver) -> None:
    _header(
        "4. Maintenance Events",
        "Recent maintenance events with fault codes and affected systems.",
    )
    _cypher(_MAINT_Q)
    rows, _, _ = driver.execute_query(_MAINT_Q)
    _table(
        ["Aircraft", "Event ID", "Date", "Type", "Fault", "System"],
        [
            [
                r["aircraft"],
                r["event"],
                _val(r["date"])[:10],
                r["type"],
                _val(r["fault"], 20),
                _val(r["system"]),
            ]
            for r in rows
        ],
    )


# ---------------------------------------------------------------------------
# 5. Sensors and readings
# ---------------------------------------------------------------------------

_SENSORS_Q = """\
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(sys:System)-[:HAS_SENSOR]->(s:Sensor)
RETURN a.tail_number AS aircraft, sys.name AS system,
       s.sensor_id AS sensor, s.type AS type, s.unit AS unit
ORDER BY a.tail_number, sys.name
LIMIT 12"""


def _sensors(driver: Driver) -> None:
    _header(
        "5. Sensors",
        "Sensors installed across the fleet with their type and unit.",
    )
    _cypher(_SENSORS_Q)
    rows, _, _ = driver.execute_query(_SENSORS_Q)
    _table(
        ["Aircraft", "System", "Sensor ID", "Type", "Unit"],
        [[r["aircraft"], r["system"], r["sensor"], r["type"], r["unit"]] for r in rows],
    )


# ---------------------------------------------------------------------------
# 6. Document-Chunk structure
# ---------------------------------------------------------------------------

_DOCS_Q = """\
MATCH (d:Document)
OPTIONAL MATCH (d)<-[:FROM_DOCUMENT]-(c:Chunk)
WITH d, count(c) AS chunks,
     sum(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded
RETURN d.documentId AS doc_id, d.aircraftType AS aircraft,
       d.title AS title, chunks, embedded
ORDER BY d.documentId"""

_CHAIN_Q = """\
MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
WITH d, c ORDER BY d.documentId, c.index
WITH d, c LIMIT 5
OPTIONAL MATCH (c)-[:NEXT_CHUNK]->(next:Chunk)
RETURN d.documentId AS doc, c.index AS idx,
       substring(c.text, 0, 60) AS preview,
       next.index AS next_idx"""


def _document_chunks(driver: Driver) -> None:
    _header(
        "6. Document-Chunk Structure",
        "Maintenance manuals loaded as Document \u2192 Chunk graphs with embedding stats.",
    )
    _cypher(_DOCS_Q)
    rows, _, _ = driver.execute_query(_DOCS_Q)
    if not rows:
        print("  (no documents \u2014 run 'enrich' first)\n")
        return
    _table(
        ["Document ID", "Aircraft", "Chunks", "Embedded"],
        [[r["doc_id"], r["aircraft"], r["chunks"], r["embedded"]] for r in rows],
    )

    print("  Chunk chain (first 5):\n")
    _cypher(_CHAIN_Q)
    rows, _, _ = driver.execute_query(_CHAIN_Q)
    for r in rows:
        arrow = f" \u2192 Chunk {r['next_idx']}" if r["next_idx"] is not None else " (end)"
        print(f"    Chunk {r['idx']:>3} \u2502 {r['preview']}\u2026{arrow}")
    print()


# ---------------------------------------------------------------------------
# 7. Extracted entities
# ---------------------------------------------------------------------------

_ENTITIES_Q = """\
UNWIND $labels AS label
CALL (label) {
    MATCH (n) WHERE label IN labels(n)
    RETURN n.name AS name
    LIMIT 5
}
RETURN label AS entity_type, collect(name) AS samples"""


def _extracted_entities(driver: Driver) -> None:
    _header(
        "7. Extracted Entities",
        "Entity types extracted from maintenance manuals via SimpleKGPipeline.",
    )
    _cypher(_ENTITIES_Q)
    rows, _, _ = driver.execute_query(_ENTITIES_Q, labels=_EXTRACTED_LABELS)
    if not rows or all(len(r["samples"]) == 0 for r in rows):
        print("  (no extracted entities \u2014 run 'enrich' first)\n")
        return
    for r in rows:
        names = r["samples"]
        if names:
            print(f"  {r['entity_type']}:")
            for name in names:
                print(f"    \u2022 {name}")
        else:
            print(f"  {r['entity_type']}: (none)")
    print()


# ---------------------------------------------------------------------------
# 8. Cross-links
# ---------------------------------------------------------------------------

_CROSSLINKS = [
    (
        "FaultCode \u2192 ATAChapter",
        """\
MATCH (fc:FaultCode)-[:CLASSIFIED_UNDER]->(ata:ATAChapter)
RETURN fc.name AS source, ata.name AS target
LIMIT 5""",
        ["FaultCode", "ATAChapter"],
    ),
    (
        "MaintenanceEvent \u2192 FaultCode",
        """\
MATCH (me:MaintenanceEvent)-[:CLASSIFIED_AS]->(fc:FaultCode)
RETURN me.event_id AS source, fc.name AS target
LIMIT 5""",
        ["Event ID", "FaultCode"],
    ),
    (
        "Component \u2192 PartNumber",
        """\
MATCH (c:Component)-[:IDENTIFIED_BY]->(pn:PartNumber)
RETURN c.name AS source, pn.name AS target
LIMIT 5""",
        ["Component", "PartNumber"],
    ),
    (
        "Sensor \u2192 OperatingLimit",
        """\
MATCH (s:Sensor)-[:HAS_LIMIT]->(ol:OperatingLimit)
RETURN s.sensor_id AS source, s.type AS type, ol.name AS target
LIMIT 5""",
        ["Sensor", "Type", "OperatingLimit"],
    ),
]


def _cross_links(driver: Driver) -> None:
    _header(
        "8. Cross-Links: Knowledge Graph \u2194 Operational Graph",
        "Relationships connecting extracted entities to the operational aircraft graph.",
    )
    any_results = False
    for title, query, headers in _CROSSLINKS:
        print(f"  {title}:")
        _cypher(query)
        rows, _, _ = driver.execute_query(query)
        if not rows:
            print("  (none)\n")
            continue
        any_results = True
        if len(headers) == 2:
            _table(headers, [[r["source"], r["target"]] for r in rows])
        else:
            _table(headers, [[r["source"], r["type"], r["target"]] for r in rows])
    if not any_results:
        print("  (no cross-links \u2014 run 'enrich' first)\n")


# ---------------------------------------------------------------------------
# 9. Vector similarity search (no API key needed)
# ---------------------------------------------------------------------------

_VECTOR_Q = """\
MATCH (seed:Chunk)
WHERE seed.embedding IS NOT NULL
WITH seed, rand() AS r ORDER BY r LIMIT 1
CALL db.index.vector.queryNodes(
    'maintenanceChunkEmbeddings', 6, seed.embedding
) YIELD node, score
WHERE node <> seed
WITH seed, node, score ORDER BY score DESC LIMIT 5
RETURN substring(seed.text, 0, 100) AS seed_text,
       score AS similarity,
       substring(node.text, 0, 100) AS match_text"""


def _vector_similarity(driver: Driver) -> None:
    _header(
        "9. Vector Similarity Search",
        "Picks a random chunk and finds the 5 most similar chunks using the\n"
        "  vector index (reuses stored embeddings \u2014 no API key needed).",
    )
    _cypher(_VECTOR_Q)
    try:
        rows, _, _ = driver.execute_query(_VECTOR_Q)
    except Exception:
        print("  (vector index not available \u2014 run 'enrich' first)\n")
        return
    if not rows:
        print("  (no chunks with embeddings \u2014 run 'enrich' first)\n")
        return
    print(f"  Seed: \"{rows[0]['seed_text']}\u2026\"\n")
    print(f"  {'Score':<8}  Similar chunk")
    print(f"  {'\u2500' * 8}  {'\u2500' * 56}")
    for r in rows:
        print(f"  {r['similarity']:.4f}    {r['match_text']}\u2026")
    print()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_all_samples(driver: Driver) -> None:
    """Run all sample queries with formatted output."""
    print(f"\n{'#' * _W}")
    print("  Aircraft Digital Twin \u2014 Sample Queries")
    print(f"{'#' * _W}")

    _aircraft_fleet(driver)
    _system_hierarchy(driver)
    _flight_operations(driver)
    _maintenance_events(driver)
    _sensors(driver)
    _document_chunks(driver)
    _extracted_entities(driver)
    _cross_links(driver)
    _vector_similarity(driver)

    print(f"{'#' * _W}")
    print("  All samples complete.")
    print(f"{'#' * _W}\n")
