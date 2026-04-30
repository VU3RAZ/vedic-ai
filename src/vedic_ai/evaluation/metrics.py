"""Evaluation metrics for prediction report quality."""

from __future__ import annotations

from pydantic import BaseModel, Field

from vedic_ai.domain.prediction import PredictionReport
from vedic_ai.evaluation.dataset import EvaluationCase


class EvaluationResult(BaseModel):
    case_id: str
    scope: str
    schema_valid: bool = True
    evidence_coverage: float = Field(ge=0.0, le=1.0, default=0.0)
    rule_trigger_agreement: float = Field(ge=0.0, le=1.0, default=0.0)
    keyword_hit_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    forbidden_keyword_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    has_summary: bool = False
    has_details: bool = False
    notes: str = ""


def _compute_evidence_coverage(report: PredictionReport, reference: EvaluationCase) -> float:
    """Fraction of expected rule IDs that appear in any evidence trigger."""
    if not reference.expected_rule_ids:
        return 1.0
    triggered_ids: set[str] = set()
    for section in report.sections:
        for ev in section.evidence:
            if ev.trigger is not None:
                triggered_ids.add(ev.trigger.rule_id)
    hits = sum(1 for r in reference.expected_rule_ids if r in triggered_ids)
    return round(hits / len(reference.expected_rule_ids), 4)


def _compute_rule_trigger_agreement(report: PredictionReport, reference: EvaluationCase) -> float:
    """Fraction of expected rule IDs present in triggered evidence."""
    return _compute_evidence_coverage(report, reference)


def _compute_keyword_hit_rate(report: PredictionReport, reference: EvaluationCase) -> float:
    """Fraction of expected_keywords found (case-insensitive) in the report text."""
    if not reference.expected_keywords:
        return 1.0
    full_text = _extract_report_text(report).lower()
    hits = sum(1 for kw in reference.expected_keywords if kw.lower() in full_text)
    return round(hits / len(reference.expected_keywords), 4)


def _compute_forbidden_keyword_rate(report: PredictionReport, reference: EvaluationCase) -> float:
    """Fraction of forbidden_keywords found (case-insensitive) in the report text."""
    if not reference.forbidden_keywords:
        return 0.0
    full_text = _extract_report_text(report).lower()
    hits = sum(1 for kw in reference.forbidden_keywords if kw.lower() in full_text)
    return round(hits / len(reference.forbidden_keywords), 4)


def _extract_report_text(report: PredictionReport) -> str:
    parts: list[str] = []
    for section in report.sections:
        parts.append(section.summary)
        parts.extend(section.details)
    return " ".join(parts)


def score_prediction_report(
    report: PredictionReport,
    reference: EvaluationCase,
) -> EvaluationResult:
    """Compute evaluation metrics for one report against a labeled case.

    Returns an EvaluationResult with per-dimension scores.
    """
    scope_sections = [s for s in report.sections if s.scope == reference.scope]
    schema_valid = len(scope_sections) > 0
    has_summary = any(s.summary for s in scope_sections)
    has_details = any(s.details for s in scope_sections)

    notes_parts = []
    if not schema_valid:
        notes_parts.append(f"No section found for scope '{reference.scope}'")

    return EvaluationResult(
        case_id=reference.case_id,
        scope=reference.scope,
        schema_valid=schema_valid,
        evidence_coverage=_compute_evidence_coverage(report, reference),
        rule_trigger_agreement=_compute_rule_trigger_agreement(report, reference),
        keyword_hit_rate=_compute_keyword_hit_rate(report, reference),
        forbidden_keyword_rate=_compute_forbidden_keyword_rate(report, reference),
        has_summary=has_summary,
        has_details=has_details,
        notes="; ".join(notes_parts),
    )
