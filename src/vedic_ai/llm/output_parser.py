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

    if not isinstance(payload, dict):
        return [f"Expected a JSON object, got {type(payload).__name__}"]

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


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models (e.g. DeepSeek, Qwen3)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json_substring(text: str) -> str:
    """Find the first {...} or [...] block in text."""
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start=start):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text


def _unwrap_if_list(parsed: object) -> dict:
    """If the LLM returned a JSON array, unwrap the first element."""
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed[0]
    return parsed  # type: ignore[return-value]


def _normalize_details(payload: object) -> dict:
    """Coerce details items from dicts/other types to plain strings. Returns payload unchanged if not a dict."""
    if not isinstance(payload, dict):
        return payload  # type: ignore[return-value]
    details = payload.get("details")
    if isinstance(details, list):
        payload["details"] = [
            item if isinstance(item, str)
            else (item.get("description") or item.get("text") or item.get("detail")
                  or ", ".join(f"{k}: {v}" for k, v in item.items()))
            if isinstance(item, dict)
            else str(item)
            for item in details
        ]
    return payload


def _try_close_truncated_json(text: str) -> str:
    """Append closing brackets/braces to complete a truncated JSON string."""
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    if not stack and not in_string:
        return text
    # Strip trailing incomplete token (comma, colon, whitespace)
    trimmed = re.sub(r'[,:\s]*$', '', text)
    # Close an unclosed string value before closing containers
    if in_string:
        trimmed += '"'
    return trimmed + "".join(reversed(stack))


def repair_llm_output(raw_text: str, schema: dict) -> dict:
    """Attempt to extract and parse JSON from a potentially noisy LLM response.

    Strategies applied in order:
    1. Strip <think> tags, then direct json.loads.
    2. Extract the first JSON object/array substring and parse that.
    3. Strip markdown code fences and retry.
    4. Extract JSON block from de-fenced text.

    Raises:
        ValueError: if all strategies fail.
    """
    text = _strip_think_tags(raw_text.strip())

    def _try(raw: str) -> dict | None:
        try:
            result = _normalize_details(_unwrap_if_list(json.loads(raw)))
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None

    # Strategy 1: direct parse (after stripping think tags)
    if (r := _try(text)) is not None:
        return r

    # Strategy 2: extract first JSON block
    candidate = _extract_json_substring(text)
    if (r := _try(candidate)) is not None:
        return r

    # Strategy 3: strip markdown fences
    stripped = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    if (r := _try(stripped)) is not None:
        return r

    # Strategy 4: extract JSON block from de-fenced text
    candidate2 = _extract_json_substring(stripped)
    if (r := _try(candidate2)) is not None:
        return r

    # Strategy 5: try to close a truncated JSON block
    for raw_trunc in (candidate, candidate2, text, stripped):
        closed = _try_close_truncated_json(raw_trunc)
        if closed != raw_trunc:
            if (r := _try(closed)) is not None:
                return r

    raise ValueError(f"Cannot repair LLM output as JSON. Raw text (first 200 chars): {text[:200]!r}")
