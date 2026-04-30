# Prompting

Design contract for the prompt builder (Phase 6). Defines the required sections, ordering, and formatting rules so prompts are deterministic for fixed inputs.

## Prompt structure

Every interpretation prompt has five ordered sections, each delimited by a markdown header.

```
## Chart Facts
## Derived Features
## Triggered Rules
## Supporting Passages
## Task
```

### 1. Chart Facts

Serialized subset of `ChartBundle` relevant to the requested scope. Includes:
- Lagna sign and degree
- All 9 graha placements (sign, house, longitude)
- All 12 house cusps
- Active dasha (Mahadasha / Antardasha) if available

Format: compact JSON block.

### 2. Derived Features

Key entries from the feature dict for the requested scope:
- Planet dignities and whether each is exalted, own, debilitated
- House lordships for the scope-relevant houses (e.g. 7th and its lord for relationships)
- Active yogas
- Relevant aspects

Format: compact JSON block.

### 3. Triggered Rules

The `list[RuleTrigger]` after `resolve_rule_conflicts()`, rendered as a structured list:

```
- [C001] Sun in 10th House — Career Prominence (weight: 0.75)
  Evidence: planets.Sun.house = 10
  Source: BPHS 24.5
```

### 4. Supporting Passages

`list[RetrievedPassage]` from the retriever, rendered as numbered excerpts with source citations:

```
[1] BPHS 24.5 — "Sun placed in the 10th house of karma bhava…"
[2] Phaladeepika 7.12 — "…"
```

Top-k defaults to 5. The retriever query is built from the triggered rule names and scope.

### 5. Task

Fixed instruction block:

```
You are a Jyotish interpreter. Generate a {scope} analysis grounded strictly in
the triggered rules and supporting passages above.

- Use only the rules and passages provided. Do not introduce claims unsupported
  by the evidence above.
- Reference rule IDs (e.g. [C001]) and passage numbers (e.g. [1]) inline.
- Return a JSON object matching the output schema below.

Output schema:
{output_schema_json}
```

## Output schema

```json
{
  "scope": "career",
  "summary": "string (2–4 sentences)",
  "sections": [
    {
      "heading": "string",
      "body": "string",
      "rule_refs": ["C001", "C003"],
      "passage_refs": [1, 2]
    }
  ],
  "caveats": ["string"],
  "unsupported_claims": []
}
```

`unsupported_claims` must be an empty array. If the LLM cannot ground a claim, it should add a caveat instead.

## Determinism requirement

For fixed inputs `(ChartBundle, features, triggers, passages, scope)` the prompt must be byte-for-byte identical. This means:
- Features and triggers are sorted by a stable key before rendering.
- Retrieved passages are sorted by descending relevance score, ties broken by `chunk_id`.
- JSON serialization uses `sort_keys=True` and no trailing whitespace.

## Temperature and generation settings

| Parameter     | Value  | Rationale |
|---------------|--------|-----------|
| `temperature` | 0.2    | Low variance; factual grounding task |
| `top_p`       | 0.9    | Default |
| `max_tokens`  | 1024   | Sufficient for 3-scope analysis |

## Repair policy

If the model returns malformed JSON, `repair_llm_output()` attempts:
1. Trim leading/trailing text outside the outermost `{…}`.
2. Parse with `json5` for lenient parsing.
3. Validate against the output schema.

If repair fails, the pipeline raises `EngineError` with the raw response attached; it does not silently return empty output.

## Unsupported-claim detection

Post-generation, `validate_llm_output()` checks that every `rule_ref` in `sections` exists in the triggered rule IDs, and every `passage_ref` exists in the passage list. Orphaned references are logged as warnings and the section is flagged.
