"""Rashi Drishti (Jaimini sign aspects) and full drishti matrix.

Graha Drishti is already computed in aspects.py.
This module adds:
  1. Rashi Drishti: sign-to-sign aspects per Jaimini principles
  2. Full drishti matrix: combined graha + rashi drishti per house
  3. Aspect strength summary per house

Rashi Drishti rules (classical Jaimini):
  - Moveable (Chara) signs aspect all Fixed signs except the one immediately following
  - Fixed (Sthira) signs aspect all Moveable signs except the one immediately preceding
  - Dual (Dwiswabhava) signs aspect all other Dual signs
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi

_RASI_SEQUENCE: list[Rasi] = list(Rasi)

# Rashi Drishti lookup table — each sign → frozenset of signs it aspects
_RASHI_DRISHTI: dict[Rasi, frozenset[Rasi]] = {
    # Moveable → Fixed (all except immediately following fixed sign)
    Rasi.ARIES:       frozenset({Rasi.LEO, Rasi.SCORPIO, Rasi.AQUARIUS}),
    Rasi.CANCER:      frozenset({Rasi.SCORPIO, Rasi.AQUARIUS, Rasi.TAURUS}),
    Rasi.LIBRA:       frozenset({Rasi.AQUARIUS, Rasi.TAURUS, Rasi.LEO}),
    Rasi.CAPRICORN:   frozenset({Rasi.TAURUS, Rasi.LEO, Rasi.SCORPIO}),
    # Fixed → Moveable (all except immediately preceding moveable sign)
    Rasi.TAURUS:      frozenset({Rasi.CANCER, Rasi.LIBRA, Rasi.CAPRICORN}),
    Rasi.LEO:         frozenset({Rasi.LIBRA, Rasi.CAPRICORN, Rasi.ARIES}),
    Rasi.SCORPIO:     frozenset({Rasi.CAPRICORN, Rasi.ARIES, Rasi.CANCER}),
    Rasi.AQUARIUS:    frozenset({Rasi.ARIES, Rasi.CANCER, Rasi.LIBRA}),
    # Dual → all other Dual signs
    Rasi.GEMINI:      frozenset({Rasi.VIRGO, Rasi.SAGITTARIUS, Rasi.PISCES}),
    Rasi.VIRGO:       frozenset({Rasi.GEMINI, Rasi.SAGITTARIUS, Rasi.PISCES}),
    Rasi.SAGITTARIUS: frozenset({Rasi.GEMINI, Rasi.VIRGO, Rasi.PISCES}),
    Rasi.PISCES:      frozenset({Rasi.GEMINI, Rasi.VIRGO, Rasi.SAGITTARIUS}),
}

# Sign quality for each rasi
_SIGN_TYPE: dict[Rasi, str] = {
    r: ("moveable" if _RASI_SEQUENCE.index(r) % 3 == 0
        else ("fixed" if _RASI_SEQUENCE.index(r) % 3 == 1 else "dual"))
    for r in Rasi
}


def compute_rashi_drishti(bundle: ChartBundle) -> dict:
    """Compute Jaimini Rashi Drishti (sign-to-sign aspects) for the natal chart.

    Returns:
        rashi_aspects        : dict[rasi_name → list of rasi names it aspects]
        house_aspects        : dict[house_number → list of house numbers it aspects via rashi drishti]
        aspected_by_house    : dict[house_number → list of house numbers aspecting it]
        house_graha_drishti  : dict[house_number → list of graha-aspect detail dicts]
                               (grahas in signs that cast rashi drishti on that house)
    """
    houses = bundle.d1.houses
    planets = bundle.d1.planets

    house_rasi: dict[int, Rasi] = {h: houses[h].rasi for h in range(1, 13)}
    rasi_house: dict[Rasi, int] = {v: k for k, v in house_rasi.items()}

    # Which houses does each house aspect via rashi drishti?
    house_aspects: dict[int, list[int]] = {}
    for h in range(1, 13):
        rasi = house_rasi[h]
        aspected = _RASHI_DRISHTI.get(rasi, frozenset())
        house_aspects[h] = sorted([rasi_house[r] for r in aspected if r in rasi_house])

    # Reverse: which houses aspect each house?
    aspected_by_house: dict[int, list[int]] = {h: [] for h in range(1, 13)}
    for src_h, targets in house_aspects.items():
        for tgt_h in targets:
            aspected_by_house[tgt_h].append(src_h)
    aspected_by_house = {h: sorted(v) for h, v in aspected_by_house.items()}

    # Grahas contributing rashi drishti to each house via their occupied sign
    house_graha_drishti: dict[int, list[dict]] = {h: [] for h in range(1, 13)}
    for tgt_h in range(1, 13):
        for src_h in aspected_by_house[tgt_h]:
            for g in Graha:
                if planets[g.value].house == src_h:
                    house_graha_drishti[tgt_h].append({
                        "graha": g.value,
                        "from_house": src_h,
                        "from_sign": house_rasi[src_h].value,
                        "sign_type": _SIGN_TYPE[house_rasi[src_h]],
                    })

    # Serializable rashi aspects (sign names)
    rashi_aspects_out: dict[str, list[str]] = {
        r.value: sorted([a.value for a in aspected])
        for r, aspected in _RASHI_DRISHTI.items()
    }

    return {
        "rashi_aspects": rashi_aspects_out,
        "house_aspects": {h: v for h, v in house_aspects.items()},
        "aspected_by_house": {h: v for h, v in aspected_by_house.items()},
        "house_graha_drishti": {h: v for h, v in house_graha_drishti.items()},
    }


def compute_full_drishti_matrix(bundle: ChartBundle) -> list[dict]:
    """Build a combined drishti matrix for all 12 houses.

    Each row shows, for one house:
      - graha_drishti   : planets aspecting via classical graha aspect
      - rashi_drishti   : planets aspecting via Jaimini rashi drishti
      - combined        : union of both (all aspecting planets)
      - double_aspect   : planets with BOTH graha and rashi drishti (very powerful)
      - graha_strength  : cumulative graha aspect strength (1.0 = full, 0.75 = 3/4, etc.)
    """
    from vedic_ai.features.aspects import compute_relationship_graph

    graha_graph = compute_relationship_graph(bundle)
    rashi = compute_rashi_drishti(bundle)

    matrix: list[dict] = []
    for h in range(1, 13):
        rasi_name = bundle.d1.houses[h].rasi.value
        occupants = [g.value for g in Graha if bundle.d1.planets[g.value].house == h]
        graha_asp = graha_graph["aspected_by"][h]
        rashi_asp = [d["graha"] for d in rashi["house_graha_drishti"][h]]
        combined = sorted(set(graha_asp) | set(rashi_asp))
        double_asp = sorted(set(graha_asp) & set(rashi_asp))
        matrix.append({
            "house": h,
            "rasi": rasi_name,
            "occupants": occupants,
            "graha_drishti": sorted(graha_asp),
            "rashi_drishti": sorted(rashi_asp),
            "combined_drishti": combined,
            "double_aspect": double_asp,
            "graha_strength": round(graha_graph["aspect_strength_on_house"][h], 2),
        })
    return matrix
