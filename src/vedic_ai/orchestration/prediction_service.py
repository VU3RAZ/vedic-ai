"""Prediction service: load rules, retrieve passages, call LLM."""

from __future__ import annotations

import logging
from pathlib import Path

from vedic_ai.core.rule_evaluator import evaluate_rules, resolve_rule_conflicts
from vedic_ai.core.rule_loader import load_rule_set
from vedic_ai.core.rules import RuleDefinition
from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.corpus import RetrievedPassage
from vedic_ai.domain.prediction import RuleTrigger
from vedic_ai.llm.output_parser import repair_llm_output, validate_llm_output
from vedic_ai.llm.prompt_builder import build_interpretation_prompt

logger = logging.getLogger(__name__)

_RULES_DIR = Path(__file__).parents[3] / "data" / "corpus" / "rules"

_OUTPUT_SCHEMA: dict = {
    "summary": "str",
    "details": "list",
    "rule_refs": "list",
    "passage_refs": "list",
}

_SCOPE_RULE_FILES: dict[str, str] = {
    "personality": "personality.yaml",
    "career": "career.yaml",
    "relationships": "relationships.yaml",
    "health": "health.yaml",
}


def load_rules_for_scope(scope: str, rules_dir: Path | None = None) -> list[RuleDefinition]:
    """Load rule definitions for the given scope from YAML.

    Falls back to an empty list if the scope has no rule file, so the pipeline
    can still run without crashing when rules are unavailable.
    """
    base = rules_dir or _RULES_DIR
    filename = _SCOPE_RULE_FILES.get(scope)
    if filename is None:
        logger.warning("No rule file registered for scope %r", scope)
        return []
    path = base / filename
    if not path.exists():
        logger.warning("Rule file not found: %s", path)
        return []
    return load_rule_set(str(path))


def evaluate_scope_rules(
    bundle: ChartBundle,
    features: dict,
    scope: str,
    rules_dir: Path | None = None,
) -> list[RuleTrigger]:
    """Load, evaluate, and resolve rules for a single scope."""
    rule_set = load_rules_for_scope(scope, rules_dir)
    raw_triggers = evaluate_rules(bundle, features, rule_set)
    scope_triggers = [t for t in raw_triggers if t.scope == scope]
    resolved = resolve_rule_conflicts(scope_triggers)
    logger.debug("Scope %r: %d rules loaded, %d triggered", scope, len(rule_set), len(resolved))
    return resolved


def call_llm_for_interpretation(
    bundle: ChartBundle,
    features: dict,
    triggers: list[RuleTrigger],
    passages: list[RetrievedPassage],
    scope: str,
    llm_client: object,
    *,
    raman_method: bool = False,
) -> dict:
    """Build the prompt, call the LLM, parse and validate the response.

    llm_client must implement the LLMClient protocol (generate method).
    Returns a dict with at minimum 'summary' and 'details' keys.
    On parse failure, falls back to repair_llm_output.
    On repeated failure, returns a minimal fallback dict.
    """
    prompt = build_interpretation_prompt(
        bundle=bundle,
        features=features,
        triggers=triggers,
        passages=passages,
        scope=scope,
        output_schema=_OUTPUT_SCHEMA,
        raman_method=raman_method,
    )
    logger.debug("Sending prompt to LLM (%d chars)", len(prompt))

    raw = llm_client.generate(prompt)
    logger.debug("LLM raw response (%d chars)", len(raw))

    try:
        import json
        from vedic_ai.llm.output_parser import _unwrap_if_list, _strip_think_tags, _normalize_details
        payload = _normalize_details(_unwrap_if_list(json.loads(_strip_think_tags(raw))))
    except Exception:
        payload = repair_llm_output(raw, _OUTPUT_SCHEMA)

    if not isinstance(payload, dict):
        logger.warning("LLM returned non-dict payload (%s); falling back to empty", type(payload).__name__)
        payload = {"summary": str(payload), "details": [], "rule_refs": [], "passage_refs": []}

    errors = validate_llm_output(payload, _OUTPUT_SCHEMA)
    if errors:
        logger.warning("LLM output validation errors: %s", errors)

    return payload
