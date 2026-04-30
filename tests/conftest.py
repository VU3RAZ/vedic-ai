"""Shared pytest fixtures and ChartBundle factory functions.

Factory functions build valid ChartBundle objects programmatically.
The generator script (scripts/gen_fixtures.py) serialises these to JSON.
"""

from datetime import date, datetime, timezone

import pytest

from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.chart import ChartBundle, DivisionalChart
from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.domain.enums import Dignity, Graha, NakshatraName, Rasi
from vedic_ai.domain.house import HousePlacement
from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nak(name: NakshatraName, pada: int, lord: Graha, deg: float) -> NakshatraPlacement:
    return NakshatraPlacement(nakshatra=name, pada=pada, nakshatra_lord=lord, degree_in_nakshatra=deg)


def _planet(
    graha: Graha,
    longitude: float,
    rasi: Rasi,
    deg_in_rasi: float,
    nak: NakshatraPlacement,
    house: int,
    *,
    dignity: Dignity | None = None,
    is_retrograde: bool = False,
    speed: float = 1.0,
) -> PlanetPlacement:
    return PlanetPlacement(
        graha=graha,
        longitude=longitude,
        speed=-speed if is_retrograde else speed,
        is_retrograde=is_retrograde,
        rasi=RasiPlacement(rasi=rasi, degree_in_rasi=deg_in_rasi),
        nakshatra=nak,
        house=house,
        dignity=dignity,
    )


def _house(
    number: int, rasi: Rasi, cusp: float, lord: Graha, occupants: list[Graha] | None = None
) -> HousePlacement:
    return HousePlacement(number=number, rasi=rasi, cusp_longitude=cusp, lord=lord, occupants=occupants or [])


_FIXED_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Chart A — Aries lagna, exalted Sun, exalted Mars, exalted Jupiter
# ---------------------------------------------------------------------------

def build_chart_a() -> ChartBundle:
    """Aries lagna with prominent exalted planets — tests dignity detection."""
    birth = BirthData(
        birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone(offset=__import__("datetime").timedelta(hours=5, minutes=30))),
        location=GeoLocation(latitude=28.6139, longitude=77.2090, place_name="New Delhi, India"),
        name="Chart A — Exalted Sun",
    )
    planets = {
        Graha.SUN.value: _planet(Graha.SUN, 5.0, Rasi.ARIES, 5.0,
            _nak(NakshatraName.ASHWINI, 2, Graha.KETU, 5.0), 1, dignity=Dignity.EXALTED),
        Graha.MOON.value: _planet(Graha.MOON, 45.0, Rasi.TAURUS, 15.0,
            _nak(NakshatraName.ROHINI, 2, Graha.MOON, 5.0), 2),
        Graha.MARS.value: _planet(Graha.MARS, 294.0, Rasi.CAPRICORN, 24.0,
            _nak(NakshatraName.DHANISHTHA, 1, Graha.MARS, 0.67), 10, dignity=Dignity.EXALTED),
        Graha.MERCURY.value: _planet(Graha.MERCURY, 20.0, Rasi.ARIES, 20.0,
            _nak(NakshatraName.BHARANI, 3, Graha.VENUS, 6.67), 1),
        Graha.JUPITER.value: _planet(Graha.JUPITER, 95.0, Rasi.CANCER, 5.0,
            _nak(NakshatraName.PUSHYA, 1, Graha.SATURN, 1.67), 4, dignity=Dignity.EXALTED),
        Graha.VENUS.value: _planet(Graha.VENUS, 357.0, Rasi.PISCES, 27.0,
            _nak(NakshatraName.REVATI, 4, Graha.MERCURY, 10.33), 12, dignity=Dignity.EXALTED),
        Graha.SATURN.value: _planet(Graha.SATURN, 290.0, Rasi.CAPRICORN, 20.0,
            _nak(NakshatraName.SHRAVANA, 4, Graha.MOON, 10.0), 10),
        Graha.RAHU.value: _planet(Graha.RAHU, 70.0, Rasi.GEMINI, 10.0,
            _nak(NakshatraName.ARDRA, 1, Graha.RAHU, 3.33), 3, is_retrograde=True),
        Graha.KETU.value: _planet(Graha.KETU, 250.0, Rasi.SAGITTARIUS, 10.0,
            _nak(NakshatraName.MULA, 4, Graha.KETU, 10.0), 9, is_retrograde=True),
    }
    houses = {
        1: _house(1, Rasi.ARIES, 0.0, Graha.MARS, [Graha.SUN, Graha.MERCURY]),
        2: _house(2, Rasi.TAURUS, 30.0, Graha.VENUS, [Graha.MOON]),
        3: _house(3, Rasi.GEMINI, 60.0, Graha.MERCURY, [Graha.RAHU]),
        4: _house(4, Rasi.CANCER, 90.0, Graha.MOON, [Graha.JUPITER]),
        5: _house(5, Rasi.LEO, 120.0, Graha.SUN),
        6: _house(6, Rasi.VIRGO, 150.0, Graha.MERCURY),
        7: _house(7, Rasi.LIBRA, 180.0, Graha.VENUS),
        8: _house(8, Rasi.SCORPIO, 210.0, Graha.MARS),
        9: _house(9, Rasi.SAGITTARIUS, 240.0, Graha.JUPITER, [Graha.KETU]),
        10: _house(10, Rasi.CAPRICORN, 270.0, Graha.SATURN, [Graha.MARS, Graha.SATURN]),
        11: _house(11, Rasi.AQUARIUS, 300.0, Graha.SATURN),
        12: _house(12, Rasi.PISCES, 330.0, Graha.JUPITER, [Graha.VENUS]),
    }
    d1 = DivisionalChart(division="D1", ascendant_longitude=0.0, planets=planets, houses=houses)
    dashas = [DashaPeriod(graha=Graha.MOON, level=1, start_date=date(1990, 4, 5), end_date=date(2000, 4, 5))]
    return ChartBundle(birth=birth, engine="flatlib", ayanamsa="lahiri", d1=d1,
                       dashas=dashas, provenance={"source": "fixture"}, computed_at=_FIXED_TS)


