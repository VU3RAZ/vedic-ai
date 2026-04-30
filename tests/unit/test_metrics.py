"""Unit tests for Phase 9 evaluation framework."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from vedic_ai.domain.prediction import (
    PredictionEvidence,
    PredictionReport,
    PredictionSection,
    RuleTrigger,
)
from vedic_ai.evaluation.dataset import EvaluationCase, EvaluationSet, load_evaluation_set
from vedic_ai.evaluation.metrics import score_prediction_report
from vedic_ai.evaluation.runner import BenchmarkSummary, run_regression_benchmark

GOLDEN_DIR = Path(__file__).parents[2] / "data" / "golden"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(
    scope: str = "career",
    summary: str = "Strong career outlook",
    details: list[str] | None = None,
    rule_ids: list[str] | None = None,
) -> PredictionReport:
    rule_ids = rule_ids or []
    details = details or ["detail one", "detail two"]

    triggers = [
        RuleTrigger(rule_id=rid, rule_name=rid, scope=scope, weight=0.7, explanation="e")
        for rid in rule_ids
    ]
    evidence = [PredictionEvidence(trigger=t) for t in triggers]

    section = PredictionSection(scope=scope, summary=summary, details=details, evidence=evidence)
    return PredictionReport(
        birth_name="Test",
        generated_at=datetime.now(timezone.utc),
        sections=[section],
        model_name="test-model",
    )


def _make_case(
    case_id: str = "EC001",
    scope: str = "career",
    expected_rule_ids: list[str] | None = None,
    expected_keywords: list[str] | None = None,
    forbidden_keywords: list[str] | None = None,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        scope=scope,
        expected_rule_ids=expected_rule_ids or [],
        expected_keywords=expected_keywords or [],
        forbidden_keywords=forbidden_keywords or [],
    )


# ---------------------------------------------------------------------------
# EvaluationCase / EvaluationSet
# ---------------------------------------------------------------------------

class TestEvaluationDataset:
    def test_load_eval_set_from_file(self):
        path = GOLDEN_DIR / "eval_set_v1.json"
        if not path.exists():
            pytest.skip("eval_set_v1.json not found")
        ev_set = load_evaluation_set(str(path))
        assert isinstance(ev_set, EvaluationSet)
        assert len(ev_set.cases) > 0

    def test_load_eval_set_has_case_ids(self):
        path = GOLDEN_DIR / "eval_set_v1.json"
        if not path.exists():
            pytest.skip("eval_set_v1.json not found")
        ev_set = load_evaluation_set(str(path))
        assert all(c.case_id for c in ev_set.cases)

    def test_load_eval_set_missing_file_raises(self, tmp_path):
        from vedic_ai.core.exceptions import ConfigError
        with pytest.raises(ConfigError):
            load_evaluation_set(str(tmp_path / "nonexistent.json"))

    def test_load_eval_set_invalid_json_raises(self, tmp_path):
        from vedic_ai.core.exceptions import ConfigError
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json")
        with pytest.raises(ConfigError):
            load_evaluation_set(str(bad_file))


# ---------------------------------------------------------------------------
# score_prediction_report
# ---------------------------------------------------------------------------

class TestScorePredictionReport:
    def test_schema_valid_when_scope_present(self):
        report = _make_report(scope="career")
        case = _make_case(scope="career")
        result = score_prediction_report(report, case)
        assert result.schema_valid is True

    def test_schema_invalid_when_scope_missing(self):
        report = _make_report(scope="personality")
        case = _make_case(scope="career")
        result = score_prediction_report(report, case)
        assert result.schema_valid is False

    def test_evidence_coverage_full_match(self):
        report = _make_report(scope="career", rule_ids=["C001", "C002"])
        case = _make_case(scope="career", expected_rule_ids=["C001", "C002"])
        result = score_prediction_report(report, case)
        assert result.evidence_coverage == 1.0

    def test_evidence_coverage_partial_match(self):
        report = _make_report(scope="career", rule_ids=["C001"])
        case = _make_case(scope="career", expected_rule_ids=["C001", "C002"])
        result = score_prediction_report(report, case)
        assert result.evidence_coverage == 0.5

    def test_evidence_coverage_no_expected(self):
        report = _make_report(scope="career", rule_ids=[])
        case = _make_case(scope="career", expected_rule_ids=[])
        result = score_prediction_report(report, case)
        assert result.evidence_coverage == 1.0

    def test_keyword_hit_rate_full(self):
        report = _make_report(scope="career", summary="Strong career professional outlook")
        case = _make_case(scope="career", expected_keywords=["career", "professional"])
        result = score_prediction_report(report, case)
        assert result.keyword_hit_rate == 1.0

    def test_keyword_hit_rate_none(self):
        report = _make_report(scope="career", summary="General reading")
        case = _make_case(scope="career", expected_keywords=["career", "professional"])
        result = score_prediction_report(report, case)
        assert result.keyword_hit_rate == 0.0

    def test_keyword_hit_rate_no_expected(self):
        report = _make_report(scope="career")
        case = _make_case(scope="career", expected_keywords=[])
        result = score_prediction_report(report, case)
        assert result.keyword_hit_rate == 1.0

    def test_forbidden_keyword_rate_zero_when_absent(self):
        report = _make_report(scope="career", summary="Career is strong")
        case = _make_case(scope="career", forbidden_keywords=["I cannot", "I don't know"])
        result = score_prediction_report(report, case)
        assert result.forbidden_keyword_rate == 0.0

    def test_forbidden_keyword_rate_nonzero_when_present(self):
        report = _make_report(scope="career", summary="I cannot determine the career")
        case = _make_case(scope="career", forbidden_keywords=["I cannot"])
        result = score_prediction_report(report, case)
        assert result.forbidden_keyword_rate > 0.0

    def test_has_summary_true(self):
        report = _make_report(summary="Some summary")
        case = _make_case()
        result = score_prediction_report(report, case)
        assert result.has_summary is True

    def test_has_details_true(self):
        report = _make_report(details=["detail"])
        case = _make_case()
        result = score_prediction_report(report, case)
        assert result.has_details is True

    def test_result_case_id_matches(self):
        report = _make_report()
        case = _make_case(case_id="MY_CASE_42")
        result = score_prediction_report(report, case)
        assert result.case_id == "MY_CASE_42"


# ---------------------------------------------------------------------------
# run_regression_benchmark
# ---------------------------------------------------------------------------

class TestRunRegressionBenchmark:
    def _make_eval_set(self, n: int = 3) -> EvaluationSet:
        return EvaluationSet(
            name="test_set",
            cases=[_make_case(case_id=f"EC{i:03d}") for i in range(n)],
        )

    def test_returns_benchmark_summary(self):
        ev_set = self._make_eval_set(2)
        reports = [_make_report() for _ in ev_set.cases]
        summary = run_regression_benchmark(ev_set, "test-model", reports)
        assert isinstance(summary, BenchmarkSummary)

    def test_total_cases_correct(self):
        ev_set = self._make_eval_set(3)
        reports = [_make_report() for _ in ev_set.cases]
        summary = run_regression_benchmark(ev_set, "test-model", reports)
        assert summary.total_cases == 3

    def test_passed_plus_failed_equals_total(self):
        ev_set = self._make_eval_set(4)
        reports = [_make_report() for _ in ev_set.cases]
        summary = run_regression_benchmark(ev_set, "test-model", reports)
        assert summary.passed + summary.failed == summary.total_cases

    def test_model_name_stored(self):
        ev_set = self._make_eval_set(1)
        reports = [_make_report()]
        summary = run_regression_benchmark(ev_set, "my-model-v2", reports)
        assert summary.model_name == "my-model-v2"

    def test_wrong_count_raises(self):
        ev_set = self._make_eval_set(3)
        reports = [_make_report(), _make_report()]
        with pytest.raises(ValueError):
            run_regression_benchmark(ev_set, "test-model", reports)

    def test_mean_coverage_in_range(self):
        ev_set = self._make_eval_set(3)
        reports = [_make_report() for _ in ev_set.cases]
        summary = run_regression_benchmark(ev_set, "test-model", reports)
        assert 0.0 <= summary.mean_evidence_coverage <= 1.0

    def test_serialises_cleanly(self):
        ev_set = self._make_eval_set(2)
        reports = [_make_report() for _ in ev_set.cases]
        summary = run_regression_benchmark(ev_set, "test-model", reports)
        payload = summary.model_dump(mode="json")
        assert json.dumps(payload)

    def test_save_benchmark_results(self, tmp_path):
        from vedic_ai.evaluation.runner import save_benchmark_results
        ev_set = self._make_eval_set(2)
        reports = [_make_report() for _ in ev_set.cases]
        summary = run_regression_benchmark(ev_set, "test-model", reports)
        out = tmp_path / "benchmark.json"
        save_benchmark_results(summary, str(out))
        assert out.exists()
        payload = json.loads(out.read_text())
        assert "total_cases" in payload
