"""Entity extraction from maintenance manual chunks using LLM backends."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

from neo4j import Driver

# Labels for extracted entity nodes
EXTRACTED_LABELS = ["FaultCode", "PartNumber", "OperatingLimit", "MaintenanceTask", "ATAChapter"]

SYSTEM_PROMPT = (
    "You extract structured entities from aviation maintenance manuals. "
    "Always respond with valid JSON matching the requested schema. "
    "Only extract entities that are explicitly stated in the text. "
    "Return ONLY the JSON object — no markdown fences, no commentary, no extra text."
)

EXTRACTION_PROMPT = """\
Analyze this aircraft maintenance manual text and extract any structured entities.

Return a JSON object with these keys (use empty arrays [] for entity types not found):

{{
  "fault_codes": [
    {{
      "code": "e.g. ENG-OVH-001",
      "description": "brief description",
      "severity_levels": ["CRITICAL", "MAJOR", "MINOR"],
      "ata_chapter": "chapter number e.g. 72",
      "immediate_action": "recommended action"
    }}
  ],
  "part_numbers": [
    {{
      "number": "e.g. V25-FM-2100",
      "component_name": "component name",
      "ata_reference": "e.g. 72-01"
    }}
  ],
  "operating_limits": [
    {{
      "parameter": "e.g. EGT, N1, Vibration, System Pressure",
      "unit": "unit of measurement",
      "regime": "operating regime e.g. ground_idle, flight_idle, max_continuous, takeoff, normal, warning",
      "min_value": null,
      "max_value": null
    }}
  ],
  "maintenance_tasks": [
    {{
      "task_id": "e.g. ENG-TC-001 or null if not given",
      "description": "task description",
      "interval": 500,
      "interval_unit": "FH or months or days",
      "duration_hours": 1.0,
      "personnel_count": 1,
      "personnel_type": "mechanic or technician or specialist"
    }}
  ],
  "ata_chapters": [
    {{
      "chapter": "chapter number e.g. 72",
      "title": "system name e.g. Engine"
    }}
  ]
}}

TEXT:
{text}"""

EMPTY_RESULT: dict[str, list] = {
    "fault_codes": [],
    "part_numbers": [],
    "operating_limits": [],
    "maintenance_tasks": [],
    "ata_chapters": [],
}


# ---------------------------------------------------------------------------
# Neo4j reads
# ---------------------------------------------------------------------------


def fetch_chunks(
    driver: Driver,
    document_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch Chunk nodes with their parent document metadata.

    Args:
        document_id: If set, only fetch chunks for this document.
        limit: If set, return at most this many chunks.
    """
    where = ""
    params: dict[str, Any] = {}
    if document_id:
        where = "WHERE d.documentId = $docId"
        params["docId"] = document_id

    if limit:
        limit_clause = "LIMIT $limit"
        params["limit"] = int(limit)
    else:
        limit_clause = ""

    records, _, _ = driver.execute_query(
        f"""
        MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
        {where}
        RETURN c.documentId AS documentId, c.index AS chunkIndex,
               c.text AS text, d.aircraftType AS aircraftType
        ORDER BY c.documentId, c.index
        {limit_clause}
        """,
        **params,
    )
    return [dict(r) for r in records]


# ---------------------------------------------------------------------------
# LLM caller abstraction
# ---------------------------------------------------------------------------


class LLMCaller(Protocol):
    """Thin callable: (system_prompt, user_prompt) -> raw response text."""

    def __call__(self, system_prompt: str, user_prompt: str) -> str: ...