# ---------------------------------------------------------------------------
# Chart B — Cancer lagna, Kemadruma yoga (Moon alone, H2/H12 empty)
# ---------------------------------------------------------------------------

def build_chart_b() -> ChartBundle:
    """Cancer lagna with Kemadruma yoga — Moon in H1, Leo (H2) and Gemini (H12) empty."""
    birth = BirthData(
        birth_datetime=datetime(1985, 6, 15, 8, 0, tzinfo=timezone(offset=__import__("datetime").timedelta(hours=5, minutes=30))),
        location=GeoLocation(latitude=19.0760, longitude=72.8777, place_name="Mumbai, India"),
        name="Chart B — Kemadruma Yoga",
    )
    planets = {
        Graha.SUN.value: _planet(Graha.SUN, 15.0, Rasi.ARIES, 15.0,
            _nak(NakshatraName.BHARANI, 1, Graha.VENUS, 1.67), 10),
        Graha.MOON.value: _planet(Graha.MOON, 100.0, Rasi.CANCER, 10.0,
            _nak(NakshatraName.PUSHYA, 3, Graha.SATURN, 6.67), 1),
        Graha.MARS.value: _planet(Graha.MARS, 215.0, Rasi.SCORPIO, 5.0,
            _nak(NakshatraName.ANURADHA, 1, Graha.SATURN, 1.67), 5),
        Graha.MERCURY.value: _planet(Graha.MERCURY, 55.0, Rasi.TAURUS, 25.0,
            _nak(NakshatraName.MRIGASHIRSHA, 1, Graha.MARS, 1.67), 11),
        Graha.JUPITER.value: _planet(Graha.JUPITER, 345.0, Rasi.PISCES, 15.0,
            _nak(NakshatraName.UTTARA_BHADRAPADA, 4, Graha.SATURN, 11.67), 9),
        Graha.VENUS.value: _planet(Graha.VENUS, 40.0, Rasi.TAURUS, 10.0,
            _nak(NakshatraName.ROHINI, 1, Graha.MOON, 0.0), 11),
        Graha.SATURN.value: _planet(Graha.SATURN, 285.0, Rasi.CAPRICORN, 15.0,
            _nak(NakshatraName.SHRAVANA, 2, Graha.MOON, 5.0), 7),
        Graha.RAHU.value: _planet(Graha.RAHU, 175.0, Rasi.VIRGO, 25.0,
            _nak(NakshatraName.CHITRA, 1, Graha.MARS, 1.67), 3, is_retrograde=True),
        Graha.KETU.value: _planet(Graha.KETU, 355.0, Rasi.PISCES, 25.0,
            _nak(NakshatraName.REVATI, 3, Graha.MERCURY, 8.33), 9, is_retrograde=True),
    }
    houses = {
        1: _house(1, Rasi.CANCER, 90.0, Graha.MOON, [Graha.MOON]),
        2: _house(2, Rasi.LEO, 120.0, Graha.SUN),           # empty → Kemadruma
        3: _house(3, Rasi.VIRGO, 150.0, Graha.MERCURY, [Graha.RAHU]),
        4: _house(4, Rasi.LIBRA, 180.0, Graha.VENUS),
        5: _house(5, Rasi.SCORPIO, 210.0, Graha.MARS, [Graha.MARS]),
        6: _house(6, Rasi.SAGITTARIUS, 240.0, Graha.JUPITER),
        7: _house(7, Rasi.CAPRICORN, 270.0, Graha.SATURN, [Graha.SATURN]),
        8: _house(8, Rasi.AQUARIUS, 300.0, Graha.SATURN),
        9: _house(9, Rasi.PISCES, 330.0, Graha.JUPITER, [Graha.JUPITER, Graha.KETU]),
        10: _house(10, Rasi.ARIES, 0.0, Graha.MARS, [Graha.SUN]),
        11: _house(11, Rasi.TAURUS, 30.0, Graha.VENUS, [Graha.MERCURY, Graha.VENUS]),
        12: _house(12, Rasi.GEMINI, 60.0, Graha.MERCURY),   # empty → Kemadruma
    }
    d1 = DivisionalChart(division="D1", ascendant_longitude=90.0, planets=planets, houses=houses)
    dashas = [DashaPeriod(graha=Graha.SATURN, level=1, start_date=date(1985, 6, 15), end_date=date(2004, 6, 15))]
    return ChartBundle(birth=birth, engine="flatlib", ayanamsa="lahiri", d1=d1,
                       dashas=dashas, provenance={"source": "fixture"}, computed_at=_FIXED_TS)


