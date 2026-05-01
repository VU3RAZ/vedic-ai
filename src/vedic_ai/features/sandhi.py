"""Bhava Sandhi (sign boundary) and Bhava Madhya (sign centre) analysis.

Sandhi  : planet within _SANDHI_DEG of a sign boundary → transitional / weakened.
Madhya  : planet within _MADHYA_TOL of sign midpoint (15°) → fully expressed / strong.
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha

_SANDHI_DEG = 2.0       # degrees from sign boundary that counts as sandhi
_MADHYA_CENTER = 15.0   # midpoint of any sign
_MADHYA_TOL = 4.0       # ±4° of midpoint = bhava madhya zone


def compute_sandhi_analysis(bundle: ChartBundle) -> dict[str, dict]:
    """Classify each graha's cusp proximity.

    Returns a dict keyed by Graha name with:
        degree_in_sign      — raw degree within sign (0–30)
        is_sandhi           — True if < _SANDHI_DEG from sign boundary
        is_bhava_madhya     — True if within _MADHYA_TOL of 15°
        distance_from_cusp  — degrees from nearest sign boundary
        distance_from_center— degrees from 15° midpoint
        label               — human-readable: Sandhi (ingress/egress), Bhava Madhya, General
    """
    out: dict[str, dict] = {}
    for graha in Graha:
        deg = bundle.d1.planets[graha.value].rasi.degree_in_rasi
        dist_cusp = min(deg, 30.0 - deg)
        dist_center = abs(deg - _MADHYA_CENTER)
        is_sandhi = dist_cusp < _SANDHI_DEG
        is_madhya = dist_center < _MADHYA_TOL

        if is_sandhi:
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
            "distance_from_cusp": round(dist_cusp, 3),
            "distance_from_center": round(dist_center, 3),
            "label": label,
        }
    return out
