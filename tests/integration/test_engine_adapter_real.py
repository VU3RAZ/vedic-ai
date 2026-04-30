"""Integration tests: real pyswisseph calls via SwissEphAdapter.

These tests make live ephemeris calculations. They require pyswisseph to be
installed (pip install pyswisseph) and use the built-in Moshier ephemeris.

Reference positions for 1990-04-05 10:00 IST, New Delhi (28.6139N, 77.2090E)
computed from Swiss Ephemeris with Lahiri ayanamsa. Tolerance ±0.5° accommodates
the Moshier ephemeris (which is accurate to ~1 arc-minute for this era).
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

import pytest

swisseph = pytest.importorskip("swisseph", reason="pyswisseph not installed")

from vedic_ai.core.config import AppConfig
from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.enums import Graha, Rasi
from vedic_ai.engines.base import AstrologyEngine, compute_core_chart
from vedic_ai.engines.registry import select_engine
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter

_BIRTH = BirthData(
    birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))),
    location=GeoLocation(latitude=28.6139, longitude=77.2090, place_name="New Delhi, India"),
    name="Integration Test Chart",
)

# Swiss Ephemeris reference values (Lahiri ayanamsa, 1990-04-05 04:30 UT)
_EXPECTED = {
    "Sun": {"longitude": 351.41, "rasi": Rasi.PISCES},
    "Moon": {"longitude": 115.05, "rasi": Rasi.CANCER},
    "Mars": {"longitude": 294.51, "rasi": Rasi.CAPRICORN},
    "Rahu": {"longitude": 289.75, "rasi": Rasi.CAPRICORN},
    "ascendant_longitude": 58.43,  # Taurus
}

_TOL = 0.5  # arc-degree tolerance for Moshier ephemeris


@pytest.fixture(scope="module")
def adapter() -> SwissEphAdapter:
    return SwissEphAdapter(ayanamsa="lahiri", house_system="whole_sign", node_type="mean")


@pytest.fixture(scope="module")
def bundle(adapter: SwissEphAdapter):
    return adapter.compute_birth_chart(_BIRTH)


class TestSelectEngine:
    def test_returns_swisseph_adapter(self) -> None:
        cfg = AppConfig()
        engine = select_engine("swisseph", cfg)
        assert isinstance(engine, SwissEphAdapter)

    def test_satisfies_protocol(self) -> None:
        cfg = AppConfig()
        engine = select_engine("swisseph", cfg)
        assert isinstance(engine, AstrologyEngine)

    def test_unknown_engine_raises_config_error(self) -> None:
        from vedic_ai.core.exceptions import ConfigError
        with pytest.raises(ConfigError, match="Unknown engine"):
            select_engine("nonexistent", AppConfig())


class TestComputeBirthChart:
    def test_returns_chart_bundle(self, bundle) -> None:
        from vedic_ai.domain.chart import ChartBundle
        assert isinstance(bundle, ChartBundle)

    def test_nine_grahas_present(self, bundle) -> None:
        assert set(bundle.d1.planets.keys()) == {g.value for g in Graha}

    def test_twelve_houses_present(self, bundle) -> None:
        assert set(bundle.d1.houses.keys()) == set(range(1, 13))

    def test_engine_label(self, bundle) -> None:
        assert bundle.engine == "swisseph"

    def test_ayanamsa_label(self, bundle) -> None:
        assert bundle.ayanamsa == "lahiri"

    def test_birth_data_attached(self, bundle) -> None:
        assert bundle.birth.name == "Integration Test Chart"

    def test_ascendant_in_taurus(self, bundle) -> None:
        assert bundle.d1.houses[1].rasi == Rasi.TAURUS
        assert bundle.d1.ascendant_longitude == pytest.approx(_EXPECTED["ascendant_longitude"], abs=_TOL)

    def test_sun_longitude(self, bundle) -> None:
        sun = bundle.d1.planets[Graha.SUN.value]
        assert sun.longitude == pytest.approx(_EXPECTED["Sun"]["longitude"], abs=_TOL)
        assert sun.rasi.rasi == _EXPECTED["Sun"]["rasi"]

    def test_moon_longitude(self, bundle) -> None:
        moon = bundle.d1.planets[Graha.MOON.value]
        assert moon.longitude == pytest.approx(_EXPECTED["Moon"]["longitude"], abs=_TOL)
        assert moon.rasi.rasi == _EXPECTED["Moon"]["rasi"]

    def test_mars_in_capricorn(self, bundle) -> None:
        mars = bundle.d1.planets[Graha.MARS.value]
        assert mars.rasi.rasi == Rasi.CAPRICORN

    def test_rahu_retrograde(self, bundle) -> None:
        assert bundle.d1.planets[Graha.RAHU.value].is_retrograde is True

    def test_ketu_retrograde(self, bundle) -> None:
        assert bundle.d1.planets[Graha.KETU.value].is_retrograde is True

    def test_rahu_ketu_opposite(self, bundle) -> None:
        rahu_lon = bundle.d1.planets[Graha.RAHU.value].longitude
        ketu_lon = bundle.d1.planets[Graha.KETU.value].longitude
        diff = abs(rahu_lon - ketu_lon)
        assert diff == pytest.approx(180.0, abs=0.01)

    def test_house_lords_correct(self, bundle) -> None:
        # H1 = Taurus → lord = Venus; H7 = Scorpio → lord = Mars
        assert bundle.d1.houses[1].lord == Graha.VENUS
        assert bundle.d1.houses[7].lord == Graha.MARS

    def test_occupants_consistent_with_house_numbers(self, bundle) -> None:
        for h, house in bundle.d1.houses.items():
            for graha in house.occupants:
                assert bundle.d1.planets[graha.value].house == h

    def test_provenance_ayanamsa_value(self, bundle) -> None:
        ay = bundle.provenance.get("ayanamsa_value")
        assert ay is not None
        assert abs(ay - 23.72) < 0.1

    def test_chart_bundle_serializes(self, bundle) -> None:
        from vedic_ai.domain.chart import serialize_chart_bundle, deserialize_chart_bundle
        payload = serialize_chart_bundle(bundle)
        restored = deserialize_chart_bundle(payload)
        assert restored.d1.ascendant_longitude == pytest.approx(bundle.d1.ascendant_longitude, abs=0.001)


class TestComputeDashas:
    def test_returns_dasha_list(self, adapter: SwissEphAdapter) -> None:
        dashas = adapter.compute_dashas(_BIRTH)
        assert len(dashas) > 0

    def test_first_dasha_starts_at_birth(self, adapter: SwissEphAdapter) -> None:
        dashas = adapter.compute_dashas(_BIRTH)
        assert dashas[0].start_date == date(1990, 4, 5)

    def test_dashas_non_overlapping(self, adapter: SwissEphAdapter) -> None:
        dashas = adapter.compute_dashas(_BIRTH)
        for i in range(len(dashas) - 1):
            assert dashas[i].end_date == dashas[i + 1].start_date

    def test_moon_in_ashlesha_starts_mercury_dasha(self, adapter: SwissEphAdapter) -> None:
        # Moon at 115.05° is in Ashlesha (106.67°–120°, lord = Mercury)
        dashas = adapter.compute_dashas(_BIRTH)
        assert dashas[0].graha == Graha.MERCURY


class TestComputeCoreChart:
    def test_includes_dashas_by_default(self, adapter: SwissEphAdapter) -> None:
        bundle = compute_core_chart(_BIRTH, adapter)
        assert len(bundle.dashas) > 0

    def test_no_dashas_when_disabled(self, adapter: SwissEphAdapter) -> None:
        bundle = compute_core_chart(_BIRTH, adapter, include_dashas=False)
        assert bundle.dashas == []

    def test_unknown_varga_raises_engine_error(self, adapter: SwissEphAdapter) -> None:
        with pytest.raises(EngineError, match="not supported"):
            compute_core_chart(_BIRTH, adapter, include_vargas=["D9"])


class TestErrorHandling:
    def test_unknown_ayanamsa_raises_engine_error(self) -> None:
        with pytest.raises(EngineError, match="Unknown ayanamsa"):
            SwissEphAdapter(ayanamsa="unknown")
