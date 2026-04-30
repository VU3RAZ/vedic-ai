"""Core feature extraction orchestrator.

Aggregates planet strengths, house lordships, aspect graph, nakshatra features,
and yoga detection into a single JSON-serializable feature dict.
All computation is deterministic and side-effect free.
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Graha, Rasi
from vedic_ai.engines.normalizer import _longitude_to_nakshatra
from vedic_ai.features.aspects import compute_relationship_graph
from vedic_ai.features.base import (
    DUSTHANA_HOUSES,
    HOUSE_TYPES,
    KENDRA_HOUSES,
    TRIKONA_HOUSES,
)
from vedic_ai.features.lordships import compute_house_lordships
from vedic_ai.features.nakshatra_features import extract_nakshatra_features
from vedic_ai.features.strength import compute_planet_strengths, full_dignity


# ---------------------------------------------------------------------------
# Yoga detection helpers
# ---------------------------------------------------------------------------

def _detect_kemadruma(bundle: ChartBundle) -> bool:
    """Kemadruma yoga: Moon has no planets in its 2nd or 12th sign, or conjunct it.

    True when the yoga is present (potentially challenging for the native).
    """
    moon_house = bundle.d1.planets[Graha.MOON.value].house
    second_from_moon = moon_house % 12 + 1          # (moon_house + 1 - 1) % 12 + 1
    twelfth_from_moon = (moon_house - 2) % 12 + 1   # (moon_house - 1 - 1) % 12 + 1

    for graha in Graha:
        if graha == Graha.MOON:
            continue
        h = bundle.d1.planets[graha.value].house
        if h in (moon_house, second_from_moon, twelfth_from_moon):
            return False
    return True


def _detect_gajakesari(bundle: ChartBundle) -> bool:
    """Gajakesari yoga: Jupiter in a kendra (1/4/7/10) from Moon.

    A classical yoga for intelligence, prosperity, and good reputation.
    """
    moon_house = bundle.d1.planets[Graha.MOON.value].house
    jup_house = bundle.d1.planets[Graha.JUPITER.value].house
    diff = (jup_house - moon_house) % 12
    return diff in (0, 3, 6, 9)


def _detect_raja_yogas(bundle: ChartBundle, lordships: dict[int, dict]) -> list[dict]:
    """Detect basic Raja yogas: trikona lord + kendra lord in association.

    Association means: conjunction (same house) or mutual aspect (7th from each other).
    Returns a list of detected yoga dicts.
    """
    yogas: list[dict] = []
    trikona_lords = {lordships[h]["lord"] for h in TRIKONA_HOUSES}
    kendra_lords = {lordships[h]["lord"] for h in KENDRA_HOUSES}

    # Exclude lagna lord from the pair condition only when it already counted for both
    for t_lord in trikona_lords:
        for k_lord in kendra_lords:
            if t_lord == k_lord:
                continue  # Same planet lords both — single-planet raja yoga

            t_house = bundle.d1.planets[t_lord].house
            k_house = bundle.d1.planets[k_lord].house

            conjunct = t_house == k_house
            mutual_7th = (k_house - t_house) % 12 == 6 or (t_house - k_house) % 12 == 6

            if conjunct or mutual_7th:
                yogas.append({
                    "type": "raja_yoga",
                    "trikona_lord": t_lord,
                    "kendra_lord": k_lord,
                    "association": "conjunction" if conjunct else "mutual_7th_aspect",
                    "house_t": t_house,
                    "house_k": k_house,
                })
    return yogas


def _detect_dhana_yogas(bundle: ChartBundle, lordships: dict[int, dict]) -> list[dict]:
    """Detect basic Dhana (wealth) yogas.

    Classic definition: lord of 2nd or 11th associated with lord of 1st or 9th.
    """
    yogas: list[dict] = []
    wealth_lords = {lordships[h]["lord"] for h in (2, 11)}
    prosperity_lords = {lordships[h]["lord"] for h in (1, 9)}

    for w_lord in wealth_lords:
        for p_lord in prosperity_lords:
            if w_lord == p_lord:
                continue

            w_house = bundle.d1.planets[w_lord].house
            p_house = bundle.d1.planets[p_lord].house

            conjunct = w_house == p_house
            mutual_7th = (p_house - w_house) % 12 == 6 or (w_house - p_house) % 12 == 6

            if conjunct or mutual_7th:
                yogas.append({
                    "type": "dhana_yoga",
                    "wealth_lord": w_lord,
                    "prosperity_lord": p_lord,
                    "association": "conjunction" if conjunct else "mutual_7th_aspect",
                    "house_w": w_house,
                    "house_p": p_house,
                })
    return yogas


def _build_lagna_features(bundle: ChartBundle, lordships: dict[int, dict]) -> dict:
    asc_lon = bundle.d1.ascendant_longitude
    lagna_rasi = bundle.d1.houses[1].rasi
    nak_name, pada, lord_graha, deg_in_nak = _longitude_to_nakshatra(asc_lon)
    lagna_lord_data = lordships[1]
    return {
        "rasi": lagna_rasi.value,
        "nakshatra": nak_name.value,
        "pada": pada,
        "nakshatra_lord": lord_graha.value,
        "degree_in_nakshatra": round(deg_in_nak, 4),
        "lord": lagna_lord_data["lord"],
        "lord_house": lagna_lord_data["lord_house"],
        "lord_rasi": lagna_lord_data["lord_rasi"],
        "lord_dignity": lagna_lord_data["lord_dignity"],
    }


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

def extract_core_features(bundle: ChartBundle) -> dict:
    """Generate all interpretation-ready features from a ChartBundle.

    Returns a deterministic, JSON-serializable dict containing:
    - ``planets``: per-graha placement + strength + nakshatra data
    - ``houses``: per-house lord, strength, occupants, aspects received
    - ``aspects``: conjunction, graha drishti, sign exchange, mutual aspects
    - ``yogas``: kemadruma, gajakesari, raja yoga, dhana yoga
    - ``lagna``: ascendant details
    - ``metadata``: engine, ayanamsa, schema version

    All values are deterministic for a fixed ChartBundle.
    """
    strengths = compute_planet_strengths(bundle)
    lordships = compute_house_lordships(bundle)
    aspects = compute_relationship_graph(bundle)
    nak_features = extract_nakshatra_features(bundle)

    # Build per-planet record
    planets_out: dict[str, dict] = {}
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        s = strengths[graha.value]
        nf = nak_features["planets"][graha.value]
        planets_out[graha.value] = {
            "graha": graha.value,
            "longitude": round(p.longitude, 6),
            "rasi": p.rasi.rasi.value,
            "degree_in_rasi": round(p.rasi.degree_in_rasi, 4),
            "house": p.house,
            "is_retrograde": p.is_retrograde,
            "speed": round(p.speed, 6),
            "dignity": s["dignity"],
            "is_exalted": s["is_exalted"],
            "is_debilitated": s["is_debilitated"],
            "is_own_sign": s["is_own_sign"],
            "in_friend_sign": s["in_friend_sign"],
            "in_enemy_sign": s["in_enemy_sign"],
            "total_strength": s["total_strength"],
            "house_type": s["house_type"],
            "nakshatra": nf["nakshatra"],
            "pada": nf["pada"],
            "nakshatra_lord": nf["lord"],
            "nakshatra_deity": nf["deity"],
            "degree_in_nakshatra": nf["degree_in_nakshatra"],
            "pada_rasi": nf["pada_rasi"],
            "aspects_to_houses": [a["house"] for a in aspects["graha_aspects"][graha.value]],
            "in_kendra": p.house in KENDRA_HOUSES,
            "in_trikona": p.house in TRIKONA_HOUSES,
            "in_dusthana": p.house in DUSTHANA_HOUSES,
        }

    # Build per-house record
    houses_out: dict[int, dict] = {}
    for h in range(1, 13):
        ld = lordships[h]
        houses_out[h] = {
            "house": h,
            "rasi": ld["rasi"],
            "lord": ld["lord"],
            "lord_house": ld["lord_house"],
            "lord_rasi": ld["lord_rasi"],
            "lord_dignity": ld["lord_dignity"],
            "lord_is_retrograde": ld["lord_is_retrograde"],
            "lord_in_kendra": ld["lord_in_kendra"],
            "lord_in_trikona": ld["lord_in_trikona"],
            "lord_in_dusthana": ld["lord_in_dusthana"],
            "lord_house_type": ld["lord_house_type"],
            "occupants": ld["occupants"],
            "is_occupied": ld["is_occupied"],
            "house_type": HOUSE_TYPES[h],
            "aspects_received_from": aspects["aspected_by"][h],
        }

    # Yoga detection
    yogas = {
        "kemadruma": _detect_kemadruma(bundle),
        "gajakesari": _detect_gajakesari(bundle),
        "raja_yogas": _detect_raja_yogas(bundle, lordships),
        "dhana_yogas": _detect_dhana_yogas(bundle, lordships),
    }

    return {
        "planets": planets_out,
        "houses": houses_out,
        "aspects": {
            "conjunctions": aspects["conjunctions"],
            "sign_exchanges": aspects["sign_exchanges"],
            "mutual_house_aspects": aspects["mutual_house_aspects"],
        },
        "yogas": yogas,
        "lagna": _build_lagna_features(bundle, lordships),
        "nakshatra_ascendant": nak_features["ascendant"],
        "metadata": {
            "engine": bundle.engine,
            "ayanamsa": bundle.ayanamsa,
            "node_type": bundle.node_type,
            "schema_version": bundle.schema_version,
        },
    }