def _make_openai_caller(api_key: str, model: str) -> LLMCaller:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    def _call(system_prompt: str, user_prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return response.choices[0].message.content  # type: ignore[return-value]

    return _call  # type: ignore[return-value]


def _make_anthropic_caller(api_key: str, model: str) -> LLMCaller:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    def _call(system_prompt: str, user_prompt: str) -> str:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text  # type: ignore[union-attr]

    return _call  # type: ignore[return-value]


def make_llm_caller(provider: str, api_key: str, model: str) -> LLMCaller:
    """Public factory: return an LLMCaller for the given provider."""
    if provider == "openai":
        return _make_openai_caller(api_key, model)
    if provider == "anthropic":
        return _make_anthropic_caller(api_key, model)
    raise ValueError(f"Unknown LLM provider: {provider!r}")


# ---------------------------------------------------------------------------
# JSON response parsing
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


def _parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = content.strip()
    m = _FENCE_RE.match(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        from json_repair import repair_json

        return json.loads(repair_json(text))  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------


def extract_entities_from_chunk(
    llm_call: LLMCaller,
    text: str,
) -> dict[str, list[dict]]:
    """Call an LLM to extract structured entities from a single chunk."""
    try:
        content = llm_call(SYSTEM_PROMPT, EXTRACTION_PROMPT.format(text=text))
        result = _parse_json_response(content)
        for key in EMPTY_RESULT:
            if key not in result:
                result[key] = []
        return result
    except Exception as exc:
        print(f"\n    [WARN] Extraction failed: {exc}")
        return dict(EMPTY_RESULT)


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------


def _make_limit_id(parameter: str, regime: str, aircraft_type: str) -> str:
    parts = [parameter, regime, aircraft_type]
    return "_".join(p.strip().replace(" ", "_").lower() for p in parts if p.strip())


def _make_task_id(task_id: str | None, description: str) -> str:
    if task_id:
        return task_id.strip()
    return description[:60].strip().replace(" ", "_").lower()


def _collect_and_deduplicate(
    all_extractions: list[dict],
) -> dict[str, list[dict]]:
    """Merge and deduplicate entities extracted across all chunks."""
    fault_codes: dict[str, dict] = {}
    part_numbers: dict[str, dict] = {}
    operating_limits: dict[str, dict] = {}
    maintenance_tasks: dict[str, dict] = {}
    ata_chapters: dict[str, dict] = {}

    for extraction in all_extractions:
        doc_id = extraction["documentId"]
        chunk_idx = extraction["chunkIndex"]
        aircraft_type = extraction["aircraftType"]
        entities = extraction["entities"]
        source = {"documentId": doc_id, "chunkIndex": chunk_idx}

        # --- Fault codes ---
        for fc in entities.get("fault_codes", []):
            code = (fc.get("code") or "").strip()
            if not code:
                continue
            if code not in fault_codes:
                fault_codes[code] = {
                    "code": code,
                    "description": fc.get("description", ""),
                    "severity_levels": fc.get("severity_levels", []),
                    "ata_chapter": str(fc.get("ata_chapter", "")),
                    "immediate_action": fc.get("immediate_action", ""),
                    "sources": [source],
                }
            else:
                fault_codes[code]["sources"].append(source)
                if len(fc.get("description", "")) > len(fault_codes[code]["description"]):
                    fault_codes[code]["description"] = fc["description"]

        # --- Part numbers ---
        for pn in entities.get("part_numbers", []):
            number = (pn.get("number") or "").strip()
            if not number:
                continue
            if number not in part_numbers:
                part_numbers[number] = {
                    "number": number,
                    "component_name": pn.get("component_name", ""),
                    "ata_reference": pn.get("ata_reference", ""),
                    "sources": [source],
                }
            else:
                part_numbers[number]["sources"].append(source)

        # --- Operating limits ---
        for ol in entities.get("operating_limits", []):
            param = (ol.get("parameter") or "").strip()
            regime = (ol.get("regime") or "").strip()
            if not param or not regime:
                continue
            key = _make_limit_id(param, regime, aircraft_type)
            if key not in operating_limits:
                operating_limits[key] = {
                    "limitId": key,
                    "parameter": param,
                    "unit": ol.get("unit", ""),
                    "regime": regime,
                    "min_value": ol.get("min_value"),
                    "max_value": ol.get("max_value"),
                    "aircraftType": aircraft_type,
                    "sources": [source],
                }
            else:
                operating_limits[key]["sources"].append(source)
                # Keep non-null values from later chunks
                if ol.get("min_value") is not None:
                    operating_limits[key]["min_value"] = ol["min_value"]
                if ol.get("max_value") is not None:
                    operating_limits[key]["max_value"] = ol["max_value"]

        # --- Maintenance tasks ---
        for mt in entities.get("maintenance_tasks", []):
            desc = (mt.get("description") or "").strip()
            if not desc:
                continue
            tid = _make_task_id(mt.get("task_id"), desc)
            if tid not in maintenance_tasks:
                maintenance_tasks[tid] = {
                    "taskId": tid,
                    "description": desc,
                    "interval": mt.get("interval"),
                    "intervalUnit": mt.get("interval_unit", ""),
                    "durationHours": mt.get("duration_hours"),
                    "personnelCount": mt.get("personnel_count"),
                    "personnelType": mt.get("personnel_type", ""),
                    "sources": [source],
                }
            else:
                maintenance_tasks[tid]["sources"].append(source)

        # --- ATA chapters ---
        for ata in entities.get("ata_chapters", []):
            chapter = str(ata.get("chapter", "")).strip()
            if not chapter:
                continue
            if chapter not in ata_chapters:
                ata_chapters[chapter] = {
                    "chapter": chapter,
                    "title": ata.get("title", ""),
                    "sources": [source],
                }
            else:
                ata_chapters[chapter]["sources"].append(source)
                # Keep longer title
                if len(ata.get("title", "")) > len(ata_chapters[chapter]["title"]):
                    ata_chapters[chapter]["title"] = ata["title"]

    return {
        "fault_codes": list(fault_codes.values()),
        "part_numbers": list(part_numbers.values()),
        "operating_limits": list(operating_limits.values()),
        "maintenance_tasks": list(maintenance_tasks.values()),
        "ata_chapters": list(ata_chapters.values()),
    }


# ---------------------------------------------------------------------------
# Neo4j writes — one function per entity type
# ---------------------------------------------------------------------------


def _write_source_links(
    driver: Driver,
    match_clause: str,
    entities: list[dict],
    key_field: str,
) -> None:
    """Create DOCUMENTED_IN relationships from entities to their source Chunk nodes."""
    links = []
    for entity in entities:
        key_value = entity[key_field]
        for src in entity.get("sources", []):
            links.append({
                "key": key_value,
                "documentId": src["documentId"],
                "chunkIndex": src["chunkIndex"],
            })
    if not links:
        return
    query = f"""
        UNWIND $batch AS row
        {match_clause}
        MATCH (c:Chunk {{documentId: row.documentId, index: row.chunkIndex}})
        MERGE (entity)-[:DOCUMENTED_IN]->(c)
    """
    driver.execute_query(query, batch=links)


def _write_fault_codes(driver: Driver, fault_codes: list[dict]) -> int:
    if not fault_codes:
        return 0
    batch = [
        {
            "code": fc["code"],
            "description": fc.get("description", ""),
            "severityLevels": fc.get("severity_levels", []),
            "ataChapter": fc.get("ata_chapter", ""),
            "immediateAction": fc.get("immediate_action", ""),
        }
        for fc in fault_codes
    ]
    driver.execute_query("""
        UNWIND $batch AS row
        MERGE (fc:FaultCode {code: row.code})
        SET fc.description = row.description,
            fc.severityLevels = row.severityLevels,
            fc.ataChapter = row.ataChapter,
            fc.immediateAction = row.immediateAction
    """, batch=batch)
    _write_source_links(
        driver,
        "MATCH (entity:FaultCode {code: row.key})",
        fault_codes,
        "code",
    )
    return len(batch)


def _write_part_numbers(driver: Driver, part_numbers: list[dict]) -> int:
    if not part_numbers:
        return 0
    batch = [
        {
            "number": pn["number"],
            "componentName": pn.get("component_name", ""),
            "ataReference": pn.get("ata_reference", ""),
        }
        for pn in part_numbers
    ]
    driver.execute_query("""
        UNWIND $batch AS row
        MERGE (pn:PartNumber {number: row.number})
        SET pn.componentName = row.componentName,
            pn.ataReference = row.ataReference
    """, batch=batch)
    _write_source_links(
        driver,
        "MATCH (entity:PartNumber {number: row.key})",
        part_numbers,
        "number",
    )
    return len(batch)


def _write_operating_limits(driver: Driver, limits: list[dict]) -> int:
    if not limits:
        return 0
    batch = [
        {
            "limitId": ol["limitId"],
            "parameter": ol["parameter"],
            "unit": ol.get("unit", ""),
            "regime": ol["regime"],
            "minValue": ol.get("min_value"),
            "maxValue": ol.get("max_value"),
            "aircraftType": ol.get("aircraftType", ""),
        }
        for ol in limits
    ]
    driver.execute_query("""
        UNWIND $batch AS row
        MERGE (ol:OperatingLimit {limitId: row.limitId})
        SET ol.parameter = row.parameter,
            ol.unit = row.unit,
            ol.regime = row.regime,
            ol.minValue = row.minValue,
            ol.maxValue = row.maxValue,
            ol.aircraftType = row.aircraftType
    """, batch=batch)
    _write_source_links(
        driver,
        "MATCH (entity:OperatingLimit {limitId: row.key})",
        limits,
        "limitId",
    )
    return len(batch)


def _write_maintenance_tasks(driver: Driver, tasks: list[dict]) -> int:
    if not tasks:
        return 0
    batch = [
        {
            "taskId": mt["taskId"],
            "description": mt["description"],
            "interval": mt.get("interval"),
            "intervalUnit": mt.get("intervalUnit", ""),
            "durationHours": mt.get("durationHours"),
            "personnelCount": mt.get("personnelCount"),
            "personnelType": mt.get("personnelType", ""),
        }
        for mt in tasks
    ]
    driver.execute_query("""
        UNWIND $batch AS row
        MERGE (mt:MaintenanceTask {taskId: row.taskId})
        SET mt.description = row.description,
            mt.interval = row.interval,
            mt.intervalUnit = row.intervalUnit,
            mt.durationHours = row.durationHours,
            mt.personnelCount = row.personnelCount,
            mt.personnelType = row.personnelType
    """, batch=batch)
    _write_source_links(
        driver,
        "MATCH (entity:MaintenanceTask {taskId: row.key})",
        tasks,
        "taskId",
    )
    return len(batch)


def _write_ata_chapters(driver: Driver, chapters: list[dict]) -> int:
    if not chapters:
        return 0
    batch = [
        {
            "chapter": ata["chapter"],
            "title": ata.get("title", ""),
        }
        for ata in chapters
    ]
    driver.execute_query("""
        UNWIND $batch AS row
        MERGE (ata:ATAChapter {chapter: row.chapter})
        SET ata.title = row.title
    """, batch=batch)
    _write_source_links(
        driver,
        "MATCH (entity:ATAChapter {chapter: row.key})",
        chapters,
        "chapter",
    )
    return len(batch)


# ---------------------------------------------------------------------------
# Cross-links to existing operational graph
# ---------------------------------------------------------------------------


def _link_to_existing_graph(driver: Driver) -> None:
    """Create relationships between extracted entities and existing graph nodes."""

    # FaultCode -[:CLASSIFIED_UNDER]-> ATAChapter
    records, _, _ = driver.execute_query("""
        MATCH (fc:FaultCode) WHERE fc.ataChapter IS NOT NULL AND fc.ataChapter <> ''
        MATCH (ata:ATAChapter {chapter: fc.ataChapter})
        MERGE (fc)-[:CLASSIFIED_UNDER]->(ata)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} FaultCode -[:CLASSIFIED_UNDER]-> ATAChapter")

    # MaintenanceEvent -[:CLASSIFIED_AS]-> FaultCode
    records, _, _ = driver.execute_query("""
        MATCH (me:MaintenanceEvent) WHERE me.fault IS NOT NULL AND me.fault <> ''
        MATCH (fc:FaultCode {code: me.fault})
        MERGE (me)-[:CLASSIFIED_AS]->(fc)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} MaintenanceEvent -[:CLASSIFIED_AS]-> FaultCode")

    # PartNumber -[:CLASSIFIED_UNDER]-> ATAChapter
    records, _, _ = driver.execute_query("""
        MATCH (pn:PartNumber) WHERE pn.ataReference IS NOT NULL AND pn.ataReference <> ''
        WITH pn, split(pn.ataReference, '-')[0] AS chapter
        MATCH (ata:ATAChapter {chapter: chapter})
        MERGE (pn)-[:CLASSIFIED_UNDER]->(ata)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} PartNumber -[:CLASSIFIED_UNDER]-> ATAChapter")

    # Component -[:IDENTIFIED_BY]-> PartNumber (name match)
    records, _, _ = driver.execute_query("""
        MATCH (c:Component)
        MATCH (pn:PartNumber)
        WHERE toLower(c.name) = toLower(pn.componentName)
        MERGE (c)-[:IDENTIFIED_BY]->(pn)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} Component -[:IDENTIFIED_BY]-> PartNumber")

    # Sensor -[:HAS_LIMIT]-> OperatingLimit (match sensor type to parameter, scoped by aircraft model)
    records, _, _ = driver.execute_query("""
        MATCH (a:Aircraft)-[:HAS_SYSTEM]->(sys:System)-[:HAS_SENSOR]->(s:Sensor)
        MATCH (ol:OperatingLimit {parameter: s.type, aircraftType: a.model})
        MERGE (s)-[:HAS_LIMIT]->(ol)
        RETURN count(*) AS count
    """)
    print(f"  [OK] {records[0]['count']} Sensor -[:HAS_LIMIT]-> OperatingLimit")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def clear_extracted(driver: Driver) -> None:
    """Delete all extracted entity nodes (preserves operational graph and documents)."""
    print("Clearing extracted entity nodes...")
    deleted_total = 0
    for label in EXTRACTED_LABELS:
        while True:
            records, _, _ = driver.execute_query(
                f"MATCH (n:{label}) WITH n LIMIT 500 DETACH DELETE n RETURN count(*) AS deleted"
            )
            count = records[0]["deleted"]
            deleted_total += count
            if count == 0:
                break
    print(f"  [OK] Cleared {deleted_total} extracted entity nodes.")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_extraction(
    driver: Driver,
    llm_call: LLMCaller,
    model_name: str,
    limit: int | None = None,
    document_id: str | None = None,
) -> None:
    """Full extraction pipeline: fetch chunks → extract → deduplicate → write → link."""
    # 1. Fetch chunks
    filter_msg = ""
    if document_id:
        filter_msg += f" (document={document_id})"
    if limit:
        filter_msg += f" (limit={limit})"
    print(f"Fetching chunks from Neo4j...{filter_msg}")
    chunks = fetch_chunks(driver, document_id=document_id, limit=limit)
    print(f"  Found {len(chunks)} chunks across all documents.")
    if not chunks:
        print("  No chunks found. Run 'embed' command first.")
        return

    # 2. Extract entities from each chunk
    print(f"\nExtracting entities using {model_name}...")
    all_extractions: list[dict] = []
    total = len(chunks)

    for i, chunk in enumerate(chunks, 1):
        entities = extract_entities_from_chunk(llm_call, chunk["text"])
        all_extractions.append({
            "documentId": chunk["documentId"],
            "chunkIndex": chunk["chunkIndex"],
            "aircraftType": chunk["aircraftType"],
            "entities": entities,
        })
        entity_count = sum(len(v) for v in entities.values() if isinstance(v, list))
        print(f"  Chunk {i}/{total}: {entity_count} entities found", end="\r")
    print()

    # 3. Deduplicate
    print("\nDeduplicating entities...")
    deduplicated = _collect_and_deduplicate(all_extractions)
    for etype, entities in deduplicated.items():
        print(f"  {etype}: {len(entities)} unique")

    # 4. Write to Neo4j
    print("\nWriting entities to Neo4j...")
    n = _write_fault_codes(driver, deduplicated["fault_codes"])
    print(f"  [OK] {n} FaultCode nodes")

    n = _write_part_numbers(driver, deduplicated["part_numbers"])
    print(f"  [OK] {n} PartNumber nodes")

    n = _write_operating_limits(driver, deduplicated["operating_limits"])
    print(f"  [OK] {n} OperatingLimit nodes")

    n = _write_maintenance_tasks(driver, deduplicated["maintenance_tasks"])
    print(f"  [OK] {n} MaintenanceTask nodes")

    n = _write_ata_chapters(driver, deduplicated["ata_chapters"])
    print(f"  [OK] {n} ATAChapter nodes")

    # 5. Cross-link to existing graph
    print("\nLinking to existing graph...")
    _link_to_existing_graph(driver)
