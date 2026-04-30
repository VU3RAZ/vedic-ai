"""Integration tests for Phase 10 fine-tuning data preparation."""

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
from vedic_ai.evaluation.dataset import EvaluationCase, EvaluationSet
from vedic_ai.evaluation.runner import BenchmarkSummary, run_regression_benchmark
from vedic_ai.evaluation.training_data import build_sft_examples, export_training_dataset
from vedic_ai.llm.fine_tune_prep import ModelComparison, compare_rag_vs_tuned


def _make_report(scope: str = "career", rule_ids: list[str] | None = None) -> PredictionReport:
    rule_ids = rule_ids or ["C001"]
    triggers = [
        RuleTrigger(rule_id=r, rule_name=r, scope=scope, weight=0.7, explanation="exp")
        for r in rule_ids
    ]
    evidence = [PredictionEvidence(trigger=t, chart_facts=["Sun: sign=Leo, house=10"]) for t in triggers]
    section = PredictionSection(
        scope=scope,
        summary=f"{scope} summary with career professional keywords",
        details=["detail one"],
        evidence=evidence,
    )
    return PredictionReport(
        birth_name="Test",
        generated_at=datetime.now(timezone.utc),
        sections=[section],
        model_name="test-model",
    )


def _make_eval_set(n: int = 3, scope: str = "career") -> EvaluationSet:
    return EvaluationSet(
        name="test_set",
        cases=[
            EvaluationCase(
                case_id=f"EC{i:03d}",
                scope=scope,
                expected_rule_ids=["C001"],
                expected_keywords=["career"],
            )
            for i in range(n)
        ],
    )


class TestBuildSftExamples:
    def test_returns_list(self):
        ev_set = _make_eval_set(2)
        reports = [_make_report() for _ in ev_set.cases]
        examples = build_sft_examples(ev_set, reports)
        assert isinstance(examples, list)

    def test_example_count_matches_cases(self):
        ev_set = _make_eval_set(3)
        reports = [_make_report() for _ in ev_set.cases]
        examples = build_sft_examples(ev_set, reports)
        assert len(examples) == 3

    def test_examples_have_prompt_and_response(self):
        ev_set = _make_eval_set(2)
        reports = [_make_report() for _ in ev_set.cases]
        examples = build_sft_examples(ev_set, reports)
        for ex in examples:
            assert "prompt" in ex
            assert "response" in ex

    def test_response_is_valid_json(self):
        ev_set = _make_eval_set(2)
        reports = [_make_report() for _ in ev_set.cases]
        examples = build_sft_examples(ev_set, reports)
        for ex in examples:
            payload = json.loads(ex["response"])
            assert "summary" in payload
            assert "details" in payload

    def test_wrong_report_count_raises(self):
        ev_set = _make_eval_set(3)
        with pytest.raises(ValueError):
            build_sft_examples(ev_set, [_make_report(), _make_report()])

    def test_skips_mismatched_scope(self):
        ev_set = EvaluationSet(
            name="x",
            cases=[EvaluationCase(case_id="EC001", scope="career")],
        )
        report = _make_report(scope="personality")
        examples = build_sft_examples(ev_set, [report])
        assert examples == []

    def test_prompt_contains_scope(self):
        ev_set = _make_eval_set(1, scope="relationships")
        reports = [_make_report(scope="relationships")]
        examples = build_sft_examples(ev_set, reports)
        assert "relationships" in examples[0]["prompt"]


class TestExportTrainingDataset:
    def test_creates_jsonl_file(self, tmp_path):
        examples = [{"prompt": "p1", "response": "r1"}, {"prompt": "p2", "response": "r2"}]
        out = export_training_dataset(examples, str(tmp_path / "train.jsonl"))
        assert Path(out).exists()

    def test_each_line_is_valid_json(self, tmp_path):
        examples = [{"prompt": "p1", "response": "r1"}, {"prompt": "p2", "response": "r2"}]
        out = export_training_dataset(examples, str(tmp_path / "train.jsonl"))
        lines = [l for l in Path(out).read_text().splitlines() if l.strip()]
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert "prompt" in obj

    def test_creates_parent_dirs(self, tmp_path):
        examples = [{"prompt": "p", "response": "r"}]
        out_path = str(tmp_path / "deep" / "nested" / "train.jsonl")
        export_training_dataset(examples, out_path)
        assert Path(out_path).exists()

    def test_returns_resolved_path(self, tmp_path):
        examples = [{"a": "b"}]
        out = export_training_dataset(examples, str(tmp_path / "out.jsonl"))
        assert out.endswith("out.jsonl")


class TestCompareRagVsTuned:
    def _summary(self, model_name: str, coverage: float, keyword: float, forbidden: float):
        return BenchmarkSummary(
            name="test",
            model_name=model_name,
            run_at=datetime.now(timezone.utc),
            total_cases=10,
            passed=8,
            failed=2,
            mean_evidence_coverage=coverage,
            mean_keyword_hit_rate=keyword,
            mean_forbidden_keyword_rate=forbidden,
        )

    def test_tuned_wins_when_all_improve(self):
        baseline = self._summary("rag", 0.6, 0.7, 0.1)
        tuned = self._summary("lora", 0.7, 0.8, 0.05)
        cmp = compare_rag_vs_tuned(baseline, tuned)
        assert cmp.tuned_wins is True

    def test_tuned_loses_when_coverage_drops(self):
        baseline = self._summary("rag", 0.8, 0.7, 0.1)
        tuned = self._summary("lora", 0.6, 0.8, 0.05)
        cmp = compare_rag_vs_tuned(baseline, tuned)
        assert cmp.tuned_wins is False

    def test_tuned_loses_when_forbidden_increases(self):
        baseline = self._summary("rag", 0.6, 0.7, 0.1)
        tuned = self._summary("lora", 0.7, 0.8, 0.2)
        cmp = compare_rag_vs_tuned(baseline, tuned)
        assert cmp.tuned_wins is False

    def test_delta_coverage_computed(self):
        baseline = self._summary("rag", 0.5, 0.5, 0.1)
        tuned = self._summary("lora", 0.7, 0.5, 0.1)
        cmp = compare_rag_vs_tuned(baseline, tuned)
        assert abs(cmp.delta_evidence_coverage - 0.2) < 0.001

    def test_model_names_stored(self):
        baseline = self._summary("rag-base", 0.5, 0.5, 0.1)
        tuned = self._summary("lora-v1", 0.6, 0.6, 0.05)
        cmp = compare_rag_vs_tuned(baseline, tuned)
        assert cmp.baseline_model == "rag-base"
        assert cmp.tuned_model == "lora-v1"

    def test_comparison_serialises(self):
        baseline = self._summary("rag", 0.5, 0.5, 0.1)
        tuned = self._summary("lora", 0.6, 0.6, 0.05)
        cmp = compare_rag_vs_tuned(baseline, tuned)
        payload = cmp.model_dump(mode="json")
        assert json.dumps(payload)
