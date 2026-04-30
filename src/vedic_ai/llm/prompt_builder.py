"""Build deterministic prompts for the local LLM interpretation call."""

from __future__ import annotations

import json

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.corpus import RetrievedPassage
from vedic_ai.domain.prediction import RuleTrigger

# Section header tokens — fixed order for snapshot stability
_SECTION_CHART_FACTS = "### CHART FACTS"
_SECTION_DERIVED = "### DERIVED FEATURES"
_SECTION_RULES = "### TRIGGERED RULES"
_SECTION_PASSAGES = "### SUPPORTING PASSAGES"
_SECTION_TASK = "### TASK"

_INSTRUCTION = (
    "You are a Vedic astrology analyst. "
    "Respond ONLY with a valid JSON object matching the output schema. "
    "Do not include unsupported claims. "
    "Every statement must be grounded in the chart facts, triggered rules, "
    "or supporting passages provided."
)


def _chart_facts_section(bundle: ChartBundle) -> str:
    birth = bundle.birth
    d1 = bundle.d1
    lines = [
        f"Ascendant longitude: {d1.ascendant_longitude:.4f}",
    ]
    # Planets — sorted for determinism
    for name in sorted(d1.planets.keys()):
        p = d1.planets[name]
        lines.append(f"{name}: sign={p.rasi.rasi.value}, house={p.house}, lon={p.longitude:.4f}")
    # Houses — sorted by key
    for num in sorted(d1.houses.keys()):
        h = d1.houses[num]
        lines.append(f"House {num}: sign={h.rasi.value}, lon={h.cusp_longitude:.4f}")
    return "\n".join(lines)


def _derived_features_section(features: dict) -> str:
    # Deterministic serialisation: sort_keys=True, compact
    return json.dumps(features, sort_keys=True, ensure_ascii=False)


def _rules_section(triggers: list[RuleTrigger]) -> str:
    # Sort by rule_id for determinism
    lines = []
    for t in sorted(triggers, key=lambda x: x.rule_id):
        lines.append(
            f"[{t.rule_id}] {t.rule_name} (scope={t.scope}, weight={t.weight:.2f}): "
            f"{t.explanation}"
        )
    return "\n".join(lines) if lines else "(none)"


def _passages_section(passages: list[RetrievedPassage]) -> str:
    # Sort by chunk_id for determinism
    lines = []
    for p in sorted(passages, key=lambda x: x.chunk_id):
        lines.append(
            f"[{p.chunk_id}] (source={p.source}, score={p.score:.4f})\n{p.text}"
        )
    return "\n\n".join(lines) if lines else "(none)"


def _task_section(scope: str, output_schema: dict) -> str:
    schema_str = json.dumps(output_schema, sort_keys=True, indent=2)
    return (
        f"Generate a {scope} interpretation.\n"
        f"Output schema:\n{schema_str}"
    )


def build_interpretation_prompt(
    bundle: ChartBundle,
    features: dict,
    triggers: list[RuleTrigger],
    passages: list[RetrievedPassage],
    scope: str,
    output_schema: dict,
) -> str:
    """Construct the final prompt sent to the local model.

    Section order is fixed: CHART FACTS → DERIVED FEATURES → TRIGGERED RULES →
    SUPPORTING PASSAGES → TASK.  All sections are deterministic for fixed input.
    """
    parts = [
        _INSTRUCTION,
        "",
        _SECTION_CHART_FACTS,
        _chart_facts_section(bundle),
        "",
        _SECTION_DERIVED,
        _derived_features_section(features),
        "",
        _SECTION_RULES,
        _rules_section(triggers),
        "",
        _SECTION_PASSAGES,
        _passages_section(passages),
        "",
        _SECTION_TASK,
        _task_section(scope, output_schema),
    ]
    return "\n".join(parts)
