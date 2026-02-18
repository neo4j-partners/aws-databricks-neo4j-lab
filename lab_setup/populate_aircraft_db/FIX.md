# Investigative Report: `enrich` Pipeline Errors

**Date:** 2026-02-17
**Run configuration:** `azure/gpt-5.2` LLM, Azure OpenAI embeddings (1536 dims)

---

## Error Summary

Three issues observed in the `enrich` command output:

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | `LLM response has improper format for chunk_index=16` | Low | Handled by `on_error="IGNORE"` |
| 2 | Neo4j warning: `__Entity__` label does not exist | Cosmetic | Benign — no fix needed |
| 3 | `Sensor -[:HAS_LIMIT]-> OperatingLimit: (none)` | **High** | Root cause identified |

---

## Issue 1: LLM Response Has Improper Format (chunk_index=16)

**What happened:** The `SimpleKGPipeline` sends each text chunk to the LLM for entity extraction. For chunk 16 of `MAINTENANCE_A320.md`, the LLM (`azure/gpt-5.2`) returned JSON that doesn't conform to the expected `Neo4jGraph` Pydantic schema (which expects `{"nodes": [...], "relationships": [...]}`).

**Why it happens:** The pipeline uses `on_error="IGNORE"` (`pipeline.py:180`), so malformed responses are silently skipped. The extraction falls back to the V1 prompt-based JSON path (no schema enforcement) because OpenAI/Azure models use `response_format: {"type": "json_object"}` which only guarantees valid JSON — not schema conformance. The LLM may return valid JSON with a wrong structure.

**Impact:** One chunk's entities are lost. With 43 chunks in the A320 manual, this is ~2.3% data loss. Most operating limits appear across multiple chunks, so the impact on final entity coverage is likely minimal.

**Fix status:** No code change needed. This is a transient LLM reliability issue. The `on_error="IGNORE"` strategy is the correct design. If this becomes frequent, see `FIX_GRAPHRAG_ANTHROPIC.md` for a discussion of structured output enforcement approaches.

---

## Issue 2: Neo4j Warning — `__Entity__` Label Does Not Exist

**What happened:** During the pipeline run, Neo4j emitted a `01N50` warning for the query `MATCH (entity:__Entity__) RETURN count(entity) as c`.

**Why it happens:** `SimpleKGPipeline` with `perform_entity_resolution=True` (`pipeline.py:181`) uses internal labels (`__Entity__`, `__KGBuilder__`) for bookkeeping during entity resolution. The pipeline queries for these labels as part of its resolution process. On a clean database (or at the start of processing), these labels don't exist yet, so Neo4j emits an informational warning. This is standard Neo4j behavior for queries referencing non-existent labels — the query returns 0 results, no error.

**Impact:** None. The warning is cosmetic. The entity resolution proceeds correctly.

**Fix status:** No fix needed. Suppressing Neo4j notifications would require driver-level configuration changes that aren't worth the complexity.

---

## Issue 3: `Sensor -[:HAS_LIMIT]-> OperatingLimit: (none)` — CRITICAL

### Root Cause

The cross-link query in `pipeline.py:278-283` requires an **exact match** on two properties:

```cypher
MATCH (a:Aircraft)-[:HAS_SYSTEM]->(sys:System)-[:HAS_SENSOR]->(s:Sensor)
MATCH (ol:OperatingLimit {parameterName: s.type, aircraftType: a.model})
MERGE (s)-[:HAS_LIMIT]->(ol)
```

This fails because the LLM (`azure/gpt-5.2`) extracts **engine type designations** as `aircraftType` instead of **aircraft model names**.

**Evidence from validation output:**

| OperatingLimit.name | parameterName | aircraftType (extracted) | Expected aircraftType |
|---|---|---|---|
| N1Speed - LEAP-1A | N1Speed | **LEAP-1A** | A321neo |
| EGT - LEAP-1A | EGT | **LEAP-1A** | A321neo |
| Oil Pressure - LEAP-1A | Oil Pressure | **LEAP-1A** | A321neo |
| Oil Temp - LEAP-1A | Oil Temp | **LEAP-1A** | A321neo |
| N2 - LEAP-1A | N2 | **LEAP-1A** | A321neo |

