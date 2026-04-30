"""Integration tests for the prediction orchestration pipeline (Phase 7).

Uses dry_run=True to bypass the LLM and KerykeionAdapter for chart computation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.chart import ChartBundle, deserialize_chart_bundle
from vedic_ai.domain.prediction import PredictionReport, PredictionSection
from vedic_ai.orchestration.evidence_builder import (
    build_prediction_evidence,
    generate_scope_report,
)
from vedic_ai.orchestration.pipeline import run_prediction_pipeline
from vedic_ai.orchestration.prediction_service import (
    evaluate_scope_rules,
    load_rules_for_scope,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parents[2] / "data" / "fixtures"
RULES_DIR = Path(__file__).parents[2] / "data" / "corpus" / "rules"


@pytest.fixture(scope="module")
def birth_data() -> BirthData:
    return BirthData(
        birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone.utc),
        location=GeoLocation(latitude=28.6, longitude=77.2, place_name="Delhi"),
        name="Test Native",
    )


@pytest.fixture(scope="module")
def fixture_bundle() -> ChartBundle:
    path = FIXTURES_DIR / "sample_chart_a.json"
    if not path.exists():
        pytest.skip("Fixture sample_chart_a.json not generated")
    return deserialize_chart_bundle(json.loads(path.read_text()))


@pytest.fixture()
def mock_engine(fixture_bundle: ChartBundle):
    """Engine mock that returns the pre-built fixture bundle."""
    engine = MagicMock()
    engine.compute_birth_chart.return_value = fixture_bundle
    engine.compute_dashas.return_value = []
    return engine


# ---------------------------------------------------------------------------
# TestLoadRules
# ---------------------------------------------------------------------------

class TestLoadRules:
    def test_career_rules_loaded(self):
        rules = load_rules_for_scope("career", RULES_DIR)
        assert len(rules) > 0

    def test_personality_rules_loaded(self):
        rules = load_rules_for_scope("personality", RULES_DIR)
        assert len(rules) > 0

    def test_relationships_rules_loaded(self):
        rules = load_rules_for_scope("relationships", RULES_DIR)
        assert len(rules) > 0

    def test_unknown_scope_returns_empty(self):
        rules = load_rules_for_scope("unknown_scope", RULES_DIR)
        assert rules == []

    def test_rules_have_ids(self):
        rules = load_rules_for_scope("career", RULES_DIR)
        assert all(r.rule_id for r in rules)


# ---------------------------------------------------------------------------
# TestEvidenceBuilder
# ---------------------------------------------------------------------------

class TestEvidenceBuilder:
    def test_evidence_includes_triggers(self, fixture_bundle):
        from vedic_ai.features.core_features import extract_core_features
        from vedic_ai.domain.prediction import RuleTrigger

        features = extract_core_features(fixture_bundle)
        trigger = RuleTrigger(
            rule_id="C001",
            rule_name="Test rule",
            scope="career",
            weight=0.8,
            explanation="Test explanation.",
        )
        evidence = build_prediction_evidence(fixture_bundle, features, [trigger], [])
        assert len(evidence) >= 1
        assert evidence[0].trigger is not None
        assert evidence[0].trigger.rule_id == "C001"

    def test_evidence_includes_passages(self, fixture_bundle):
        from vedic_ai.domain.corpus import RetrievedPassage
        from vedic_ai.features.core_features import extract_core_features

        features = extract_core_features(fixture_bundle)
        passage = RetrievedPassage(
            chunk_id="bphs_024_0000",
            text="The Sun in the tenth house.",
            source="BPHS",
            score=0.9,
        )
        evidence = build_prediction_evidence(fixture_bundle, features, [], [passage])
        passage_evidences = [e for e in evidence if e.passage is not None]
        assert len(passage_evidences) == 1
        assert "tenth house" in passage_evidences[0].passage

    def test_chart_facts_populated(self, fixture_bundle):
        from vedic_ai.features.core_features import extract_core_features

        features = extract_core_features(fixture_bundle)
        evidence = build_prediction_evidence(fixture_bundle, features, [], [])
        # No triggers or passages → empty list
        assert evidence == []

    def test_chart_facts_on_trigger_evidence(self, fixture_bundle):
        from vedic_ai.domain.prediction import RuleTrigger
        from vedic_ai.features.core_features import extract_core_features

        features = extract_core_features(fixture_bundle)
        trigger = RuleTrigger(
            rule_id="P001",
            rule_name="Lagna rule",
            scope="personality",
            weight=0.5,
            explanation="Lagna effect.",
        )
        evidence = build_prediction_evidence(fixture_bundle, features, [trigger], [])
        assert len(evidence[0].chart_facts) > 0
        assert any("Sun" in f for f in evidence[0].chart_facts)


# ---------------------------------------------------------------------------
# TestGenerateScopeReport
# ---------------------------------------------------------------------------

class TestGenerateScopeReport:
    def test_section_scope_matches(self):
        section = generate_scope_report("career", {"summary": "Career ok", "details": []}, [])
        assert section.scope == "career"

    def test_section_summary_extracted(self):
        section = generate_scope_report("career", {"summary": "Strong career", "details": []}, [])
        assert section.summary == "Strong career"

    def test_section_details_extracted(self):
        interp = {"summary": "x", "details": ["point1", "point2"]}
        section = generate_scope_report("career", interp, [])
        assert section.details == ["point1", "point2"]

    def test_missing_summary_uses_empty_string(self):
        section = generate_scope_report("career", {"details": []}, [])
        assert section.summary == ""

    def test_non_list_details_wrapped(self):
        section = generate_scope_report("career", {"summary": "ok", "details": "single"}, [])
        assert isinstance(section.details, list)

    def test_evidence_attached(self):
        from vedic_ai.domain.prediction import PredictionEvidence, RuleTrigger

        trigger = RuleTrigger(
            rule_id="C001",
            rule_name="r",
            scope="career",
            weight=0.7,
            explanation="e",
        )
        ev = PredictionEvidence(trigger=trigger)
        section = generate_scope_report("career", {"summary": "s", "details": []}, [ev])
        assert len(section.evidence) == 1


# ---------------------------------------------------------------------------
# TestPredictionPipeline
# ---------------------------------------------------------------------------

class TestPredictionPipeline:
    def test_dry_run_returns_report(self, birth_data, mock_engine, tmp_path):
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            dry_run=True,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert isinstance(report, PredictionReport)

    def test_report_has_section(self, birth_data, mock_engine, tmp_path):
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            dry_run=True,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert len(report.sections) == 1
        assert report.sections[0].scope == "career"

    def test_report_birth_name(self, birth_data, mock_engine, tmp_path):
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            dry_run=True,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert report.birth_name == "Test Native"

    def test_artifacts_saved(self, birth_data, mock_engine, tmp_path):
        adir = tmp_path / "artifacts"
        run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            dry_run=True,
            artifacts_dir=adir,
            rules_dir=RULES_DIR,
        )
        assert (adir / "features.json").exists()
        assert (adir / "triggers.json").exists()
        assert (adir / "interpretation.json").exists()
        assert (adir / "report.json").exists()

    def test_report_serialises_cleanly(self, birth_data, mock_engine, tmp_path):
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            dry_run=True,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        payload = report.model_dump(mode="json")
        assert json.dumps(payload)  # must be JSON-serialisable

    def test_personality_scope(self, birth_data, mock_engine, tmp_path):
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="personality",
            engine=mock_engine,
            dry_run=True,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert report.sections[0].scope == "personality"

    def test_relationships_scope(self, birth_data, mock_engine, tmp_path):
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="relationships",
            engine=mock_engine,
            dry_run=True,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert report.sections[0].scope == "relationships"

    def test_mock_llm_called(self, birth_data, mock_engine, tmp_path):
        mock_client = MagicMock()
        mock_client.model_name = "mock-llm"
        mock_client.generate.return_value = json.dumps({
            "summary": "Mock summary",
            "details": ["detail1"],
            "rule_refs": [],
            "passage_refs": [],
        })
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            llm_client=mock_client,
            dry_run=False,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert mock_client.generate.called
        assert report.sections[0].summary == "Mock summary"

    def test_mock_llm_model_name_in_report(self, birth_data, mock_engine, tmp_path):
        mock_client = MagicMock()
        mock_client.model_name = "test-model-v1"
        mock_client.generate.return_value = json.dumps({
            "summary": "ok",
            "details": [],
            "rule_refs": [],
            "passage_refs": [],
        })
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            llm_client=mock_client,
            dry_run=False,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert report.model_name == "test-model-v1"

    def test_with_retriever(self, birth_data, mock_engine, tmp_path):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        report = run_prediction_pipeline(
            birth=birth_data,
            scope="career",
            engine=mock_engine,
            retriever=mock_retriever,
            dry_run=True,
            artifacts_dir=tmp_path / "artifacts",
            rules_dir=RULES_DIR,
        )
        assert mock_retriever.retrieve.called
        assert isinstance(report, PredictionReport)
