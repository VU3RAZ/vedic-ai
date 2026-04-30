"""Unit tests for the engine normalizer using pre-recorded mock raw output.

No pyswisseph call is made in these tests — the normalizer is exercised in
isolation with deterministic fixture data.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.enums import Dignity, Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS, compute_dignity
from vedic_ai.engines.normalizer import (
    _longitude_to_nakshatra,
    _longitude_to_rasi,
    _planet_house,
    normalize_engine_output,
)
from vedic_ai.engines.vimshottari import compute_vimshottari_dashas

# ---------------------------------------------------------------------------
# Pre-recorded raw output from pyswisseph for 1990-04-05 10:00 IST New Delhi
# ---------------------------------------------------------------------------
_BIRTH = BirthData(
    birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone(
        __import__("datetime").timedelta(hours=5, minutes=30)
    )),
    location=GeoLocation(latitude=28.6139, longitude=77.2090, place_name="New Delhi"),
    name="Test Chart",
)

_RAW_OUTPUT = {
    "engine": "swisseph",
    "ayanamsa": "lahiri",
    "node_type": "mean",
    "ascendant_longitude": 58.43,  # Taurus 28.43°
    "ayanamsa_value": 23.72,
    "planets": {
        "Sun":     {"longitude": 351.41, "latitude": 0.0,  "speed":  0.9845},
        "Moon":    {"longitude": 115.05, "latitude": 0.0,  "speed": 12.8081},
        "Mars":    {"longitude": 294.51, "latitude": 0.0,  "speed":  0.7464},
        "Mercury": {"longitude":   7.76, "latitude": 0.0,  "speed":  1.6794},
        "Jupiter": {"longitude":  69.50, "latitude": 0.0,  "speed":  0.1163},
        "Venus":   {"longitude": 305.05, "latitude": 0.0,  "speed":  1.0200},
        "Saturn":  {"longitude": 270.90, "latitude": 0.0,  "speed":  0.0474},
        "Rahu":    {"longitude": 289.75, "latitude": 0.0,  "speed": -0.0530},
        "Ketu":    {"longitude": 109.75, "latitude": 0.0,  "speed": -0.0530},
    },
}


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestLongitudeToRasi:
    def test_aries_start(self) -> None:
        rasi, deg = _longitude_to_rasi(0.0)
        assert rasi == Rasi.ARIES
        assert deg == pytest.approx(0.0)

    def test_taurus_boundary(self) -> None:
        rasi, deg = _longitude_to_rasi(30.0)
        assert rasi == Rasi.TAURUS
        assert deg == pytest.approx(0.0)

    def test_pisces_end(self) -> None:
        rasi, deg = _longitude_to_rasi(359.0)
        assert rasi == Rasi.PISCES
        assert deg == pytest.approx(29.0)

    def test_mid_sign(self) -> None:
        rasi, deg = _longitude_to_rasi(45.0)
        assert rasi == Rasi.TAURUS
        assert deg == pytest.approx(15.0)

    def test_sun_longitude(self) -> None:
        rasi, deg = _longitude_to_rasi(351.41)
        assert rasi == Rasi.PISCES
        assert deg == pytest.approx(21.41, abs=0.01)


class TestLongitudeToNakshatra:
    def test_ashwini_start(self) -> None:
        nak, pada, lord, deg = _longitude_to_nakshatra(0.0)
        from vedic_ai.domain.enums import NakshatraName
        assert nak == NakshatraName.ASHWINI
        assert pada == 1
        assert lord == Graha.KETU
        assert deg == pytest.approx(0.0)

    def test_boundary_within_nakshatra(self) -> None:
        # 13.4° is clearly inside Bharani (boundary is at 360/27 ≈ 13.333°)
        nak, pada, _, _ = _longitude_to_nakshatra(13.4)
        from vedic_ai.domain.enums import NakshatraName
        assert nak == NakshatraName.BHARANI

    def test_pada_progression(self) -> None:
        nak_span = 360 / 27
        pada_span = nak_span / 4
        _, pada, _, _ = _longitude_to_nakshatra(pada_span * 2)  # mid of pada 3
        assert pada == 3

    def test_all_27_nakshatras_covered(self) -> None:
        from vedic_ai.domain.enums import NakshatraName
        seen = set()
        for i in range(27):
            lon = i * (360 / 27) + 1.0
            nak, _, _, _ = _longitude_to_nakshatra(lon)
            seen.add(nak)
        assert seen == set(NakshatraName)


class TestPlanetHouse:
    def test_same_sign_is_house_1(self) -> None:
        assert _planet_house(Rasi.ARIES, Rasi.ARIES) == 1

    def test_next_sign_is_house_2(self) -> None:
        assert _planet_house(Rasi.TAURUS, Rasi.ARIES) == 2

    def test_opposite_sign_is_house_7(self) -> None:
        assert _planet_house(Rasi.LIBRA, Rasi.ARIES) == 7

    def test_wrap_around(self) -> None:
        # Pisces from Aries ascendant = house 12
        assert _planet_house(Rasi.PISCES, Rasi.ARIES) == 12

    def test_cancer_asc_capricorn_is_7(self) -> None:
        assert _planet_house(Rasi.CAPRICORN, Rasi.CANCER) == 7


# ---------------------------------------------------------------------------
# Dignity tests
# ---------------------------------------------------------------------------

class TestComputeDignity:
    def test_sun_exalted_in_aries(self) -> None:
        assert compute_dignity(Graha.SUN, Rasi.ARIES, 10.0) == Dignity.EXALTED

    def test_sun_debilitated_in_libra(self) -> None:
        assert compute_dignity(Graha.SUN, Rasi.LIBRA, 10.0) == Dignity.DEBILITATED

    def test_sun_moolatrikona_in_leo(self) -> None:
        assert compute_dignity(Graha.SUN, Rasi.LEO, 10.0) == Dignity.MOOLATRIKONA

    def test_sun_own_in_leo_outside_moolatrikona(self) -> None:
        # Leo 21° is beyond moolatrikona range (0-20°)
        assert compute_dignity(Graha.SUN, Rasi.LEO, 21.0) == Dignity.OWN

    def test_moon_exalted_in_taurus(self) -> None:
        assert compute_dignity(Graha.MOON, Rasi.TAURUS, 3.0) == Dignity.EXALTED

    def test_mars_exalted_in_capricorn(self) -> None:
        assert compute_dignity(Graha.MARS, Rasi.CAPRICORN, 28.0) == Dignity.EXALTED

    def test_saturn_exalted_in_libra(self) -> None:
        assert compute_dignity(Graha.SATURN, Rasi.LIBRA, 20.0) == Dignity.EXALTED

    def test_venus_own_in_taurus(self) -> None:
        assert compute_dignity(Graha.VENUS, Rasi.TAURUS, 10.0) == Dignity.OWN

    def test_neutral_returns_none(self) -> None:
        # Sun in Pisces has no special dignity
        assert compute_dignity(Graha.SUN, Rasi.PISCES, 10.0) is None

    def test_rasi_lords_all_present(self) -> None:
        assert set(RASI_LORDS.keys()) == set(Rasi)


# ---------------------------------------------------------------------------
# Vimshottari dasha tests
# ---------------------------------------------------------------------------

class TestVimshottariDashas:
    def test_returns_list_of_dasha_periods(self) -> None:
        from datetime import date
        dashas = compute_vimshottari_dashas(115.05, date(1990, 4, 5))
        assert len(dashas) > 0

    def test_dashas_are_non_overlapping(self) -> None:
        from datetime import date
        dashas = compute_vimshottari_dashas(115.05, date(1990, 4, 5))
        for i in range(len(dashas) - 1):
            assert dashas[i].end_date == dashas[i + 1].start_date

    def test_first_dasha_starts_at_birth(self) -> None:
        from datetime import date
        birth = date(1990, 4, 5)
        dashas = compute_vimshottari_dashas(115.05, birth)
        assert dashas[0].start_date == birth

    def test_all_dashas_are_level_1(self) -> None:
        from datetime import date
        dashas = compute_vimshottari_dashas(115.05, date(1990, 4, 5))
        assert all(d.level == 1 for d in dashas)

    def test_moon_in_rohini_starts_moon_dasha(self) -> None:
        from datetime import date
        # Rohini nakshatra: 40-53.33° — lord = Moon
        dashas = compute_vimshottari_dashas(45.0, date(2000, 1, 1))
        assert dashas[0].graha == Graha.MOON

    def test_span_covers_120_years(self) -> None:
        from datetime import date
        birth = date(1990, 4, 5)
        dashas = compute_vimshottari_dashas(115.05, birth)
        last_end = max(d.end_date for d in dashas)
        years_covered = (last_end - birth).days / 365.25
        assert years_covered >= 119


# ---------------------------------------------------------------------------
# normalize_engine_output tests
# ---------------------------------------------------------------------------

class TestNormalizeEngineOutput:
    def test_returns_chart_bundle(self) -> None:
        from vedic_ai.domain.chart import ChartBundle
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert isinstance(bundle, ChartBundle)

    def test_all_nine_grahas_present(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert set(bundle.d1.planets.keys()) == {g.value for g in Graha}

    def test_twelve_houses_present(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert set(bundle.d1.houses.keys()) == set(range(1, 13))

    def test_ascendant_in_taurus(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert bundle.d1.ascendant_longitude == pytest.approx(58.43)
        # First house should be Taurus
        assert bundle.d1.houses[1].rasi == Rasi.TAURUS

    def test_sun_in_pisces(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert bundle.d1.planets[Graha.SUN.value].rasi.rasi == Rasi.PISCES

    def test_rahu_is_retrograde(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert bundle.d1.planets[Graha.RAHU.value].is_retrograde is True

    def test_ketu_is_retrograde(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert bundle.d1.planets[Graha.KETU.value].is_retrograde is True

    def test_rahu_ketu_opposite(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        rahu_lon = bundle.d1.planets[Graha.RAHU.value].longitude
        ketu_lon = bundle.d1.planets[Graha.KETU.value].longitude
        diff = abs(rahu_lon - ketu_lon)
        assert diff == pytest.approx(180.0, abs=0.1)

    def test_house_lords_correct(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        # H1 = Taurus → lord = Venus
        assert bundle.d1.houses[1].lord == Graha.VENUS
        # H7 = Scorpio → lord = Mars
        assert bundle.d1.houses[7].lord == Graha.MARS

    def test_occupants_match_house_numbers(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        for h, house in bundle.d1.houses.items():
            for graha in house.occupants:
                assert bundle.d1.planets[graha.value].house == h

    def test_missing_graha_raises_engine_error(self) -> None:
        bad = dict(_RAW_OUTPUT)
        bad["planets"] = {k: v for k, v in _RAW_OUTPUT["planets"].items() if k != "Sun"}
        with pytest.raises(EngineError, match="missing grahas"):
            normalize_engine_output(bad, _BIRTH)

    def test_engine_and_ayanamsa_fields_preserved(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert bundle.engine == "swisseph"
        assert bundle.ayanamsa == "lahiri"

    def test_birth_data_attached(self) -> None:
        bundle = normalize_engine_output(_RAW_OUTPUT, _BIRTH)
        assert bundle.birth.name == "Test Chart"
