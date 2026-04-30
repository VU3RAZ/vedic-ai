"""Build supervised fine-tuning (SFT) training examples from labeled evaluation cases."""

from __future__ import annotations

import json
from pathlib import Path

from vedic_ai.domain.prediction import PredictionReport
from vedic_ai.evaluation.dataset import EvaluationCase, EvaluationSet


def build_sft_examples(
    cases: EvaluationSet,
    reports: list[PredictionReport],
) -> list[dict]:
    """Generate SFT training examples from chart facts and approved interpretations.

    Each example is a dict with:
      - 'case_id'
      - 'scope'
      - 'prompt'   — the instruction sent to the model (derived from evidence)
      - 'response' — the approved interpretation (summary + details)

    Only cases whose reports have a matching scope section are included.
    """
    if len(reports) != len(cases.cases):
        raise ValueError(
            f"Report count ({len(reports)}) must equal case count ({len(cases.cases)})"
        )

    examples: list[dict] = []
    for case, report in zip(cases.cases, reports):
        section = next(
            (s for s in report.sections if s.scope == case.scope), None
        )
        if section is None:
            continue

        rule_ids = [
            ev.trigger.rule_id
            for ev in section.evidence
            if ev.trigger is not None
        ]
        chart_facts = [
            fact
            for ev in section.evidence
            for fact in ev.chart_facts
        ]

        prompt = (
            f"Scope: {case.scope}\n"
            f"Triggered rules: {', '.join(rule_ids) or 'none'}\n"
            f"Chart facts: {'; '.join(chart_facts[:5]) or 'none'}\n"
            "Generate a grounded Vedic astrology interpretation for this scope."
        )

        response_dict = {
            "summary": section.summary,
            "details": section.details,
            "rule_refs": rule_ids,
            "passage_refs": [],
        }

        examples.append({
            "case_id": case.case_id,
            "scope": case.scope,
            "prompt": prompt,
            "response": json.dumps(response_dict, ensure_ascii=False),
        })

    return examples


def export_training_dataset(examples: list[dict], output_path: str) -> str:
    """Write SFT examples as a JSONL file (one JSON object per line).

    Returns the resolved output path.
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(ex, ensure_ascii=False) for ex in examples]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p.resolve())
