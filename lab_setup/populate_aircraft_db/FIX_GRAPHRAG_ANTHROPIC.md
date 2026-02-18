# Fix: neo4j-graphrag AnthropicLLM Structured Output

**Problem:** When using `AnthropicLLM` with `SimpleKGPipeline`, entity extraction fails on some chunks with `LLM response has improper format`. The LLM returns JSON that doesn't match the expected `Neo4jGraph` Pydantic schema. Failed chunks are silently skipped (`on_error="IGNORE"`), leaving gaps in the knowledge graph.

**Root cause:** The `AnthropicLLM` class in neo4j-graphrag v1.13.0 does not support structured output. It sets `supports_structured_output = False` (inherited default) and raises `NotImplementedError` in both V2 invoke methods. The extraction pipeline falls back to V1 prompt-based JSON, which relies on the LLM voluntarily returning well-formed JSON — no enforcement.

By contrast, `OpenAILLM` sets `supports_structured_output = True` and uses `response_format: {"type": "json_schema", "strict": True}` to guarantee schema conformance.

**Affected code (neo4j-graphrag 1.13.0):**

- `neo4j_graphrag/llm/anthropic_llm.py:56` — `AnthropicLLM` class
  - Lines 219-222: `__invoke_v2` raises `NotImplementedError`
  - Lines 294-297: `__ainvoke_v2` raises `NotImplementedError`
- `neo4j_graphrag/llm/base.py:48` — `supports_structured_output: bool = False`
- `neo4j_graphrag/experimental/components/entity_relation_extractor.py:241-261` — V2 structured output path (never reached for Anthropic)
- `neo4j_graphrag/experimental/components/entity_relation_extractor.py:263-286` — V1 prompt-based fallback (current path, where errors occur)

---

## Anthropic's Recommended Approach: Tool Use for Structured Output

Anthropic does not have a `response_format` parameter like OpenAI. Instead, Anthropic [recommends using tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) to force structured JSON output:

1. Define a "tool" whose `input_schema` is the desired JSON schema (e.g., `Neo4jGraph`)
2. Set `tool_choice: {"type": "any"}` to force the model to call the tool
3. The tool call's `input` field contains the structured JSON, guaranteed to conform to the schema
4. With `strict: true` on the tool definition, Anthropic provides **guaranteed schema validation** ([Structured Outputs docs](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs))

