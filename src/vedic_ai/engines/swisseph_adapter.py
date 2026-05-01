"""Primary calculation engine adapter backed by pyswisseph.

Uses the Swiss Ephemeris (Moshier built-in) for sidereal planet positions
with Lahiri ayanamsa and whole-sign houses by default.

Note: pyswisseph uses global mutable state via swe.set_sid_mode().
This is safe for single-threaded CLI use; avoid sharing instances across threads.
"""

from __future__ import annotations

import atexit
from datetime import datetime, timezone

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.chart import ChartBundle, DivisionalChart, TransitSnapshot
from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.engines.normalizer import normalize_engine_output
from vedic_ai.engines.vimshottari import compute_vimshottari_dashas

_AYANAMSA_MAP = {
    "lahiri": 1,        # swe.SIDM_LAHIRI
    "krishnamurti": 5,  # swe.SIDM_KRISHNAMURTI
    "raman": 3,         # swe.SIDM_RAMAN
}

_HOUSE_SYSTEM_MAP = {
    "whole_sign": b"W",
    "placidus": b"P",
}


def _import_swe():
    try:
        import swisseph as swe
        return swe
    except ImportError as exc:
        raise EngineError(
            "pyswisseph is not installed. Run: pip install pyswisseph"
        ) from exc


def _dt_to_jd(dt: datetime) -> float:
    """Convert a timezone-aware datetime to a Julian Day number (UT)."""
    dt_utc = dt.astimezone(timezone.utc)
    hour_frac = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    swe = _import_swe()
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_frac)


def _compute_raw_planets(swe, jd: float, node_type: str) -> dict:
    """Return raw planet dict keyed by Graha name."""
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

    _SWE_PLANETS = [
        ("Sun", swe.SUN),
        ("Moon", swe.MOON),
        ("Mars", swe.MARS),
        ("Mercury", swe.MERCURY),
        ("Jupiter", swe.JUPITER),
        ("Venus", swe.VENUS),
        ("Saturn", swe.SATURN),
    ]
    node_id = swe.MEAN_NODE if node_type == "mean" else swe.TRUE_NODE

    raw: dict = {}
    for name, pid in _SWE_PLANETS:
        result, ret = swe.calc_ut(jd, pid, flags)
        if ret < 0:
            raise EngineError(f"pyswisseph returned error for {name}: {ret}")
        raw[name] = {"longitude": result[0] % 360, "latitude": result[1], "speed": result[3]}

    rahu_result, ret = swe.calc_ut(jd, node_id, flags)
    if ret < 0:
        raise EngineError("pyswisseph returned error for Rahu")
    rahu_lon = rahu_result[0] % 360
    ketu_lon = (rahu_lon + 180.0) % 360
    raw["Rahu"] = {"longitude": rahu_lon, "latitude": 0.0, "speed": rahu_result[3]}
    raw["Ketu"] = {"longitude": ketu_lon, "latitude": 0.0, "speed": rahu_result[3]}

    return raw


def _setup_swe(swe, ayanamsa: str) -> None:
    sid_mode = _AYANAMSA_MAP.get(ayanamsa)
    if sid_mode is None:
        raise EngineError(f"Unknown ayanamsa {ayanamsa!r}. Choose: lahiri, krishnamurti, raman")
    swe.set_ephe_path(None)   # use built-in Moshier ephemeris
    swe.set_sid_mode(sid_mode, 0, 0)


class SwissEphAdapter:
    """AstrologyEngine implementation backed by pyswisseph."""

    def __init__(
        self,
        ayanamsa: str = "lahiri",
        house_system: str = "whole_sign",
        node_type: str = "mean",
    ) -> None:
        self.ayanamsa = ayanamsa
        self.house_system = house_system
        self.node_type = node_type
        self._swe = _import_swe()
        _setup_swe(self._swe, ayanamsa)
        atexit.register(self._swe.close)

    def _house_byte(self) -> bytes:
        hs = _HOUSE_SYSTEM_MAP.get(self.house_system)
        if hs is None:
            raise EngineError(
                f"Unknown house system {self.house_system!r}. Choose: whole_sign, placidus"
            )
        return hs

    def _compute_asc(self, jd: float, lat: float, lon: float) -> tuple[float, float]:
        """Return (ascendant_longitude, ayanamsa_value)."""
        try:
            houses, ascmc = self._swe.houses_ex(
                jd, lat, lon, self._house_byte(), self._swe.FLG_SIDEREAL
            )
            ayanamsa = self._swe.get_ayanamsa_ut(jd)
            return ascmc[0] % 360, ayanamsa
        except Exception as exc:
            raise EngineError(f"House calculation failed: {exc}") from exc

    def compute_birth_chart(
        self, birth: BirthData, options: dict | None = None
    ) -> ChartBundle:
        try:
            jd = _dt_to_jd(birth.birth_datetime)
            lat = birth.location.latitude
            lon = birth.location.longitude
            asc_lon, ayanamsa_val = self._compute_asc(jd, lat, lon)
            raw_planets = _compute_raw_planets(self._swe, jd, self.node_type)
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(f"Chart calculation failed: {exc}") from exc

        raw_output = {
            "engine": "swisseph",
            "ayanamsa": self.ayanamsa,
            "node_type": self.node_type,
            "ascendant_longitude": asc_lon,
            "ayanamsa_value": ayanamsa_val,
            "planets": raw_planets,
        }
        return normalize_engine_output(raw_output, birth, options)

    def compute_divisional_chart(
        self, birth: BirthData, division: str, options: dict | None = None
    ) -> DivisionalChart:
        d1 = self.compute_birth_chart(birth, options).d1
        if division == "D1":
            return d1
        from vedic_ai.engines.normalizer import build_varga_chart
        return build_varga_chart(d1, division)

    def compute_dashas(
        self, birth: BirthData, options: dict | None = None
    ) -> list[DashaPeriod]:
        try:
            jd = _dt_to_jd(birth.birth_datetime)
            flags = self._swe.FLG_SIDEREAL | self._swe.FLG_SPEED
            moon_result, _ = self._swe.calc_ut(jd, self._swe.MOON, flags)
            moon_lon = moon_result[0] % 360
        except Exception as exc:
            raise EngineError(f"Dasha calculation failed: {exc}") from exc

        return compute_vimshottari_dashas(moon_lon, birth.birth_datetime.date())

    def compute_transits(
        self, birth: BirthData, at_time: datetime, options: dict | None = None
    ) -> TransitSnapshot:
        try:
            jd = _dt_to_jd(at_time)
            raw_planets = _compute_raw_planets(self._swe, jd, self.node_type)
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(f"Transit calculation failed: {exc}") from exc

        from vedic_ai.engines.normalizer import (
            _build_planet_placement,
            _longitude_to_rasi,
        )
        from vedic_ai.domain.enums import Graha

        asc_rasi, _ = _longitude_to_rasi(0.0)  # transit: no ascendant context, use Aries
        planets = {
            g.value: _build_planet_placement(g, raw_planets[g.value], asc_rasi)
            for g in Graha
        }
        return TransitSnapshot(at_time=at_time, planets=planets)