# ---------------------------------------------------------------------------
# Chart C — Libra lagna, balanced chart
# ---------------------------------------------------------------------------

def build_chart_c() -> ChartBundle:
    """Libra lagna, planets distributed across multiple houses."""
    birth = BirthData(
        birth_datetime=datetime(2000, 9, 22, 14, 0, tzinfo=timezone(offset=__import__("datetime").timedelta(hours=5, minutes=30))),
        location=GeoLocation(latitude=12.9716, longitude=77.5946, place_name="Bangalore, India"),
        name="Chart C — Balanced",
    )
    planets = {
        Graha.SUN.value: _planet(Graha.SUN, 183.0, Rasi.LIBRA, 3.0,
            _nak(NakshatraName.CHITRA, 3, Graha.MARS, 9.67), 1, dignity=Dignity.DEBILITATED),
        Graha.MOON.value: _planet(Graha.MOON, 225.0, Rasi.SCORPIO, 15.0,
            _nak(NakshatraName.ANURADHA, 4, Graha.SATURN, 11.67), 2),
        Graha.MARS.value: _planet(Graha.MARS, 70.0, Rasi.GEMINI, 10.0,
            _nak(NakshatraName.ARDRA, 1, Graha.RAHU, 3.33), 9),
        Graha.MERCURY.value: _planet(Graha.MERCURY, 170.0, Rasi.VIRGO, 20.0,
            _nak(NakshatraName.HASTA, 4, Graha.MOON, 10.0), 12, dignity=Dignity.OWN),
        Graha.JUPITER.value: _planet(Graha.JUPITER, 35.0, Rasi.TAURUS, 5.0,
            _nak(NakshatraName.KRITTIKA, 3, Graha.SUN, 8.33), 8),
        Graha.VENUS.value: _planet(Graha.VENUS, 200.0, Rasi.LIBRA, 20.0,
            _nak(NakshatraName.VISHAKHA, 1, Graha.JUPITER, 0.0), 1, dignity=Dignity.OWN),
        Graha.SATURN.value: _planet(Graha.SATURN, 40.0, Rasi.TAURUS, 10.0,
            _nak(NakshatraName.ROHINI, 1, Graha.MOON, 0.0), 8),
        Graha.RAHU.value: _planet(Graha.RAHU, 75.0, Rasi.GEMINI, 15.0,
            _nak(NakshatraName.ARDRA, 3, Graha.RAHU, 8.33), 9, is_retrograde=True),
        Graha.KETU.value: _planet(Graha.KETU, 255.0, Rasi.SAGITTARIUS, 15.0,
            _nak(NakshatraName.PURVA_ASHADHA, 1, Graha.VENUS, 1.67), 3, is_retrograde=True),
    }
    houses = {
        1: _house(1, Rasi.LIBRA, 180.0, Graha.VENUS, [Graha.SUN, Graha.VENUS]),
        2: _house(2, Rasi.SCORPIO, 210.0, Graha.MARS, [Graha.MOON]),
        3: _house(3, Rasi.SAGITTARIUS, 240.0, Graha.JUPITER, [Graha.KETU]),
        4: _house(4, Rasi.CAPRICORN, 270.0, Graha.SATURN),
        5: _house(5, Rasi.AQUARIUS, 300.0, Graha.SATURN),
        6: _house(6, Rasi.PISCES, 330.0, Graha.JUPITER),
        7: _house(7, Rasi.ARIES, 0.0, Graha.MARS),
        8: _house(8, Rasi.TAURUS, 30.0, Graha.VENUS, [Graha.JUPITER, Graha.SATURN]),
        9: _house(9, Rasi.GEMINI, 60.0, Graha.MERCURY, [Graha.MARS, Graha.RAHU]),
        10: _house(10, Rasi.CANCER, 90.0, Graha.MOON),
        11: _house(11, Rasi.LEO, 120.0, Graha.SUN),
        12: _house(12, Rasi.VIRGO, 150.0, Graha.MERCURY, [Graha.MERCURY]),
    }
    d1 = DivisionalChart(division="D1", ascendant_longitude=180.0, planets=planets, houses=houses)
    dashas = [DashaPeriod(graha=Graha.VENUS, level=1, start_date=date(2000, 9, 22), end_date=date(2020, 9, 22))]
    return ChartBundle(birth=birth, engine="flatlib", ayanamsa="lahiri", d1=d1,
                       dashas=dashas, provenance={"source": "fixture"}, computed_at=_FIXED_TS)


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chart_a() -> ChartBundle:
    return build_chart_a()


@pytest.fixture
def chart_b() -> ChartBundle:
    return build_chart_b()


@pytest.fixture
def chart_c() -> ChartBundle:
    return build_chart_c()
