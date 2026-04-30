"""Normalizer: converts raw engine output dict into a canonical ChartBundle.

The raw dict format (produced by any engine adapter):
{
    "ascendant_longitude": float,   # sidereal, 0-360
    "ayanamsa_value": float,        # degrees subtracted from tropical
    "engine": str,
    "ayanamsa": str,
    "node_type": str,               # "mean" | "true"
    "planets": {
        "<GrahaName>": {
            "longitude": float,     # sidereal, 0-360
            "latitude": float,
            "speed": float,         # degrees/day; negative = retrograde
        },
        ...
    }
}
"""

from datetime import datetime, timezone

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.chart import ChartBundle, DivisionalChart
from vedic_ai.domain.enums import Graha, NakshatraName, Rasi
from vedic_ai.domain.house import HousePlacement
from vedic_ai.domain.nakshatra import NAKSHATRA_DATA
from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement
from vedic_ai.engines.dignity import RASI_LORDS, compute_dignity

_RASI_SEQUENCE: list[Rasi] = list(Rasi)
_NAKSHATRA_SEQUENCE: list[NakshatraName] = list(NakshatraName)

_NAK_SPAN = 360.0 / 27.0   # ≈ 13.333°
_PADA_SPAN = _NAK_SPAN / 4.0  # ≈ 3.333°


def _longitude_to_rasi(longitude: float) -> tuple[Rasi, float]:
    """Return (rasi, degree_in_rasi) for a sidereal longitude."""
    idx = int(longitude / 30.0) % 12
    degree = longitude % 30.0
    return _RASI_SEQUENCE[idx], degree


def _longitude_to_nakshatra(longitude: float) -> tuple[NakshatraName, int, Graha, float]:
    """Return (nakshatra, pada, nakshatra_lord, degree_in_nakshatra)."""
    idx = int(longitude / _NAK_SPAN) % 27
    deg_in_nak = longitude % _NAK_SPAN
    pada = min(int(deg_in_nak / _PADA_SPAN) + 1, 4)
    nak_name = _NAKSHATRA_SEQUENCE[idx]
    nak_lord = NAKSHATRA_DATA[nak_name].lord
    return nak_name, pada, nak_lord, deg_in_nak


def _planet_house(planet_rasi: Rasi, asc_rasi: Rasi) -> int:
    """Compute house number in whole-sign system."""
    planet_idx = _RASI_SEQUENCE.index(planet_rasi)
    asc_idx = _RASI_SEQUENCE.index(asc_rasi)
    return (planet_idx - asc_idx) % 12 + 1


def _build_planet_placement(
    graha: Graha,
    raw: dict,
    asc_rasi: Rasi,
) -> PlanetPlacement:
    lon = float(raw["longitude"])
    lat = float(raw.get("latitude", 0.0))
    speed = float(raw.get("speed", 0.0))
    is_retrograde = speed < 0 or graha in (Graha.RAHU, Graha.KETU)

    rasi, deg_in_rasi = _longitude_to_rasi(lon)
    nak_name, pada, nak_lord, deg_in_nak = _longitude_to_nakshatra(lon)
    dignity = compute_dignity(graha, rasi, deg_in_rasi)
    house = _planet_house(rasi, asc_rasi)

    return PlanetPlacement(
        graha=graha,
        longitude=lon,
        latitude=lat,
        speed=speed,
        is_retrograde=is_retrograde,
        rasi=RasiPlacement(rasi=rasi, degree_in_rasi=deg_in_rasi),
        nakshatra=NakshatraPlacement(
            nakshatra=nak_name,
            pada=pada,
            nakshatra_lord=nak_lord,
            degree_in_nakshatra=deg_in_nak,
        ),
        house=house,
        dignity=dignity,
    )


def _build_houses(asc_rasi: Rasi, planets: dict[str, PlanetPlacement]) -> dict[int, HousePlacement]:
    asc_idx = _RASI_SEQUENCE.index(asc_rasi)
    occupants_by_house: dict[int, list[Graha]] = {h: [] for h in range(1, 13)}
    for placement in planets.values():
        occupants_by_house[placement.house].append(placement.graha)

    houses: dict[int, HousePlacement] = {}
    for h in range(1, 13):
        rasi_idx = (asc_idx + h - 1) % 12
        rasi = _RASI_SEQUENCE[rasi_idx]
        cusp = rasi_idx * 30.0
        lord = RASI_LORDS[rasi]
        houses[h] = HousePlacement(
            number=h,
            rasi=rasi,
            cusp_longitude=cusp,
            lord=lord,
            occupants=occupants_by_house[h],
        )
    return houses


def normalize_engine_output(
    raw_output: dict,
    birth: BirthData,
    options: dict | None = None,
) -> ChartBundle:
    """Transform a raw engine output dict into a canonical ChartBundle.

    Raises:
        EngineError: If a required graha is missing or data is malformed.
    """
    try:
        asc_lon = float(raw_output["ascendant_longitude"])
        asc_rasi, _ = _longitude_to_rasi(asc_lon)

        raw_planets: dict = raw_output.get("planets", {})
        required = {g.value for g in Graha}
        missing = required - set(raw_planets.keys())
        if missing:
            raise EngineError(f"Engine output missing grahas: {missing}")

        planets: dict[str, PlanetPlacement] = {}
        for graha in Graha:
            planets[graha.value] = _build_planet_placement(
                graha, raw_planets[graha.value], asc_rasi
            )

        houses = _build_houses(asc_rasi, planets)
        d1 = DivisionalChart(
            division="D1",
            ascendant_longitude=asc_lon,
            planets=planets,
            houses=houses,
        )
        return ChartBundle(
            birth=birth,
            engine=str(raw_output.get("engine", "unknown")),
            ayanamsa=str(raw_output.get("ayanamsa", "lahiri")),
            node_type=str(raw_output.get("node_type", "mean")),
            d1=d1,
            provenance={
                "ayanamsa_value": raw_output.get("ayanamsa_value"),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except EngineError:
        raise
    except Exception as exc:
        raise EngineError(f"Normalization failed: {exc}") from exc
