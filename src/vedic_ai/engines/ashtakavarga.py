"""Ashtakavarga — Eight-source benefic point system.

Computes:
  BAV  : Bhinnashtakavarga (individual Ashtakavarga per planet, 8 reference sources)
  SAV  : Sarvashtakavarga (total bindus per sign, sum of all 7 BAVs)
  Trikona Shodhana : triangular reduction (optional; exposed for callers)
  Ekadhipatya Shodhana : dual-sign reduction (optional)

Bindu contribution tables from BPHS Ch.66-71 and B.V. Raman
'Ashtakavarga System of Prediction' (Raman, 4th ed.).

For each planet P, the table gives which houses (counted from each of 8
reference points: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Lagna)
receive a benefic point.

Reference: BPHS Ch.66-71; Ashtakavarga System of Prediction (B.V. Raman).
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi

# ---------------------------------------------------------------------------
# Bindu contribution tables (BPHS / B.V. Raman)
# Key: planet whose BAV is being computed
# Value: dict mapping reference point name → list of 1-based house offsets
#        from that reference point's sign that receive a bindu.
# ---------------------------------------------------------------------------

# Reference point keys (8 sources)
_REF_POINTS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"]

# Each entry: list of 1-based offsets FROM the reference sign that get a bindu
BINDU_TABLES: dict[str, dict[str, list[int]]] = {

    "Sun": {
        "Sun":     [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon":    [3, 6, 10, 11],
        "Mars":    [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus":   [6, 7, 12],
        "Saturn":  [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna":   [3, 4, 6, 10, 11, 12],
    },

    "Moon": {
        "Sun":     [3, 6, 7, 8, 10, 11],
        "Moon":    [1, 3, 6, 7, 10, 11],
        "Mars":    [2, 3, 5, 6, 9, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 10, 11, 12],
        "Venus":   [3, 4, 5, 7, 9, 10, 11],
        "Saturn":  [3, 5, 6, 11],
        "Lagna":   [3, 6, 10, 11],
    },

    "Mars": {
        "Sun":     [3, 5, 6, 10, 11],
        "Moon":    [3, 6, 11],
        "Mars":    [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus":   [6, 8, 11, 12],
        "Saturn":  [1, 4, 7, 8, 9, 10, 11],
        "Lagna":   [1, 3, 6, 10, 11],
    },

    "Mercury": {
        "Sun":     [5, 6, 9, 11, 12],
        "Moon":    [2, 4, 6, 8, 10, 11],
        "Mars":    [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus":   [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn":  [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna":   [1, 2, 4, 6, 8, 10, 11],
    },

    "Jupiter": {
        "Sun":     [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon":    [2, 5, 7, 9, 11],
        "Mars":    [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "Venus":   [2, 5, 6, 9, 10, 11],
        "Saturn":  [3, 5, 6, 12],
        "Lagna":   [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },

    "Venus": {
        "Sun":     [8, 11, 12],
        "Moon":    [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars":    [3, 4, 6, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus":   [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn":  [3, 4, 5, 8, 9, 10, 11],
        "Lagna":   [1, 2, 3, 4, 5, 8, 9, 11],
    },

    "Saturn": {
        "Sun":     [1, 2, 4, 7, 8, 10, 11],
        "Moon":    [3, 6, 11],
        "Mars":    [3, 5, 6, 10, 11, 12],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus":   [6, 11, 12],
        "Saturn":  [3, 5, 6, 11],
        "Lagna":   [1, 3, 4, 6, 10, 11],
    },
}

# Rasi → 0-based index
_RASI_LIST = list(Rasi)
_RASI_IDX: dict[Rasi, int] = {r: i for i, r in enumerate(_RASI_LIST)}


def _sign_index(bundle: ChartBundle, ref: str) -> int:
    """Return 0-based sign index for a reference point (planet or Lagna)."""
    if ref == "Lagna":
        return int(bundle.d1.ascendant_longitude / 30.0) % 12
    planet = bundle.d1.planets.get(ref)
    if planet is None:
        return 0
    return _RASI_IDX[planet.rasi.rasi]


def compute_bav(bundle: ChartBundle, planet: str) -> dict[str, int]:
    """Compute Bhinnashtakavarga (BAV) for one planet.

    Returns dict[rasi_name → bindu_count] (0–8 per sign).
    """
    table = BINDU_TABLES.get(planet)
    if table is None:
        return {r.value: 0 for r in Rasi}

    bindus = [0] * 12  # 0-indexed sign accumulator

    for ref, offsets in table.items():
        ref_idx = _sign_index(bundle, ref)
        for offset in offsets:
            target_idx = (ref_idx + offset - 1) % 12
            bindus[target_idx] += 1

    return {_RASI_LIST[i].value: bindus[i] for i in range(12)}


def compute_all_bavs(bundle: ChartBundle) -> dict[str, dict[str, int]]:
    """Compute BAV for all 7 planets (Sun through Saturn).

    Returns dict[planet_name → dict[rasi_name → bindu_count]].
    Rahu/Ketu are excluded from classical Ashtakavarga.
    """
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    return {p: compute_bav(bundle, p) for p in planets}


def compute_sav(bavs: dict[str, dict[str, int]]) -> dict[str, int]:
    """Compute Sarvashtakavarga (SAV) — total bindus per sign.

    SAV = sum of all 7 BAVs for each sign.
    Returns dict[rasi_name → total_bindus] (0–56 per sign).
    """
    sav: dict[str, int] = {r.value: 0 for r in Rasi}
    for planet_bav in bavs.values():
        for rasi_name, count in planet_bav.items():
            sav[rasi_name] += count
    return sav


def trikona_shodhana(bav: dict[str, int]) -> dict[str, int]:
    """Apply Trikona Shodhana (triangular reduction) to a BAV.

    For each of the four trikona groups (Aries/Leo/Sag, Taurus/Virgo/Cap,
    Gemini/Libra/Aqua, Cancer/Scorpio/Pisces), subtract the minimum bindu
    count from all three signs in that group.

    Source: BPHS Ch.72; Raman 'Ashtakavarga System' Ch.3.
    """
    _TRIKONA_GROUPS: list[list[str]] = [
        ["Aries", "Leo", "Sagittarius"],
        ["Taurus", "Virgo", "Capricorn"],
        ["Gemini", "Libra", "Aquarius"],
        ["Cancer", "Scorpio", "Pisces"],
    ]
    reduced = dict(bav)
    for group in _TRIKONA_GROUPS:
        min_val = min(reduced[r] for r in group)
        for r in group:
            reduced[r] -= min_val
    return reduced


def ekadhipatya_shodhana(
    bav: dict[str, int],
    bundle: ChartBundle,
) -> dict[str, int]:
    """Apply Ekadhipatya Shodhana (dual-lordship reduction) to a BAV.

    For planets ruling two signs (Mars, Mercury, Jupiter, Venus, Saturn),
    if both signs are unoccupied, subtract the lower from the higher.
    If only one is occupied, retain that sign's count and set the other's to
    the difference. (If both occupied, no reduction.)

    Source: BPHS Ch.72; Raman 'Ashtakavarga System' Ch.3.
    """
    _DUAL_LORDS: dict[str, list[str]] = {
        "Mars":    ["Aries", "Scorpio"],
        "Mercury": ["Gemini", "Virgo"],
        "Jupiter": ["Sagittarius", "Pisces"],
        "Venus":   ["Taurus", "Libra"],
        "Saturn":  ["Capricorn", "Aquarius"],
    }

    reduced = dict(bav)
    occupied_signs: set[str] = set()
    for planet_data in bundle.d1.planets.values():
        occupied_signs.add(planet_data.rasi.rasi.value)

    for _lord, signs in _DUAL_LORDS.items():
        s1, s2 = signs
        s1_occupied = s1 in occupied_signs
        s2_occupied = s2 in occupied_signs

        if not s1_occupied and not s2_occupied:
            lo, hi = (s1, s2) if reduced[s1] <= reduced[s2] else (s2, s1)
            diff = reduced[hi] - reduced[lo]
            reduced[hi] = diff
            reduced[lo] = 0
        elif s1_occupied and not s2_occupied:
            reduced[s2] = abs(reduced[s1] - reduced[s2])
        elif s2_occupied and not s1_occupied:
            reduced[s1] = abs(reduced[s1] - reduced[s2])
        # Both occupied: no change

    return reduced


def interpret_transit_bindus(planet: str, transit_sign: str, bav: dict[str, int]) -> dict:
    """Interpret transit quality for a planet moving through a sign.

    Args:
        planet       : planet name (must be in BINDU_TABLES)
        transit_sign : Rasi name the transiting planet occupies
        bav          : BAV dict for that planet (from compute_bav)

    Returns:
        bindu_count, quality label, interpretation text.
    """
    count = bav.get(transit_sign, 0)
    if count >= 7:
        quality, label = "Exceptional", f"{count}/8 — extremely auspicious transit"
    elif count >= 5:
        quality, label = "Excellent", f"{count}/8 — highly favourable"
    elif count >= 4:
        quality, label = "Favourable", f"{count}/8 — generally good"
    elif count == 3:
        quality, label = "Moderate", f"{count}/8 — mixed results"
    else:
        quality, label = "Unfavourable", f"{count}/8 — challenging; strengthen natal planet"

    return {
        "planet": planet,
        "transit_sign": transit_sign,
        "bindus": count,
        "quality": quality,
        "interpretation": label,
    }


def compute_ashtakavarga(bundle: ChartBundle, apply_shodhana: bool = False) -> dict:
    """Compute full Ashtakavarga analysis for the natal chart.

    Args:
        bundle           : ChartBundle
        apply_shodhana   : If True, apply both Trikona and Ekadhipatya Shodhana
                           to each BAV before computing SAV.

    Returns dict with:
        bav              : {planet: {rasi: bindu_count}} — raw BAVs
        bav_reduced      : same after Shodhana (only if apply_shodhana=True)
        sav              : {rasi: total_bindus} — Sarvashtakavarga
        sav_reduced      : same after Shodhana (only if apply_shodhana=True)
        planet_totals    : {planet: total bindus across all 12 signs}
        weak_signs       : signs with SAV ≤ 25 (challenging transits)
        strong_signs     : signs with SAV ≥ 30 (favourable transits)
        transit_guide    : for each planet, its current D1 sign bindu score
    """
    bavs = compute_all_bavs(bundle)

    if apply_shodhana:
        bavs_reduced = {}
        for planet, bav in bavs.items():
            b = trikona_shodhana(bav)
            b = ekadhipatya_shodhana(b, bundle)
            bavs_reduced[planet] = b
        sav_reduced = compute_sav(bavs_reduced)
    else:
        bavs_reduced = {}
        sav_reduced = {}

    sav = compute_sav(bavs)

    planet_totals = {p: sum(bav.values()) for p, bav in bavs.items()}

    weak_signs  = [r for r, c in sav.items() if c <= 25]
    strong_signs = [r for r, c in sav.items() if c >= 30]

    # Transit guide: current sign of each planet vs its BAV
    transit_guide: list[dict] = []
    for planet_name, bav in bavs.items():
        p = bundle.d1.planets.get(planet_name)
        if p is None:
            continue
        current_sign = p.rasi.rasi.value
        transit_guide.append(interpret_transit_bindus(planet_name, current_sign, bav))

    result: dict = {
        "bav": bavs,
        "sav": sav,
        "planet_totals": planet_totals,
        "weak_signs": weak_signs,
        "strong_signs": strong_signs,
        "transit_guide": transit_guide,
    }

    if apply_shodhana:
        result["bav_reduced"] = bavs_reduced
        result["sav_reduced"] = sav_reduced

    return result
