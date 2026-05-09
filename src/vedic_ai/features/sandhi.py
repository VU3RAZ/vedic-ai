"""Bhava Sandhi, Bhava Madhya, and Gandanta analysis.

Sandhi   : planet within _SANDHI_DEG of a sign boundary → transitional / weakened.
Madhya   : planet within _MADHYA_TOL of sign midpoint (15°) → fully expressed / strong.
Gandanta : planet in the junction zone between a water sign (Cancer/Scorpio/Pisces)
           and the following fire sign (Leo/Sagittarius/Aries). The zone spans
           last 3°20' of the water sign and first 3°20' of the fire sign.
           Gandanta is a strongly malefic position indicating karmic burdens.
           Source: BPHS Ch.3; Uttara Kalamrita; Phaladeepika Ch.2.
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi

_SANDHI_DEG = 2.0       # degrees from sign boundary that counts as sandhi
_MADHYA_CENTER = 15.0   # midpoint of any sign
_MADHYA_TOL = 4.0       # ±4° of midpoint = bhava madhya zone
_GANDANTA_DEG = 3.333   # 3°20' — Gandanta zone on each side of water/fire junction

# Water signs whose egress (last 3°20') is Gandanta
_GANDANTA_WATER: frozenset[Rasi] = frozenset({Rasi.CANCER, Rasi.SCORPIO, Rasi.PISCES})
# Fire signs whose ingress (first 3°20') is Gandanta
_GANDANTA_FIRE: frozenset[Rasi] = frozenset({Rasi.ARIES, Rasi.LEO, Rasi.SAGITTARIUS})


def _is_gandanta(rasi: Rasi, degree_in_rasi: float) -> tuple[bool, str]:
    """Return (is_gandanta, side) where side is 'water_egress' or 'fire_ingress'."""
    if rasi in _GANDANTA_WATER and degree_in_rasi >= (30.0 - _GANDANTA_DEG):
        return True, "water_egress"
    if rasi in _GANDANTA_FIRE and degree_in_rasi <= _GANDANTA_DEG:
        return True, "fire_ingress"
    return False, ""


def compute_sandhi_analysis(bundle: ChartBundle) -> dict[str, dict]:
    """Classify each graha's cusp proximity, including Gandanta detection.

    Returns a dict keyed by Graha name with:
        degree_in_sign      — raw degree within sign (0–30)
        is_sandhi           — True if < _SANDHI_DEG from sign boundary
        is_bhava_madhya     — True if within _MADHYA_TOL of 15°
        is_gandanta         — True if in water/fire junction zone (3°20')
        gandanta_side       — 'water_egress' | 'fire_ingress' | ''
        distance_from_cusp  — degrees from nearest sign boundary
        distance_from_center— degrees from 15° midpoint
        label               — human-readable classification
    """
    out: dict[str, dict] = {}
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        deg = p.rasi.degree_in_rasi
        rasi = p.rasi.rasi
        dist_cusp = min(deg, 30.0 - deg)
        dist_center = abs(deg - _MADHYA_CENTER)
        is_sandhi = dist_cusp < _SANDHI_DEG
        is_madhya = dist_center < _MADHYA_TOL
        is_gandanta, gandanta_side = _is_gandanta(rasi, deg)

        if is_gandanta:
            label = f"Gandanta ({gandanta_side})"
        elif is_sandhi:
            side = "ingress" if deg < 15 else "egress"
            label = f"Sandhi ({side})"
        elif is_madhya:
            label = "Bhava Madhya"
        else:
            label = "General"

        out[graha.value] = {
            "degree_in_sign": round(deg, 3),
            "is_sandhi": is_sandhi,
            "is_bhava_madhya": is_madhya,
            "is_gandanta": is_gandanta,
            "gandanta_side": gandanta_side,
            "distance_from_cusp": round(dist_cusp, 3),
            "distance_from_center": round(dist_center, 3),
            "label": label,
        }
    return out


def compute_gandanta_flags(bundle: ChartBundle) -> dict:
    """Summarise Gandanta placements across the chart.

    Returns:
        gandanta_planets  : list of planet names in Gandanta
        lagna_gandanta    : True if Ascendant is in Gandanta
        details           : per-planet Gandanta detail dicts
    """
    asc_lon = bundle.d1.ascendant_longitude
    asc_deg_in_rasi = asc_lon % 30.0
    asc_rasi_idx = int(asc_lon / 30.0)
    rasi_list = list(Rasi)
    asc_rasi = rasi_list[asc_rasi_idx % 12]

    lagna_gandanta, lagna_side = _is_gandanta(asc_rasi, asc_deg_in_rasi)

    gandanta_planets: list[str] = []
    details: list[dict] = []
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        is_g, g_side = _is_gandanta(p.rasi.rasi, p.rasi.degree_in_rasi)
        if is_g:
            gandanta_planets.append(graha.value)
            details.append({
                "graha": graha.value,
                "rasi": p.rasi.rasi.value,
                "degree_in_rasi": round(p.rasi.degree_in_rasi, 3),
                "gandanta_side": g_side,
                "house": p.house,
                "interpretation": (
                    f"{graha.value} in Gandanta ({g_side}) at {p.rasi.degree_in_rasi:.2f}° "
                    f"{p.rasi.rasi.value} — karmic stress; planet's significations under strain."
                ),
            })

    return {
        "gandanta_planets": gandanta_planets,
        "lagna_gandanta": lagna_gandanta,
        "lagna_gandanta_side": lagna_side,
        "details": details,
        "summary": (
            f"{len(gandanta_planets)} planet(s) in Gandanta: {', '.join(gandanta_planets)}"
            if gandanta_planets else "No planets in Gandanta."
        ),
    }
