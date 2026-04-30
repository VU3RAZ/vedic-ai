"""Integration tests for Phase 8 timing pipeline."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.chart import deserialize_chart_bundle
from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.domain.enums import Graha
from vedic_ai.domain.prediction import ForecastReport
from vedic_ai.features.dasha_features import compute_timing_features
from vedic_ai.features.transit_features import compute_transit_features
from vedic_ai.orchestration.timing_service import evaluate_timing_rules, generate_forecast_window

FIXTURES_DIR = Path(__file__).parents[2] / "data" / "fixtures"
RULES_DIR = Path(__file__).parents[2] / "data" / "corpus" / "rules"
TIMING_RULES_PATH = RULES_DIR / "timing.yaml"


@pytest.fixture(scope="module")
def fixture_bundle():
    path = FIXTURES_DIR / "sample_chart_a.json"
    if not path.exists():
        pytest.skip("sample_chart_a.json not available")
    bundle = deserialize_chart_bundle(json.loads(path.read_text()))
    return bundle.model_copy(update={
        "dashas": [
            DashaPeriod(graha=Graha.JUPITER, level=1,
                        start_date=date(2015, 1, 1), end_date=date(2031, 1, 1)),
            DashaPeriod(graha=Graha.SATURN, level=1,
                        start_date=date(2031, 1, 1), end_date=date(2050, 1, 1)),
        ]
    })


@pytest.fixture(scope="module")
def birth_data():
    return BirthData(
        birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone.utc),
        location=GeoLocation(latitude=28.6, longitude=77.2, place_name="Delhi"),
        name="Test Native",
    )


class TestTimingRuleEvaluation:
    def test_timing_rules_file_exists(self):
        assert TIMING_RULES_PATH.exists(), "timing.yaml not found"

    def test_evaluate_timing_rules_returns_list(self, fixture_bundle):
        from vedic_ai.core.rule_loader import load_rule_set
        rules = load_rule_set(str(TIMING_RULES_PATH))
        at = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
        timing_feats = compute_timing_features(fixture_bundle, at)
        from vedic_ai.features.core_features import extract_core_features
        natal_feats = extract_core_features(fixture_bundle)
        triggers = evaluate_timing_rules(fixture_bundle, natal_feats, timing_feats, rules)
        assert isinstance(triggers, list)

    def test_jupiter_mahadasha_triggers_rule(self, fixture_bundle):
        from vedic_ai.core.rule_loader import load_rule_set
        rules = load_rule_set(str(TIMING_RULES_PATH))
        at = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
        timing_feats = compute_timing_features(fixture_bundle, at)
        from vedic_ai.features.core_features import extract_core_features
        natal_feats = extract_core_features(fixture_bundle)
        triggers = evaluate_timing_rules(fixture_bundle, natal_feats, timing_feats, rules)
        rule_ids = [t.rule_id for t in triggers]
        assert "T002" in rule_ids  # Jupiter Mahadasha rule

    def test_triggers_have_timing_scope(self, fixture_bundle):
        from vedic_ai.core.rule_loader import load_rule_set
        rules = load_rule_set(str(TIMING_RULES_PATH))
        at = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
        timing_feats = compute_timing_features(fixture_bundle, at)
        from vedic_ai.features.core_features import extract_core_features
        natal_feats = extract_core_features(fixture_bundle)
        triggers = evaluate_timing_rules(fixture_bundle, natal_feats, timing_feats, rules)
        assert all(t.scope == "timing" for t in triggers)


class TestTransitFeatures:
    def test_transit_features_returns_dict(self, fixture_bundle):
        from vedic_ai.domain.chart import TransitSnapshot
        snapshot = TransitSnapshot(
            at_time=datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc),
            planets=fixture_bundle.d1.planets,
        )
        feats = compute_transit_features(fixture_bundle, snapshot)
        assert isinstance(feats, dict)

    def test_transit_features_has_house_keys(self, fixture_bundle):
        from vedic_ai.domain.chart import TransitSnapshot
        snapshot = TransitSnapshot(
            at_time=datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc),
            planets=fixture_bundle.d1.planets,
        )
        feats = compute_transit_features(fixture_bundle, snapshot)
        assert "transit" in feats
        assert len(feats["transit"]) > 0
        # Each graha dict should have a 'house' key
        for graha_name, graha_dict in feats["transit"].items():
            assert "house" in graha_dict, f"Missing 'house' for {graha_name}"

    def test_transit_house_values_in_range(self, fixture_bundle):
        from vedic_ai.domain.chart import TransitSnapshot
        snapshot = TransitSnapshot(
            at_time=datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc),
            planets=fixture_bundle.d1.planets,
        )
        feats = compute_transit_features(fixture_bundle, snapshot)
        for graha_name, graha_dict in feats["transit"].items():
            h = graha_dict["house"]
            assert 1 <= h <= 12, f"{graha_name}.house = {h} out of range"


class TestForecastWindow:
    def test_forecast_returns_report(self, birth_data, fixture_bundle):
        mock_engine = MagicMock()
        mock_engine.compute_birth_chart.return_value = fixture_bundle
        mock_engine.compute_dashas.return_value = fixture_bundle.dashas
        mock_engine.compute_transits.side_effect = Exception("no transits in test")

        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 3, 31, tzinfo=timezone.utc)

        report = generate_forecast_window(
            birth=birth_data,
            start=start,
            end=end,
            scopes=["career"],
            engine=mock_engine,
            rules_path=TIMING_RULES_PATH,
            step_days=30,
        )
        assert isinstance(report, ForecastReport)

    def test_forecast_windows_non_empty(self, birth_data, fixture_bundle):
        mock_engine = MagicMock()
        mock_engine.compute_birth_chart.return_value = fixture_bundle
        mock_engine.compute_dashas.return_value = fixture_bundle.dashas
        mock_engine.compute_transits.side_effect = Exception("no transits in test")

        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 3, 31, tzinfo=timezone.utc)

        report = generate_forecast_window(
            birth=birth_data,
            start=start,
            end=end,
            scopes=["career", "personality"],
            engine=mock_engine,
            rules_path=TIMING_RULES_PATH,
            step_days=30,
        )
        # 3 steps × 2 scopes = 6 windows
        assert len(report.windows) >= 4

    def test_forecast_windows_have_mahadasha(self, birth_data, fixture_bundle):
        mock_engine = MagicMock()
        mock_engine.compute_birth_chart.return_value = fixture_bundle
        mock_engine.compute_dashas.return_value = fixture_bundle.dashas
        mock_engine.compute_transits.side_effect = Exception("no transits in test")

        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)

        report = generate_forecast_window(
            birth=birth_data,
            start=start,
            end=end,
            scopes=["career"],
            engine=mock_engine,
            rules_path=TIMING_RULES_PATH,
            step_days=30,
        )
        assert report.windows[0].mahadasha_lord == "Jupiter"

    def test_forecast_report_serialises(self, birth_data, fixture_bundle):
        mock_engine = MagicMock()
        mock_engine.compute_birth_chart.return_value = fixture_bundle
        mock_engine.compute_dashas.return_value = fixture_bundle.dashas
        mock_engine.compute_transits.side_effect = Exception("no transits in test")

        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)

        report = generate_forecast_window(
            birth=birth_data,
            start=start,
            end=end,
            scopes=["career"],
            engine=mock_engine,
            rules_path=TIMING_RULES_PATH,
            step_days=30,
        )
        payload = report.model_dump(mode="json")
        assert json.dumps(payload)  # must be JSON-serialisable