This is a well-documented pattern — Anthropic has a dedicated [JSON Extractor cookbook](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#next-steps) example for exactly this use case.

---

## Proposed Fix: Implement V2 Structured Output in AnthropicLLM

### What needs to change

The `__invoke_v2` and `__ainvoke_v2` methods in `AnthropicLLM` should be implemented instead of raising `NotImplementedError`. When a `response_format` (Pydantic model or JSON schema dict) is provided, the method should:

1. Convert the Pydantic model to a JSON schema
2. Create a tool definition with that schema as `input_schema`
3. Call the Anthropic API with `tool_choice={"type": "any"}` to force tool use
4. Extract the structured JSON from the tool call result's `input` field
5. Return it as `LLMResponse.content` (serialized JSON string)

Additionally, set `supports_structured_output = True` on the class so the pipeline uses the V2 path.

### Pseudocode for `__ainvoke_v2`

```python
# In AnthropicLLM class:
supports_structured_output: bool = True  # Enable V2 path

@async_rate_limit_handler_decorator
async def __ainvoke_v2(
    self,
    input: List[LLMMessage],
    response_format: Optional[Union[Type[BaseModel], dict[str, Any]]] = None,
    **kwargs: Any,
) -> LLMResponse:
    system_instruction, messages = self.get_messages_v2(input)

    params = {**self.model_params, **kwargs}

    if response_format is not None:
        # Convert Pydantic model to JSON schema
        if isinstance(response_format, type) and issubclass(response_format, BaseModel):
            schema = response_format.model_json_schema()
            tool_name = response_format.__name__
        elif isinstance(response_format, dict):
            schema = response_format
            tool_name = "structured_output"
        else:
            raise ValueError(f"Unsupported response_format type: {type(response_format)}")

        # Define a tool whose input_schema IS the desired output schema
        tool = {
            "name": tool_name,
            "description": "Extract structured data matching the required schema.",
            "input_schema": schema,
            # "strict": True,  # Uncomment when Anthropic SDK supports it
        }

        response = await self.async_client.messages.create(
            model=self.model_name,
            system=system_instruction,
            messages=messages,
            tools=[tool],
            tool_choice={"type": "any"},  # Force tool use
            **params,
        )

        # Extract structured JSON from the tool call result
        for block in response.content:
            if block.type == "tool_use":
                import json
                return LLMResponse(content=json.dumps(block.input))

        raise LLMGenerationError("No tool_use block in Anthropic response")
    else:
        # No structured output requested — plain text response
        response = await self.async_client.messages.create(
            model=self.model_name,
            system=system_instruction,
            messages=messages,
            **params,
        )
        if response.content and len(response.content) > 0:
            return LLMResponse(content=response.content[0].text)
        raise LLMGenerationError("LLM returned empty response.")
```

### Where to implement this

**Option A: Upstream PR to neo4j-graphrag** (preferred long-term)

Submit a PR to [neo4j/neo4j-graphrag-python](https://github.com/neo4j/neo4j-graphrag-python) implementing the V2 methods. This benefits the entire community. The changes are isolated to `neo4j_graphrag/llm/anthropic_llm.py`.

**Option B: Local subclass in this project** (immediate fix)

Create a subclass in `populate_aircraft_db/pipeline.py` that overrides the V2 methods and sets `supports_structured_output = True`. Then use it in `_create_pipeline()` instead of the stock `AnthropicLLM`.

```python
class StructuredAnthropicLLM(AnthropicLLM):
    supports_structured_output = True

    async def ainvoke(self, input, response_format=None, **kwargs):
        if response_format is not None:
            # ... tool-use implementation as above ...
        return await super().ainvoke(input, **kwargs)
```

Then in `_create_pipeline()`:

```python
elif provider == "anthropic":
    llm = StructuredAnthropicLLM(  # Instead of AnthropicLLM
        model_name=llm_model,
        model_params={"max_tokens": 4096},
        api_key=anthropic_api_key,
    )
```

And enable structured output in `SimpleKGPipeline`:

```python
return SimpleKGPipeline(
    llm=llm,
    driver=driver,
    embedder=embedder,
    schema=schema,
    text_splitter=splitter,
    from_pdf=False,
    on_error="IGNORE",
    perform_entity_resolution=True,
    # Enable V2 structured output path:
    # (check if SimpleKGPipeline exposes this, or set it on the extractor directly)
)
```

---

## Pipeline Integration Detail

The `SimpleKGPipeline` creates an `LLMEntityRelationExtractor` internally. The extraction path is selected in `extract_for_chunk()` (entity_relation_extractor.py:230):

- **V2 path (line 241):** Used when `self.use_structured_output` is `True` AND `self.llm.supports_structured_output` is `True`. Calls `llm.ainvoke(messages, response_format=Neo4jGraph)`. Then validates with `Neo4jGraph.model_validate_json()`.

- **V1 path (line 263):** Current fallback for Anthropic. Calls `llm.ainvoke(prompt)` with no schema enforcement. Tries `json.loads()` + `fix_invalid_json()` + `Neo4jGraph.model_validate()`. Two failure points: invalid JSON, or valid JSON with wrong structure.

The `Neo4jGraph` schema (types.py:165) is straightforward:

```python
class Neo4jGraph(DataModel):
    nodes: list[Neo4jNode] = []          # id, label, properties, embedding_properties
    relationships: list[Neo4jRelationship] = []  # start_node_id, end_node_id, type, properties
```

This schema translates directly to a tool `input_schema` for the Anthropic tool-use approach.

---

## Additional Improvement: Retry Logic

Regardless of the structured output fix, adding retry logic for failed chunks would improve robustness. The `LLMEntityRelationExtractor.run_for_chunk()` method (line 318) has no retry — a single failure permanently skips the chunk.

A simple improvement would be a retry decorator (e.g., `tenacity`) on `extract_for_chunk()` that retries 1-2 times on `LLMGenerationError` or `ValidationError` before falling back to `Neo4jGraph()`.

---

## Summary

| Approach | Effort | Robustness | Scope |
|---|---|---|---|
| Upstream PR to neo4j-graphrag | Medium | Best — guaranteed schema via tool use | Benefits all users |
| Local `StructuredAnthropicLLM` subclass | Low | Best — same mechanism | This project only |
| Add retry logic (complementary) | Low | Good — handles transient failures | Either scope |
| Use OpenAI for extraction instead | None | Best — native JSON mode | Config change only |
