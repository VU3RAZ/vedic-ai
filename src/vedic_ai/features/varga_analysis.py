"""Divisional chart (Varga) analysis for scope-based interpretation.

Each varga represents a specific life domain:
  D3  (Drekkana)     — siblings, co-borns, courage, longevity
  D7  (Saptamsha)    — children, progeny, creative expression
  D9  (Navamsa)      — marriage, partnerships, dharma, overall chart strength
  D10 (Dasamsa)      — career, profession, social achievement
  D12 (Dvadashamsha) — parents, ancestral lineage, inherited patterns

For each varga we extract:
  - Lagna + lagna lord placement and dignity
  - All planet positions (sign, house, dignity)
  - Scope karaka positions and dignity
  - Dignity statistics (exalted/own/debilitated counts)
  - Notable varga yogas (lagna lord in kendra/trikona, sign exchanges, special placements)
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle, DivisionalChart
from vedic_ai.domain.enums import Dignity, Graha
from vedic_ai.engines.dignity import RASI_LORDS
from vedic_ai.features.base import DUSTHANA_HOUSES, KENDRA_HOUSES, TRIKONA_HOUSES

_VARGA_SCOPE: dict[str, dict] = {
    "D3":  {"name": "Drekkana",     "domain": "siblings, courage, longevity"},
    "D7":  {"name": "Saptamsha",    "domain": "children, progeny, creativity"},
    "D9":  {"name": "Navamsa",      "domain": "marriage, dharma, partnerships"},
    "D10": {"name": "Dasamsa",      "domain": "career, profession, social achievement"},
    "D12": {"name": "Dvadashamsha", "domain": "parents, ancestral lineage"},
}

# Scope-relevant karaka planets for each division
_VARGA_KARAKA: dict[str, list[Graha]] = {
    "D3":  [Graha.MARS, Graha.JUPITER],
    "D7":  [Graha.JUPITER, Graha.VENUS],
    "D9":  [Graha.VENUS, Graha.JUPITER, Graha.MOON],
    "D10": [Graha.SUN, Graha.SATURN, Graha.MERCURY, Graha.MARS],
    "D12": [Graha.SUN, Graha.MOON, Graha.SATURN],
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
            yogas.append({"type": "lagna_lord_kendra", "graha": lagna_lord.value, "house": ll.house})
        if ll.house in TRIKONA_HOUSES:
            yogas.append({"type": "lagna_lord_trikona", "graha": lagna_lord.value, "house": ll.house})
        if ll.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "lagna_lord_strong", "graha": lagna_lord.value, "dignity": ll.dignity.value})
        if ll.house in DUSTHANA_HOUSES:
            yogas.append({"type": "lagna_lord_dusthana", "graha": lagna_lord.value, "house": ll.house})

    # Sign exchange (parivartana) within varga
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

    # D9-specific: 7th lord in kendra/own/exalted → strong marriage potential
    if division == "D9":
        h7_lord = RASI_LORDS[chart.houses[7].rasi]
        h7l = chart.planets.get(h7_lord.value)
        if h7l and h7l.dignity in _STRONG_DIGNITIES:
            yogas.append({"type": "d9_7th_lord_strong", "graha": h7_lord.value, "dignity": h7l.dignity.value, "house": h7l.house})
        if h7l and h7l.house in KENDRA_HOUSES:
            yogas.append({"type": "d9_7th_lord_kendra", "graha": h7_lord.value, "house": h7l.house})

    # D10-specific: Sun/Saturn/Mercury in 1st or 10th → career prominence
    if division == "D10":
        for g in (Graha.SUN, Graha.SATURN, Graha.MERCURY):
            p = chart.planets.get(g.value)
            if p and p.house in (1, 10):
                yogas.append({"type": "d10_career_planet_prominent", "graha": g.value, "house": p.house, "dignity": p.dignity.value if p.dignity else None})

    # D12-specific: Sun/Moon dignity → parent's wellbeing
    if division == "D12":
        for g in (Graha.SUN, Graha.MOON):
            p = chart.planets.get(g.value)
            if p and p.dignity == Dignity.EXALTED:
                yogas.append({"type": "d12_parent_luminary_exalted", "graha": g.value, "dignity": p.dignity.value})
            elif p and p.dignity == Dignity.DEBILITATED:
                yogas.append({"type": "d12_parent_luminary_debilitated", "graha": g.value, "dignity": p.dignity.value})

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
