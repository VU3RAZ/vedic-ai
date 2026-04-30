"""Benchmark runner: execute evaluation over a labeled EvaluationSet."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from vedic_ai.domain.prediction import PredictionReport
from vedic_ai.evaluation.dataset import EvaluationCase, EvaluationSet
from vedic_ai.evaluation.metrics import EvaluationResult, score_prediction_report

logger = logging.getLogger(__name__)


class BenchmarkSummary(BaseModel):
    name: str
    model_name: str
    run_at: datetime
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    mean_evidence_coverage: float = Field(ge=0.0, le=1.0, default=0.0)
    mean_keyword_hit_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    mean_forbidden_keyword_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    results: list[EvaluationResult] = Field(default_factory=list)


def run_regression_benchmark(
    cases: EvaluationSet,
    model_name: str,
    reports: list[PredictionReport],
    *,
    pass_threshold_coverage: float = 0.0,
) -> BenchmarkSummary:
    """Run the benchmark for a set of labeled cases against pre-generated reports.

    Args:
        cases: Labeled evaluation set.
        model_name: Name of the model that generated the reports.
        reports: One PredictionReport per EvaluationCase, in the same order.
        pass_threshold_coverage: Minimum evidence_coverage to count as 'passed'.

    Returns:
        BenchmarkSummary with per-case results and aggregate metrics.
    """
    if len(reports) != len(cases.cases):
        raise ValueError(
            f"Report count ({len(reports)}) must equal case count ({len(cases.cases)})"
        )

    results: list[EvaluationResult] = []
    for case, report in zip(cases.cases, reports):
        result = score_prediction_report(report, case)
        results.append(result)
        logger.debug(
            "Case %s: coverage=%.2f keyword_hit=%.2f forbidden=%.2f",
            case.case_id,
            result.evidence_coverage,
            result.keyword_hit_rate,
            result.forbidden_keyword_rate,
        )

    passed = sum(
        1 for r in results if r.schema_valid and r.evidence_coverage >= pass_threshold_coverage
    )
    n = len(results)

    mean_coverage = round(sum(r.evidence_coverage for r in results) / n, 4) if n else 0.0
    mean_keyword = round(sum(r.keyword_hit_rate for r in results) / n, 4) if n else 0.0
    mean_forbidden = round(sum(r.forbidden_keyword_rate for r in results) / n, 4) if n else 0.0

    return BenchmarkSummary(
        name=cases.name,
        model_name=model_name,
        run_at=datetime.now(timezone.utc),
        total_cases=n,
        passed=passed,
        failed=n - passed,
        mean_evidence_coverage=mean_coverage,
        mean_keyword_hit_rate=mean_keyword,
        mean_forbidden_keyword_rate=mean_forbidden,
        results=results,
    )


def save_benchmark_results(summary: BenchmarkSummary, output_path: str) -> None:
    """Persist benchmark results as JSON for regression tracking."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(summary.model_dump(mode="json"), indent=2), encoding="utf-8")
    logger.info("Benchmark results saved to %s", output_path)
