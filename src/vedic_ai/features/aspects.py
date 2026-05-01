"""Graha drishti (planetary aspect) computation.

Jyotish special aspects encoded as a lookup table (not hard-coded conditionals):
  - All planets: 7th house aspect
  - Mars:        4th and 8th (in addition to 7th)
  - Jupiter:     5th and 9th
  - Saturn:      3rd and 10th
  - Rahu/Ketu:   5th, 7th, 9th (commonly used; some traditions differ)
"""

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS

# Aspect numbers for each graha (1 = self, 7 = opposite, etc.)
GRAHA_ASPECTS: dict[Graha, list[int]] = {
    Graha.SUN:     [7],
    Graha.MOON:    [7],
    Graha.MARS:    [4, 7, 8],
    Graha.MERCURY: [7],
    Graha.JUPITER: [5, 7, 9],
    Graha.VENUS:   [7],
    Graha.SATURN:  [3, 7, 10],
    Graha.RAHU:    [5, 7, 9],
    Graha.KETU:    [5, 7, 9],
}

# Classical aspect strength fractions (non-7th special aspects only; 7th = 1.0 for all)
# Mars 4th = 3/4, 8th = 1/2; Saturn 3rd = 3/4, 10th = 3/4; Jupiter/Rahu/Ketu = full
_SPECIAL_STRENGTHS: dict[Graha, dict[int, float]] = {
    Graha.MARS:   {4: 0.75, 8: 0.50},
    Graha.SATURN: {3: 0.75, 10: 0.75},
}


def _aspect_strength(graha: Graha, aspect_n: int) -> float:
    return _SPECIAL_STRENGTHS.get(graha, {}).get(aspect_n, 1.0)


def _aspected_house(planet_house: int, aspect_number: int) -> int:
    """Return the house number that receives an Nth-house aspect from planet_house."""
    return (planet_house + aspect_number - 2) % 12 + 1


def _rasi_idx(rasi: Rasi) -> int:
    return list(Rasi).index(rasi)


def compute_relationship_graph(bundle: ChartBundle) -> dict:
    """Build the complete aspect, conjunction, and exchange relationship graph.

    Returns a dict with keys:
    - ``graha_aspects``: every graha → houses it aspects, and the aspect types
    - ``aspected_by``: every house → grahas aspecting it
    - ``conjunctions``: groups of planets sharing a sign
    - ``sign_exchanges``: parivartana (mutual sign exchange) pairs
    - ``mutual_house_aspects``: pairs of grahas aspecting each other's natal house
    """
    planets = bundle.d1.planets

    # 1. Build graha → list of aspected houses
    graha_aspects: dict[str, list[dict]] = {}
    for graha in Graha:
        p = planets[graha.value]
        aspects_list = []
        for n in GRAHA_ASPECTS[graha]:
            aspected = _aspected_house(p.house, n)
            strength = _aspect_strength(graha, n)
            aspects_list.append({
                "house": aspected,
                "aspect_type": f"{n}th",
                "strength": strength,
                "strength_label": "Full" if strength == 1.0 else ("3/4" if strength == 0.75 else "1/2"),
            })
        graha_aspects[graha.value] = aspects_list

    # 2. Build house → list of aspecting grahas
    aspected_by: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for graha_name, aspects_list in graha_aspects.items():
        for asp in aspects_list:
            aspected_by[asp["house"]].append(graha_name)

    # 3. Conjunctions — planets sharing the same sign/house
    house_to_grahas: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for g in Graha:
        house_to_grahas[planets[g.value].house].append(g.value)

    conjunctions = [
        {"grahas": grahas, "house": h, "rasi": bundle.d1.houses[h].rasi.value}
        for h, grahas in house_to_grahas.items()
        if len(grahas) > 1
    ]

    # 4. Sign exchanges (Parivartana)
    sign_exchanges: list[dict] = []
    checked: set[tuple[str, str]] = set()
    for graha_a in Graha:
        pa = planets[graha_a.value]
        lord_of_a = RASI_LORDS[pa.rasi.rasi]
        if lord_of_a == graha_a:
            continue  # planet in own sign — not an exchange
        pb = planets[lord_of_a.value]
        lord_of_b = RASI_LORDS[pb.rasi.rasi]
        if lord_of_b == graha_a:
            pair = tuple(sorted([graha_a.value, lord_of_a.value]))
            if pair not in checked:
                checked.add(pair)
                sign_exchanges.append({
                    "graha_a": graha_a.value,
                    "graha_b": lord_of_a.value,
                    "house_a": pa.house,
                    "house_b": pb.house,
                    "rasi_a": pa.rasi.rasi.value,
                    "rasi_b": pb.rasi.rasi.value,
                })

    # 5. Mutual house aspects — two planets aspecting each other's natal house
    mutual: list[dict] = []
    graha_list = list(Graha)
    for i, ga in enumerate(graha_list):
        ha = planets[ga.value].house
        aspected_a = {d["house"] for d in graha_aspects[ga.value]}
        for gb in graha_list[i + 1:]:
            hb = planets[gb.value].house
            aspected_b = {d["house"] for d in graha_aspects[gb.value]}
            if hb in aspected_a and ha in aspected_b:
                mutual.append({"graha_a": ga.value, "graha_b": gb.value,
                                "house_a": ha, "house_b": hb})

    # 6. Rasi drishti — aspect strengths each graha receives from aspecting grahas
    aspect_strength_on_house: dict[int, float] = {h: 0.0 for h in range(1, 13)}
    for graha_name, aspects_list in graha_aspects.items():
        for asp in aspects_list:
            aspect_strength_on_house[asp["house"]] += asp["strength"]

    return {
        "graha_aspects": graha_aspects,
        "aspected_by": aspected_by,
        "aspect_strength_on_house": aspect_strength_on_house,
        "conjunctions": conjunctions,
        "sign_exchanges": sign_exchanges,
        "mutual_house_aspects": mutual,
    }
