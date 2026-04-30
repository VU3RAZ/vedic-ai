"""Utilities for comparing RAG baseline vs fine-tuned model benchmark results."""

from __future__ import annotations

from pydantic import BaseModel

from vedic_ai.evaluation.runner import BenchmarkSummary


class ModelComparison(BaseModel):
    baseline_model: str
    tuned_model: str
    delta_evidence_coverage: float
    delta_keyword_hit_rate: float
    delta_forbidden_keyword_rate: float
    tuned_wins: bool
    notes: str = ""


def compare_rag_vs_tuned(
    baseline_results: BenchmarkSummary,
    tuned_results: BenchmarkSummary,
) -> ModelComparison:
    """Compare fine-tuned model quality against a RAG baseline benchmark.

    A tuned model 'wins' when it improves coverage and keyword hit rate
    without increasing the forbidden-keyword rate.

    Returns:
        ModelComparison with deltas and a pass/fail verdict.
    """
    delta_coverage = round(
        tuned_results.mean_evidence_coverage - baseline_results.mean_evidence_coverage, 4
    )
    delta_keyword = round(
        tuned_results.mean_keyword_hit_rate - baseline_results.mean_keyword_hit_rate, 4
    )
    delta_forbidden = round(
        tuned_results.mean_forbidden_keyword_rate - baseline_results.mean_forbidden_keyword_rate, 4
    )

    tuned_wins = (
        delta_coverage >= 0.0
        and delta_keyword >= 0.0
        and delta_forbidden <= 0.0
    )

    parts: list[str] = []
    if delta_coverage < 0:
        parts.append(f"coverage dropped by {abs(delta_coverage):.2%}")
    if delta_keyword < 0:
        parts.append(f"keyword hit rate dropped by {abs(delta_keyword):.2%}")
    if delta_forbidden > 0:
        parts.append(f"forbidden keyword rate increased by {delta_forbidden:.2%}")

    notes = "; ".join(parts) if parts else "Tuned model meets all quality gates."

    return ModelComparison(
        baseline_model=baseline_results.model_name,
        tuned_model=tuned_results.model_name,
        delta_evidence_coverage=delta_coverage,
        delta_keyword_hit_rate=delta_keyword,
        delta_forbidden_keyword_rate=delta_forbidden,
        tuned_wins=tuned_wins,
        notes=notes,
    )
