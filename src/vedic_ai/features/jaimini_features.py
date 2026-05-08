"""Jaimini astrology feature computation.

Computes Chara Karakas, Arudha Lagna (and all 12 Arudha Padas),
Karakamsha Lagna, and Upapada Lagna from a ChartBundle.
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS

# Rasi → integer index (1-based, Aries=1)
_RASI_INDEX: dict[str, int] = {
    "Aries": 1, "Taurus": 2, "Gemini": 3, "Cancer": 4,
    "Leo": 5, "Virgo": 6, "Libra": 7, "Scorpio": 8,
    "Sagittarius": 9, "Capricorn": 10, "Aquarius": 11, "Pisces": 12,
}
_INDEX_RASI: dict[int, str] = {v: k for k, v in _RASI_INDEX.items()}

# Planets eligible for Chara Karaka (exclude Rahu in 7-karaka scheme)
_CK_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]
_CK_NAMES = ["Atmakaraka", "Amatyakaraka", "Bhratrukaraka", "Matrukaraka",
             "Pitrukaraka", "Putrakaraka", "Gnatikaraka", "Darakaraka"]
_CK_ABBR  = ["AK", "AmK", "BK", "MK", "PK", "PuK", "GK", "DK"]


def _rasi_lord(rasi_name: str) -> str:
    """Return the lord planet name for a sign."""
    rasi_enum = Rasi(rasi_name)
    lord_enum = RASI_LORDS[rasi_enum]
    return lord_enum.value


def _count_signs_forward(from_rasi: str, to_rasi: str) -> int:
    """Count signs forward (inclusive) from from_rasi to to_rasi."""
    f = _RASI_INDEX[from_rasi]
    t = _RASI_INDEX[to_rasi]
    return ((t - f) % 12) + 1


def _count_signs_backward(from_rasi: str, to_rasi: str) -> int:
    """Count signs backward (inclusive) from from_rasi to to_rasi."""
    f = _RASI_INDEX[from_rasi]
    t = _RASI_INDEX[to_rasi]
    return ((f - t) % 12) + 1


def _sign_from(start_rasi: str, count: int) -> str:
    """Return the sign reached by counting `count` signs forward from start_rasi."""
    start_idx = _RASI_INDEX[start_rasi]
    result_idx = ((start_idx - 1 + count) % 12) + 1
    return _INDEX_RASI[result_idx]


def _compute_arudha(house_rasi: str, lord_rasi: str) -> str:
    """Compute the Arudha Pada for a house.

    Count signs from house_rasi to lord_rasi (forward), then same count
    forward from lord_rasi. Apply special rules: if result = house_rasi,
    use 10th from it; if result = 7th from house_rasi, use 4th from it.
    """
    count = _count_signs_forward(house_rasi, lord_rasi)
    result = _sign_from(lord_rasi, count)

    # Special rule 1: result falls in the same sign as the house
    if result == house_rasi:
        result = _sign_from(house_rasi, 10)

    # Special rule 2: result falls in 7th from house
    seventh = _sign_from(house_rasi, 7)
    if result == seventh:
        result = _sign_from(house_rasi, 4)

    return result


def compute_chara_karakas(bundle: ChartBundle) -> dict:
    """Compute Chara Karakas using the 8-karaka scheme (including Rahu).

    Returns a dict with:
      - karakas: list of {abbr, name, planet, degree_in_sign}
      - planet_to_karaka: {planet_name: abbr}
    """
    placements = []
    for pname in _CK_PLANETS:
        pp = bundle.d1.planets.get(pname)
        if pp is None:
            continue
        deg = pp.rasi.degree_in_rasi
        # Rahu: subtract from 30 before ranking (Jaimini convention)
        if pname == "Rahu":
            deg = 30.0 - deg
        placements.append((pname, deg))

    # Sort descending by degree-in-sign
    placements.sort(key=lambda x: x[1], reverse=True)

    karakas = []
    planet_to_karaka: dict[str, str] = {}
    for i, (pname, deg) in enumerate(placements):
        if i >= len(_CK_NAMES):
            break
        karakas.append({
            "abbr": _CK_ABBR[i],
            "name": _CK_NAMES[i],
            "planet": pname,
            "degree_in_sign": round(deg, 4),
        })
        planet_to_karaka[pname] = _CK_ABBR[i]

    return {"karakas": karakas, "planet_to_karaka": planet_to_karaka}


def compute_karakamsha(bundle: ChartBundle, chara_karakas: dict) -> dict:
    """Compute Karakamsha Lagna — the D1 house corresponding to AK's navamsha sign.

    Returns {navamsha_sign, d1_house, description}
    """
    ak_entry = next((k for k in chara_karakas["karakas"] if k["abbr"] == "AK"), None)
    if ak_entry is None:
        return {"navamsha_sign": None, "d1_house": None, "description": "AK not found"}

    ak_planet = ak_entry["planet"]
    d9 = bundle.vargas.get("D9")
    if d9 is None:
        return {"navamsha_sign": None, "d1_house": None, "description": "D9 not computed"}

    ak_d9 = d9.planets.get(ak_planet)
    if ak_d9 is None:
        return {"navamsha_sign": None, "d1_house": None, "description": "AK not in D9"}

    navamsha_sign = ak_d9.rasi.rasi.value
    d1_house = ak_d9.house  # D9 house corresponds to D1 house in whole-sign
    return {
        "navamsha_sign": navamsha_sign,
        "d1_house": d1_house,
        "ak_planet": ak_planet,
        "description": f"{ak_planet} (AK) in {navamsha_sign} navamsha — Karakamsha in house {d1_house}",
    }


def compute_arudha_padas(bundle: ChartBundle) -> dict:
    """Compute all 12 Arudha Padas (A1–A12).

    Returns {
      "AL": sign,  # Arudha Lagna (A1)
      "UL": sign,  # Upapada Lagna (A12)
      "padas": [{"pada": "A1", "house": 1, "sign": "..."}, ...]
    }
    """
    houses_data = bundle.d1.houses
    padas = []

    for h in range(1, 13):
        hd = houses_data.get(h)
        if hd is None:
            continue
        house_rasi = hd.rasi.value if hasattr(hd.rasi, "value") else str(hd.rasi)
        lord_name = _rasi_lord(house_rasi)
        lord_pp = bundle.d1.planets.get(lord_name)
        if lord_pp is None:
            continue
        lord_rasi = lord_pp.rasi.rasi.value
        arudha_sign = _compute_arudha(house_rasi, lord_rasi)
        padas.append({
            "pada": f"A{h}",
            "house": h,
            "house_sign": house_rasi,
            "lord": lord_name,
            "lord_sign": lord_rasi,
            "arudha_sign": arudha_sign,
        })

    al = next((p["arudha_sign"] for p in padas if p["house"] == 1), None)
    ul = next((p["arudha_sign"] for p in padas if p["house"] == 12), None)

    return {"AL": al, "UL": ul, "padas": padas}


def compute_jaimini_rasi_aspects(bundle: ChartBundle) -> dict[int, list[str]]:
    """Compute which planets aspect each house via Jaimini Rasi Drishti.

    Moveable signs aspect all fixed signs except adjacent; fixed signs aspect
    all moveable signs except adjacent; dual signs aspect all other dual signs.
    Returns {house_num: [planet_names_aspecting_via_rasi_drishti]}
    """
    _MOVEABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
    _FIXED    = {"Taurus", "Leo", "Scorpio", "Aquarius"}
    _DUAL     = {"Gemini", "Virgo", "Sagittarius", "Pisces"}

    def aspects_of(sign: str) -> set[str]:
        idx = _RASI_INDEX[sign]
        if sign in _MOVEABLE:
            targets = _FIXED - {_INDEX_RASI[((idx) % 12) + 1]}  # exclude adjacent fixed
            return targets
        if sign in _FIXED:
            targets = _MOVEABLE - {_INDEX_RASI[((idx) % 12) + 1]}  # exclude adjacent moveable
            return targets
        if sign in _DUAL:
            return _DUAL - {sign}
        return set()

    houses_data = bundle.d1.houses
    result: dict[int, list[str]] = {h: [] for h in range(1, 13)}

    for pname, pp in bundle.d1.planets.items():
        planet_sign = pp.rasi.rasi.value
        aspected_signs = aspects_of(planet_sign)
        for h, hd in houses_data.items():
            house_sign = hd.rasi.value if hasattr(hd.rasi, "value") else str(hd.rasi)
            if house_sign in aspected_signs:
                result[h].append(pname)

    return result


def compute_jaimini_features(bundle: ChartBundle) -> dict:
    """Aggregate all Jaimini features into a single dict."""
    ck = compute_chara_karakas(bundle)
    km = compute_karakamsha(bundle, ck)
    ap = compute_arudha_padas(bundle)
    rasi_aspects = compute_jaimini_rasi_aspects(bundle)

    return {
        "chara_karakas": ck["karakas"],
        "planet_to_karaka": ck["planet_to_karaka"],
        "karakamsha": km,
        "arudha_padas": ap["padas"],
        "arudha_lagna": ap["AL"],
        "upapada_lagna": ap["UL"],
        "rasi_drishti_on_houses": rasi_aspects,
    }
