"""Divisional chart (Varga) analysis for scope-based interpretation.

Varga → life domain mapping:
  D2  Hora           — wealth, finances, luminaries
  D3  Drekkana       — siblings, co-borns, courage, longevity
  D4  Chaturthamsha  — property, fixed assets, fortune
  D6  Shashthamsha   — health, disease, enemies, debts
  D7  Saptamsha      — children, progeny, creative expression
  D8  Ashtamsha      — longevity, hidden obstacles, calamities
  D9  Navamsa        — marriage, dharma, partnerships, spiritual strength
  D10 Dasamsa        — career, profession, social achievement
  D12 Dvadashamsha   — parents, ancestral lineage, inherited patterns
  D16 Shodashamsha   — vehicles, conveyances, comforts, luxuries
  D20 Vimshamsha     — spiritual progress, religious activities
  D24 Chaturvimshamsha — education, learning, knowledge
  D27 Saptavimshamsha  — physical strength, vitality, constitution
  D30 Trimshamsha    — misfortune, disease, past karma, dangers
  D60 Shashtiamsha   — general karma, past-life themes
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle, DivisionalChart
from vedic_ai.domain.enums import Dignity, Graha
from vedic_ai.engines.dignity import RASI_LORDS
from vedic_ai.features.base import DUSTHANA_HOUSES, KENDRA_HOUSES, TRIKONA_HOUSES

_VARGA_SCOPE: dict[str, dict] = {
    "D2":  {"name": "Hora",             "domain": "wealth, finances, luminaries"},
    "D3":  {"name": "Drekkana",          "domain": "siblings, courage, longevity"},
    "D4":  {"name": "Chaturthamsha",     "domain": "property, fixed assets, fortune"},
    "D6":  {"name": "Shashthamsha",      "domain": "health, disease, enemies, debts"},
    "D7":  {"name": "Saptamsha",         "domain": "children, progeny, creativity"},
    "D8":  {"name": "Ashtamsha",         "domain": "longevity, obstacles, calamities"},
    "D9":  {"name": "Navamsa",           "domain": "marriage, dharma, partnerships"},
    "D10": {"name": "Dasamsa",           "domain": "career, profession, social achievement"},
    "D12": {"name": "Dvadashamsha",      "domain": "parents, ancestral lineage"},
    "D16": {"name": "Shodashamsha",      "domain": "vehicles, comforts, luxuries"},
    "D20": {"name": "Vimshamsha",        "domain": "spiritual progress, religious life"},
    "D24": {"name": "Chaturvimshamsha",  "domain": "education, learning, knowledge"},
    "D27": {"name": "Saptavimshamsha",   "domain": "physical strength, vitality"},
    "D30": {"name": "Trimshamsha",       "domain": "misfortune, disease, past karma"},
    "D60": {"name": "Shashtiamsha",      "domain": "general karma, past-life themes"},
}

# Scope-relevant karaka planets for each division
_VARGA_KARAKA: dict[str, list[Graha]] = {
    "D2":  [Graha.SUN, Graha.MOON],
    "D3":  [Graha.MARS, Graha.JUPITER],
    "D4":  [Graha.MARS, Graha.VENUS],
    "D6":  [Graha.MARS, Graha.SATURN, Graha.MOON],   # afflictors and vitality
    "D7":  [Graha.JUPITER, Graha.VENUS],
    "D8":  [Graha.SATURN, Graha.MARS],
    "D9":  [Graha.VENUS, Graha.JUPITER, Graha.MOON],
    "D10": [Graha.SUN, Graha.SATURN, Graha.MERCURY, Graha.MARS],
    "D12": [Graha.SUN, Graha.MOON, Graha.SATURN],
    "D16": [Graha.VENUS, Graha.MOON],
    "D20": [Graha.JUPITER, Graha.KETU, Graha.MOON],
    "D24": [Graha.MERCURY, Graha.JUPITER],
    "D27": [Graha.SUN, Graha.MARS, Graha.SATURN],
    "D30": [Graha.MARS, Graha.SATURN, Graha.RAHU, Graha.KETU],
    "D60": [Graha.SATURN, Graha.RAHU],
}

_STRONG_DIGNITIES = frozenset({Dignity.EXALTED, Dignity.OWN, Dignity.MOOLATRIKONA})


def _planet_record(g: Graha, chart: DivisionalChart) -> dict | None:
    p = chart.planets.get(g.value)
    if p is None:
        return None
    return {
        "graha": g.value,
        "rasi": p.rasi.rasi.value,
        "house": p.house,
        "dignity": p.dignity.value if p.dignity else None,
        "is_retrograde": p.is_retrograde,
        "in_kendra": p.house in KENDRA_HOUSES,
        "in_trikona": p.house in TRIKONA_HOUSES,
        "in_dusthana": p.house in DUSTHANA_HOUSES,
        "is_strong": (p.dignity in _STRONG_DIGNITIES),
        "is_debilitated": (p.dignity == Dignity.DEBILITATED),
    }


def _dignity_stats(chart: DivisionalChart) -> dict:
    stats = {"exalted": 0, "own_sign": 0, "debilitated": 0, "neutral": 0, "retrograde": 0}
    for g in Graha:
        p = chart.planets.get(g.value)
        if p is None:
            continue
        if p.dignity == Dignity.EXALTED:
            stats["exalted"] += 1
        elif p.dignity in (Dignity.OWN, Dignity.MOOLATRIKONA):
            stats["own_sign"] += 1
        elif p.dignity == Dignity.DEBILITATED:
            stats["debilitated"] += 1
        else:
            stats["neutral"] += 1
        if p.is_retrograde:
            stats["retrograde"] += 1
    stats["strength_score"] = stats["exalted"] * 3 + stats["own_sign"] * 2 - stats["debilitated"] * 2
    return stats


def _detect_varga_yogas(chart: DivisionalChart, division: str) -> list[dict]:
    yogas: list[dict] = []

    lagna_rasi = chart.houses[1].rasi
    lagna_lord = RASI_LORDS[lagna_rasi]
    ll = chart.planets.get(lagna_lord.value)

    if ll:
        if ll.house in KENDRA_HOUSES:
            yogas.append({"type": "lagna_lord_kendra",   "graha": lagna_lord.value, "house": ll.house})
        if ll.house in TRIKONA_HOUSES:
            yogas.append({"type": "lagna_lord_trikona",  "graha": lagna_lord.value, "house": ll.house})
        if ll.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "lagna_lord_strong",   "graha": lagna_lord.value, "dignity": ll.dignity.value})
        if ll.house in DUSTHANA_HOUSES:
            yogas.append({"type": "lagna_lord_dusthana", "graha": lagna_lord.value, "house": ll.house})

    # Sign exchange within this varga
    checked: set[tuple] = set()
    for g_a in Graha:
        pa = chart.planets.get(g_a.value)
        if pa is None:
            continue
        lord_of_a = RASI_LORDS[pa.rasi.rasi]
        if lord_of_a == g_a:
            continue
        pb = chart.planets.get(lord_of_a.value)
        if pb is None:
            continue
        if RASI_LORDS[pb.rasi.rasi] == g_a:
            pair = tuple(sorted([g_a.value, lord_of_a.value]))
            if pair not in checked:
                checked.add(pair)
                yogas.append({
                    "type": "sign_exchange",
                    "graha_a": g_a.value, "house_a": pa.house,
                    "graha_b": lord_of_a.value, "house_b": pb.house,
                })

    # D6-specific: 6th / 8th lord strong → health challenge; lagna lord strong → resilience
    if division == "D6":
        for h in (6, 8):
            h_lord = RASI_LORDS[chart.houses[h].rasi]
            h_lp = chart.planets.get(h_lord.value)
            if h_lp:
                if h_lp.dignity in _STRONG_DIGNITIES:
                    yogas.append({"type": f"d6_h{h}_lord_strong", "graha": h_lord.value, "dignity": h_lp.dignity.value, "note": "challenge indicated"})
                if h_lp.house in KENDRA_HOUSES:
                    yogas.append({"type": f"d6_h{h}_lord_kendra", "graha": h_lord.value, "house": h_lp.house})
        # Saturn/Mars/Rahu in lagna of D6 → constitutional vulnerability
        for g in (Graha.SATURN, Graha.MARS, Graha.RAHU):
            p = chart.planets.get(g.value)
            if p and p.house == 1:
                yogas.append({"type": "d6_malefic_in_lagna", "graha": g.value})

    # D8-specific: 8th lord placement matters for longevity
    if division == "D8":
        h8_lord = RASI_LORDS[chart.houses[8].rasi]
        h8l = chart.planets.get(h8_lord.value)
        if h8l:
            if h8l.dignity in _STRONG_DIGNITIES:
                yogas.append({"type": "d8_8th_lord_strong", "graha": h8_lord.value, "dignity": h8l.dignity.value})
            if h8l.house in DUSTHANA_HOUSES:
                yogas.append({"type": "d8_8th_lord_dusthana", "graha": h8_lord.value, "house": h8l.house})

    # D9-specific: 7th lord strong → marriage; Venus strong → partnership quality
    if division == "D9":
        h7_lord = RASI_LORDS[chart.houses[7].rasi]
        h7l = chart.planets.get(h7_lord.value)
        if h7l and h7l.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d9_7th_lord_strong", "graha": h7_lord.value, "dignity": h7l.dignity.value, "house": h7l.house})
        if h7l and h7l.house in KENDRA_HOUSES:
            yogas.append({"type": "d9_7th_lord_kendra", "graha": h7_lord.value, "house": h7l.house})
        venus = chart.planets.get(Graha.VENUS.value)
        if venus and venus.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d9_venus_strong", "dignity": venus.dignity.value, "house": venus.house})

    # D10-specific: Sun/Saturn/Mercury in 1st or 10th
    if division == "D10":
        for g in (Graha.SUN, Graha.SATURN, Graha.MERCURY):
            p = chart.planets.get(g.value)
            if p and p.house in (1, 10):
                yogas.append({"type": "d10_career_planet_prominent", "graha": g.value, "house": p.house, "dignity": p.dignity.value if p.dignity else None})

    # D12-specific: luminaries strong → parent wellbeing
    if division == "D12":
        for g in (Graha.SUN, Graha.MOON):
            p = chart.planets.get(g.value)
            if p and p.dignity == Dignity.EXALTED:
                yogas.append({"type": "d12_parent_luminary_exalted", "graha": g.value})
            elif p and p.dignity == Dignity.DEBILITATED:
                yogas.append({"type": "d12_parent_luminary_debilitated", "graha": g.value})

    # D16-specific: Venus/Moon strength → vehicles and comforts
    if division == "D16":
        venus = chart.planets.get(Graha.VENUS.value)
        moon = chart.planets.get(Graha.MOON.value)
        if venus and venus.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d16_venus_strong", "dignity": venus.dignity.value, "house": venus.house, "note": "vehicle/comfort fortune"})
        if venus and venus.house in DUSTHANA_HOUSES:
            yogas.append({"type": "d16_venus_dusthana", "house": venus.house, "note": "vehicle obstacles/losses"})
        if moon and moon.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d16_moon_strong", "dignity": moon.dignity.value, "house": moon.house, "note": "comforts and luxuries enhanced"})
        if moon and moon.dignity == Dignity.DEBILITATED:
            yogas.append({"type": "d16_moon_debilitated", "house": moon.house, "note": "domestic/comfort challenges"})
        # 4th lord strong → property and vehicles from family
        h4_lord = RASI_LORDS[chart.houses[4].rasi]
        h4l = chart.planets.get(h4_lord.value)
        if h4l and h4l.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d16_4th_lord_strong", "graha": h4_lord.value, "dignity": h4l.dignity.value})

    # D20-specific: Jupiter/Ketu/Moon for spiritual progress
    if division == "D20":
        jupiter = chart.planets.get(Graha.JUPITER.value)
        ketu = chart.planets.get(Graha.KETU.value)
        moon = chart.planets.get(Graha.MOON.value)
        if jupiter and jupiter.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d20_jupiter_strong", "dignity": jupiter.dignity.value, "house": jupiter.house, "note": "strong spiritual wisdom"})
        if jupiter and jupiter.house in KENDRA_HOUSES | TRIKONA_HOUSES:
            yogas.append({"type": "d20_jupiter_angular", "house": jupiter.house, "note": "dharmic path supported"})
        if ketu and ketu.house in TRIKONA_HOUSES:
            yogas.append({"type": "d20_ketu_trikona", "house": ketu.house, "note": "spiritual liberation potential"})
        if moon and moon.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d20_moon_strong", "dignity": moon.dignity.value, "house": moon.house, "note": "devotional nature enhanced"})
        # 9th lord strength → religious activities
        h9_lord = RASI_LORDS[chart.houses[9].rasi]
        h9l = chart.planets.get(h9_lord.value)
        if h9l and h9l.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d20_9th_lord_strong", "graha": h9_lord.value, "dignity": h9l.dignity.value, "note": "religious merit"})

    # D24-specific: Mercury/Jupiter for education and learning
    if division == "D24":
        mercury = chart.planets.get(Graha.MERCURY.value)
        jupiter = chart.planets.get(Graha.JUPITER.value)
        if mercury and mercury.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d24_mercury_strong", "dignity": mercury.dignity.value, "house": mercury.house, "note": "sharp intellect, academic success"})
        if mercury and mercury.house in DUSTHANA_HOUSES:
            yogas.append({"type": "d24_mercury_dusthana", "house": mercury.house, "note": "educational obstacles"})
        if jupiter and jupiter.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d24_jupiter_strong", "dignity": jupiter.dignity.value, "house": jupiter.house, "note": "higher learning, philosophy"})
        # 4th and 5th lord placement (education houses)
        for h in (4, 5):
            h_lord = RASI_LORDS[chart.houses[h].rasi]
            hl = chart.planets.get(h_lord.value)
            if hl and hl.dignity in _STRONG_DIGNITIES:
                yogas.append({"type": f"d24_h{h}_lord_strong", "graha": h_lord.value, "dignity": hl.dignity.value})
            if hl and hl.house in DUSTHANA_HOUSES:
                yogas.append({"type": f"d24_h{h}_lord_dusthana", "graha": h_lord.value, "house": hl.house})

    # D27-specific: Sun/Mars/Saturn for physical strength and vitality
    if division == "D27":
        sun = chart.planets.get(Graha.SUN.value)
        mars = chart.planets.get(Graha.MARS.value)
        saturn = chart.planets.get(Graha.SATURN.value)
        if sun and sun.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d27_sun_strong", "dignity": sun.dignity.value, "house": sun.house, "note": "vitality and constitution strong"})
        if sun and sun.dignity == Dignity.DEBILITATED:
            yogas.append({"type": "d27_sun_debilitated", "house": sun.house, "note": "physical constitution weak"})
        if mars and mars.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d27_mars_strong", "dignity": mars.dignity.value, "house": mars.house, "note": "physical strength and courage"})
        if mars and mars.house in DUSTHANA_HOUSES:
            yogas.append({"type": "d27_mars_dusthana", "house": mars.house, "note": "injury/accident risk"})
        if saturn and saturn.dignity == Dignity.EXALTED:
            yogas.append({"type": "d27_saturn_exalted", "house": saturn.house, "note": "endurance and stamina"})
        if saturn and saturn.dignity == Dignity.DEBILITATED:
            yogas.append({"type": "d27_saturn_debilitated", "house": saturn.house, "note": "chronic health issues"})
        # Lagna lord in 6th or 8th → physical vulnerability
        ll_graha = RASI_LORDS[chart.houses[1].rasi]
        ll_p = chart.planets.get(ll_graha.value)
        if ll_p and ll_p.house in (6, 8):
            yogas.append({"type": "d27_lagna_lord_dusthana", "graha": ll_graha.value, "house": ll_p.house, "note": "physical resilience challenged"})

    # D30-specific: Saturn/Mars/Rahu/Ketu in 1st or 8th → misfortune area
    if division == "D30":
        for g in (Graha.SATURN, Graha.MARS, Graha.RAHU, Graha.KETU):
            p = chart.planets.get(g.value)
            if p and p.house in (1, 8):
                yogas.append({"type": "d30_malefic_sensitive_house", "graha": g.value, "house": p.house})

    # D60-specific: Saturn/Rahu for karma themes
    if division == "D60":
        saturn = chart.planets.get(Graha.SATURN.value)
        rahu = chart.planets.get(Graha.RAHU.value)
        ketu = chart.planets.get(Graha.KETU.value)
        if saturn and saturn.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d60_saturn_strong", "dignity": saturn.dignity.value, "house": saturn.house, "note": "karmic debts being resolved"})
        if saturn and saturn.dignity == Dignity.DEBILITATED:
            yogas.append({"type": "d60_saturn_debilitated", "house": saturn.house, "note": "heavy karmic burden"})
        if rahu and rahu.house in TRIKONA_HOUSES:
            yogas.append({"type": "d60_rahu_trikona", "house": rahu.house, "note": "worldly karma active"})
        if ketu and ketu.house in TRIKONA_HOUSES:
            yogas.append({"type": "d60_ketu_trikona", "house": ketu.house, "note": "spiritual karma ripening"})
        # Strong lagna lord → karmic merit carries forward
        ll_graha = RASI_LORDS[chart.houses[1].rasi]
        ll_p = chart.planets.get(ll_graha.value)
        if ll_p and ll_p.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d60_lagna_lord_strong", "graha": ll_graha.value, "dignity": ll_p.dignity.value, "note": "past-life merit supports this life"})

    return yogas


def analyze_varga_chart(chart: DivisionalChart, division: str) -> dict:
    """Produce a structured analysis of a single divisional chart."""
    scope = _VARGA_SCOPE.get(division, {"name": division, "domain": "unknown"})
    karakas = _VARGA_KARAKA.get(division, [])

    lagna_rasi = chart.houses[1].rasi
    lagna_lord = RASI_LORDS[lagna_rasi]
    ll = chart.planets.get(lagna_lord.value)

    planets_out = [rec for g in Graha if (rec := _planet_record(g, chart)) is not None]
    karakas_out = [rec for g in karakas if (rec := _planet_record(g, chart)) is not None]

    return {
        "division": division,
        "name": scope["name"],
        "domain": scope["domain"],
        "lagna": lagna_rasi.value,
        "lagna_lord": lagna_lord.value,
        "lagna_lord_house": ll.house if ll else None,
        "lagna_lord_dignity": ll.dignity.value if ll and ll.dignity else None,
        "lagna_lord_strong": bool(ll and ll.dignity in _STRONG_DIGNITIES),
        "planets": planets_out,
        "karaka_analysis": karakas_out,
        "dignity_stats": _dignity_stats(chart),
        "yogas": _detect_varga_yogas(chart, division),
    }


def extract_varga_analysis(bundle: ChartBundle) -> dict[str, dict]:
    """Analyze all available varga charts present in the bundle."""
    return {
        division: analyze_varga_chart(chart, division)
        for division, chart in bundle.vargas.items()
        if division in _VARGA_SCOPE
    }