The LEAP-1A is the **engine type** for the A321neo (from `MAINTENANCE_A321neo.md`), not the aircraft model. The same issue likely affects the A320 manual (V2500-A1 instead of A320-200) and B737 manual (CFM56-7B instead of B737-800).

**Secondary mismatch — parameterName:** Some extracted `parameterName` values (`N2`, `Oil Pressure`, `Oil Temp`) don't match any `Sensor.type` values in the operational graph. The CSV sensors only have 4 types: `EGT`, `Vibration`, `N1Speed`, `FuelFlow`. Even if `aircraftType` matched, these parameters would never link.

### Why it worked before

The `sample_data.txt` file shows a previous successful run where entities had correct values (`EGT - A320-200`, `Vibration - B737-800`). That run likely used a different LLM model (OpenAI `gpt-5-mini` or similar) that followed the schema description more precisely. The `azure/gpt-5.2` model appears to interpret the manual's engine sections more literally, using the engine designation that dominates the text rather than the aircraft model mentioned in the document header.

### Contributing factors

1. **Schema description ambiguity** (`schema.py:144`): The `aircraftType` property description says `"Aircraft type, e.g. A320-200"` but the maintenance manuals prominently feature engine designations (LEAP-1A, V2500-A1, CFM56-7B) throughout, especially in the sections where operating limits are defined (Section 3: Engine System).

2. **Entity name pattern** (`schema.py:130-133`): The `name` property says `"Always append ' - <aircraft type>'"` with examples like `'EGT - A320-200'`. When the LLM uses engine types, the name becomes `'EGT - LEAP-1A'` which propagates the error to the `aircraftType` field.

3. **No document-level context injection**: The `document_metadata` (including `aircraftType: "A321neo"`) is stored on the `Document` node but is NOT injected into the LLM extraction prompt. The LLM only sees the chunk text, which is dominated by engine-specific terminology.

4. **Extra parameters beyond sensor types**: The manuals define operating limits for parameters (N2, Oil Pressure, Oil Temp) that don't exist as sensor types in the CSV data. This is a data model gap — not an LLM error — but it means extracted entities for these parameters can never cross-link.

### Implemented Fix: Custom Extraction Prompt + Document Context Header

**Status: IMPLEMENTED** in `pipeline.py`

Rather than hardcoding allowed values in schema descriptions (brittle, requires updates per manual), this fix uses a custom `prompt_template` that teaches the LLM **how to reason** about the domain. Two coordinated changes:

**1. Custom `EXTRACTION_PROMPT`** (`pipeline.py:100-153`)

Replaces the generic `ERExtractionTemplate` with a domain-aware prompt that:
- Sets the LLM's role as an aviation engineer (domain framing)
- Teaches aircraft type vs engine model disambiguation as a reasoning rule ("Engine models are components OF the aircraft, not the aircraft type itself")
- Instructs the LLM to read a `[DOCUMENT CONTEXT]` header for the aircraft type
- Guides `parameterName` toward concise sensor-style names from the document's own sensor tables
- Specifies the `name` format pattern (`<parameterName> - <aircraftType>`)
- Includes a concrete JSON example showing correct extraction
- Adds a quality filter: only extract when numeric limits are present

The prompt teaches *reasoning patterns* rather than enumerating values, so it generalizes to new manuals without updates.

**2. Document context header prepend** (`pipeline.py:321-328`)

Prepends `[DOCUMENT CONTEXT] Aircraft Type: {type} | Title: {title}` to the text before it enters the splitter. This ensures every chunk — even those deep in engine-specific sections — carries the aircraft type. The custom prompt tells the LLM to use this header.

```python
context_header = (
    f"[DOCUMENT CONTEXT] Aircraft Type: {meta.aircraft_type} | "
    f"Title: {meta.title}\n\n"
)
text = context_header + text
```

**Why this approach:**
- The prompt teaches reasoning, not memorization — works for any new aircraft type
- The context header solves the "lost metadata after chunking" problem
- No post-processing or Cypher cleanup needed if the LLM follows the prompt
- The `{schema}` dict (with property descriptions) still provides structural guidance
