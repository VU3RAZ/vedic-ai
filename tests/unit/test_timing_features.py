"""Unit tests for Phase 8 timing feature modules."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.domain.enums import Graha
from vedic_ai.engines.vimshottari import (
    VIMSHOTTARI_YEARS,
    compute_antardasha_periods,
    compute_vimshottari_dashas,
)
from vedic_ai.features.dasha_features import (
    compute_timing_features,
    get_active_antardasha,
    get_active_mahadasha,
)

FIXTURES_DIR = Path(__file__).parents[2] / "data" / "fixtures"


# ---------------------------------------------------------------------------
# Antardasha computation
# ---------------------------------------------------------------------------

class TestComputeAntardashaperiods:
    def _make_maha(self, graha: Graha, years: int) -> DashaPeriod:
        start = date(2000, 1, 1)
        end = date(2000 + years, 1, 1)
        return DashaPeriod(graha=graha, level=1, start_date=start, end_date=end)

    def test_returns_nine_sub_periods(self):
        maha = self._make_maha(Graha.JUPITER, 16)
        subs = compute_antardasha_periods(maha)
        assert len(subs) == 9

    def test_sub_periods_are_level_2(self):
        maha = self._make_maha(Graha.SATURN, 19)
        subs = compute_antardasha_periods(maha)
        assert all(s.level == 2 for s in subs)

    def test_first_sub_lord_is_maha_lord(self):
        maha = self._make_maha(Graha.VENUS, 20)
        subs = compute_antardasha_periods(maha)
        assert subs[0].graha == Graha.VENUS

    def test_sub_periods_are_contiguous(self):
        maha = self._make_maha(Graha.JUPITER, 16)
        subs = compute_antardasha_periods(maha)
        for i in range(len(subs) - 1):
            assert subs[i].end_date == subs[i + 1].start_date

    def test_sub_periods_start_at_maha_start(self):
        maha = self._make_maha(Graha.MERCURY, 17)
        subs = compute_antardasha_periods(maha)
        assert subs[0].start_date == maha.start_date

    def test_sub_periods_end_at_maha_end(self):
        maha = self._make_maha(Graha.MARS, 7)
        subs = compute_antardasha_periods(maha)
        assert subs[-1].end_date == maha.end_date

    def test_longer_lords_get_longer_sub_periods(self):
        maha = self._make_maha(Graha.VENUS, 20)
        subs = compute_antardasha_periods(maha)
        sub_by_lord = {s.graha: (s.end_date - s.start_date).days for s in subs}
        # Venus sub-period (20 yrs / 120 * total) > Sun sub-period (6 yrs / 120 * total)
        assert sub_by_lord[Graha.VENUS] > sub_by_lord[Graha.SUN]


# ---------------------------------------------------------------------------
# get_active_mahadasha / get_active_antardasha
# ---------------------------------------------------------------------------

class TestGetActiveDasha:
    def _dashas(self):
        return [
            DashaPeriod(graha=Graha.JUPITER, level=1,
                        start_date=date(2010, 1, 1), end_date=date(2026, 1, 1)),
            DashaPeriod(graha=Graha.SATURN, level=1,
                        start_date=date(2026, 1, 1), end_date=date(2045, 1, 1)),
        ]

    def test_returns_correct_mahadasha(self):
        dashas = self._dashas()
        result = get_active_mahadasha(dashas, date(2020, 6, 15))
        assert result is not None
        assert result.graha == Graha.JUPITER

    def test_returns_none_before_all_dashas(self):
        dashas = self._dashas()
        result = get_active_mahadasha(dashas, date(2005, 1, 1))
        assert result is None

    def test_boundary_date_belongs_to_next_period(self):
        dashas = self._dashas()
        result = get_active_mahadasha(dashas, date(2026, 1, 1))
        assert result is not None
        assert result.graha == Graha.SATURN

    def test_antardasha_lord_found(self):
        maha = DashaPeriod(
            graha=Graha.JUPITER, level=1,
            start_date=date(2010, 1, 1), end_date=date(2026, 1, 1),
        )
        # First sub = Jupiter itself; check that something is found
        antar = get_active_antardasha(maha, date(2010, 3, 1))
        assert antar is not None
        assert antar.graha == Graha.JUPITER

    def test_antardasha_none_outside_maha(self):
        maha = DashaPeriod(
            graha=Graha.MARS, level=1,
            start_date=date(2030, 1, 1), end_date=date(2037, 1, 1),
        )
        antar = get_active_antardasha(maha, date(2025, 1, 1))
        assert antar is None


# ---------------------------------------------------------------------------
# compute_timing_features
# ---------------------------------------------------------------------------

class TestComputeTimingFeatures:
    def _bundle_with_dashas(self):
        path = FIXTURES_DIR / "sample_chart_a.json"
        if not path.exists():
            pytest.skip("sample_chart_a.json not available")
        from vedic_ai.domain.chart import deserialize_chart_bundle
        bundle = deserialize_chart_bundle(json.loads(path.read_text()))
        # Override dashas to something deterministic
        bundle = bundle.model_copy(update={
            "dashas": [
                DashaPeriod(graha=Graha.JUPITER, level=1,
                            start_date=date(2015, 1, 1), end_date=date(2031, 1, 1)),
                DashaPeriod(graha=Graha.SATURN, level=1,
                            start_date=date(2031, 1, 1), end_date=date(2050, 1, 1)),
            ]
        })
        return bundle

    def test_has_required_keys(self):
        bundle = self._bundle_with_dashas()
        at = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
        result = compute_timing_features(bundle, at)
        assert "timing" in result
        assert "mahadasha" in result["timing"]
        assert "antardasha" in result["timing"]
        assert "reference_date" in result["timing"]

    def test_correct_mahadasha_lord(self):
        bundle = self._bundle_with_dashas()
        at = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
        result = compute_timing_features(bundle, at)
        assert result["timing"]["mahadasha"]["lord"] == "Jupiter"

    def test_antardasha_lord_is_string_or_none(self):
        bundle = self._bundle_with_dashas()
        at = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
        result = compute_timing_features(bundle, at)
        lord = result["timing"]["antardasha"]["lord"]
        assert lord is None or isinstance(lord, str)

    def test_no_mahadasha_outside_all_periods(self):
        path = FIXTURES_DIR / "sample_chart_a.json"
        if not path.exists():
            pytest.skip("sample_chart_a.json not available")
        from vedic_ai.domain.chart import deserialize_chart_bundle
        bundle = deserialize_chart_bundle(json.loads(path.read_text()))
        bundle = bundle.model_copy(update={"dashas": []})
        at = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
        result = compute_timing_features(bundle, at)
        assert result["timing"]["mahadasha"]["lord"] is None
