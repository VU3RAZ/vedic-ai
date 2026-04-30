"""Parse and validate JSON output from the local LLM."""

from __future__ import annotations

import json
import re


def validate_llm_output(payload: dict, schema: dict) -> list[str]:
    """Validate a parsed LLM response dict against an expected schema.

    schema is a flat dict of {key: type_name_string}, e.g.
    {"summary": "str", "details": "list", "rule_refs": "list"}.

    Returns a list of human-readable error strings; empty list means valid.
    Unsupported keys (present in payload but absent from schema) are flagged.
    """
    if not schema:
        return []

    errors: list[str] = []
    type_map = {"str": str, "int": int, "float": float, "list": list, "dict": dict, "bool": bool}

    for key, expected_type_name in schema.items():
        if key not in payload:
            errors.append(f"Missing required key: '{key}'")
            continue
        expected_type = type_map.get(expected_type_name)
        if expected_type is not None and not isinstance(payload[key], expected_type):
            actual = type(payload[key]).__name__
            errors.append(
                f"Key '{key}': expected {expected_type_name}, got {actual}"
            )

    unsupported = [k for k in payload if k not in schema]
    for key in sorted(unsupported):
        errors.append(f"Unsupported key in output: '{key}'")

    return errors


def _extract_json_substring(text: str) -> str:
    """Find the first {...} or [...] block in text."""
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = text.find(start_char)
        if start == -1:
            continue
        # Walk backwards from end to find matching closer
        depth = 0
        for i, ch in enumerate(text[start:], start=start):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text


def repair_llm_output(raw_text: str, schema: dict) -> dict:
    """Attempt to extract and parse JSON from a potentially noisy LLM response.

    Strategies applied in order:
    1. Direct json.loads on stripped text.
    2. Extract the first JSON object/array substring and parse that.
    3. Strip markdown code fences and retry.

    Raises:
        ValueError: if all strategies fail.
    """
    text = raw_text.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract first JSON block
    candidate = _extract_json_substring(text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Strategy 3: strip markdown fences
    stripped = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Strategy 4: try extracted block from stripped text
    candidate2 = _extract_json_substring(stripped)
    try:
        return json.loads(candidate2)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Cannot repair LLM output as JSON. Raw text (first 200 chars): {text[:200]!r}")
