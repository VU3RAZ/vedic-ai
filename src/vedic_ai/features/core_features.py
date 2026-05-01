"""Core feature extraction orchestrator.

Aggregates planet strengths, house lordships, aspect graph, nakshatra features,
sandhi analysis, divisional chart positions, and yoga detection into a single
JSON-serializable feature dict.
All computation is deterministic and side-effect free.
"""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Dignity, Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS, compute_dignity
from vedic_ai.engines.normalizer import _longitude_to_nakshatra
from vedic_ai.features.aspects import compute_relationship_graph
from vedic_ai.features.base import (
    DUSTHANA_HOUSES,
    HOUSE_TYPES,
    KENDRA_HOUSES,
    TRIKONA_HOUSES,
)
from vedic_ai.features.drishti import compute_full_drishti_matrix, compute_rashi_drishti
from vedic_ai.features.lordships import compute_house_lordships
from vedic_ai.features.nakshatra_features import extract_nakshatra_features
from vedic_ai.features.sandhi import compute_sandhi_analysis
from vedic_ai.features.strength import compute_planet_strengths, full_dignity
from vedic_ai.features.varga_analysis import extract_varga_analysis

# ---------------------------------------------------------------------------
# Yoga detection tables
# ---------------------------------------------------------------------------

_MAHAPURUSHA: dict[Graha, tuple[str, frozenset]] = {
    Graha.MARS:    ("Ruchaka",  frozenset({Rasi.ARIES, Rasi.SCORPIO, Rasi.CAPRICORN})),
    Graha.MERCURY: ("Bhadra",   frozenset({Rasi.GEMINI, Rasi.VIRGO})),
    Graha.JUPITER: ("Hamsa",    frozenset({Rasi.SAGITTARIUS, Rasi.PISCES, Rasi.CANCER})),
    Graha.VENUS:   ("Malavya",  frozenset({Rasi.TAURUS, Rasi.LIBRA, Rasi.PISCES})),
    Graha.SATURN:  ("Shasha",   frozenset({Rasi.CAPRICORN, Rasi.AQUARIUS, Rasi.LIBRA})),
}

_DEBILITATION_SIGN: dict[Graha, Rasi] = {
    Graha.SUN:     Rasi.LIBRA,
    Graha.MOON:    Rasi.SCORPIO,
    Graha.MARS:    Rasi.CANCER,
    Graha.MERCURY: Rasi.PISCES,
    Graha.JUPITER: Rasi.CAPRICORN,
    Graha.VENUS:   Rasi.VIRGO,
    Graha.SATURN:  Rasi.ARIES,
    Graha.RAHU:    Rasi.SCORPIO,
    Graha.KETU:    Rasi.TAURUS,
}

# Which planet is exalted in each sign (for neechabhanga condition 2)
_EXALTED_IN_SIGN: dict[Rasi, Graha] = {
    Rasi.ARIES:      Graha.SUN,
    Rasi.TAURUS:     Graha.MOON,
    Rasi.CAPRICORN:  Graha.MARS,
    Rasi.VIRGO:      Graha.MERCURY,
    Rasi.CANCER:     Graha.JUPITER,
    Rasi.PISCES:     Graha.VENUS,
    Rasi.LIBRA:      Graha.SATURN,
}


# ---------------------------------------------------------------------------
# Yoga detectors
# ---------------------------------------------------------------------------

def _detect_kemadruma(bundle: ChartBundle) -> bool:
    """Kemadruma yoga: Moon has no planets in its 2nd or 12th sign, or conjunct it."""
    moon_house = bundle.d1.planets[Graha.MOON.value].house
    second = moon_house % 12 + 1
    twelfth = (moon_house - 2) % 12 + 1
    for graha in Graha:
        if graha == Graha.MOON:
            continue
        if bundle.d1.planets[graha.value].house in (moon_house, second, twelfth):
            return False
    return True


def _detect_gajakesari(bundle: ChartBundle) -> bool:
    """Gajakesari yoga: Jupiter in a kendra (1/4/7/10) from Moon."""
    moon_house = bundle.d1.planets[Graha.MOON.value].house
    jup_house = bundle.d1.planets[Graha.JUPITER.value].house
    return (jup_house - moon_house) % 12 in (0, 3, 6, 9)


def _detect_raja_yogas(bundle: ChartBundle, lordships: dict[int, dict]) -> list[dict]:
    """Detect basic Raja yogas: trikona lord + kendra lord in conjunction or mutual 7th."""
    yogas: list[dict] = []
    trikona_lords = {lordships[h]["lord"] for h in TRIKONA_HOUSES}
    kendra_lords = {lordships[h]["lord"] for h in KENDRA_HOUSES}

    for t_lord in trikona_lords:
        for k_lord in kendra_lords:
            if t_lord == k_lord:
                continue
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
    """Detect basic Dhana yogas: lord of 2nd/11th associated with lord of 1st/9th."""
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


def _detect_pancha_mahapurusha(bundle: ChartBundle) -> list[dict]:
    """Detect Pancha Mahapurusha Yogas.

    A planet in a Kendra (1/4/7/10) in its own sign or exaltation sign.
    """
    yogas: list[dict] = []
    for graha, (name, qualifying_signs) in _MAHAPURUSHA.items():
        p = bundle.d1.planets[graha.value]
        if p.house in KENDRA_HOUSES and p.rasi.rasi in qualifying_signs:
            yogas.append({
                "type": "pancha_mahapurusha",
                "name": name,
                "graha": graha.value,
                "rasi": p.rasi.rasi.value,
                "house": p.house,
            })
    return yogas


def _detect_neechabhanga(bundle: ChartBundle) -> list[dict]:
    """Detect Neechabhanga Raja Yoga (debilitation cancellation).

    Condition 1: Lord of the debilitation sign is in a Kendra from lagna.
    Condition 2: Planet exalted in the debilitation sign is in a Kendra from lagna.
    """
    yogas: list[dict] = []
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        if p.dignity != Dignity.DEBILITATED:
            continue
        debi_sign = _DEBILITATION_SIGN.get(graha)
        if debi_sign is None:
            continue

        cancellation_by: list[str] = []

        # Condition 1: sign lord of debilitation sign in kendra
        debi_lord = RASI_LORDS[debi_sign]
        debi_lord_house = bundle.d1.planets[debi_lord.value].house
        if debi_lord_house in KENDRA_HOUSES:
            cancellation_by.append(
                f"{debi_lord.value} (lord of {debi_sign.value}) in H{debi_lord_house} (kendra)"
            )

        # Condition 2: planet exalted in that sign in kendra
        exalted_graha = _EXALTED_IN_SIGN.get(debi_sign)
        if exalted_graha and exalted_graha != graha:
            exalted_house = bundle.d1.planets[exalted_graha.value].house
            if exalted_house in KENDRA_HOUSES:
                cancellation_by.append(
                    f"{exalted_graha.value} (exalted in {debi_sign.value}) in H{exalted_house} (kendra)"
                )

        if cancellation_by:
            yogas.append({
                "type": "neechabhanga_raja_yoga",
                "graha": graha.value,
                "debilitation_sign": debi_sign.value,
                "house": p.house,
                "cancellation_by": cancellation_by,
            })
    return yogas


def _detect_viparita_raja_yoga(bundle: ChartBundle, lordships: dict[int, dict]) -> list[dict]:
    """Detect Viparita Raja Yoga: dusthana lord placed in another dusthana house."""
    yogas: list[dict] = []
    for house in DUSTHANA_HOUSES:
        lord = lordships[house]["lord"]
        lord_house = bundle.d1.planets[lord].house
        if lord_house in DUSTHANA_HOUSES and lord_house != house:
            yogas.append({
                "type": "viparita_raja_yoga",
                "lord": lord,
                "owns_house": house,
                "placed_in_house": lord_house,
            })
    return yogas


def _detect_vargottama(bundle: ChartBundle) -> dict[str, bool]:
    """Detect Vargottama: planet occupies the same sign in D1 and D9 (very strong)."""
    if "D9" not in bundle.vargas:
        return {}
    d9 = bundle.vargas["D9"]
    return {
        graha.value: bundle.d1.planets[graha.value].rasi.rasi == d9.planets[graha.value].rasi.rasi
        for graha in Graha
    }


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


def _build_varga_summary(bundle: ChartBundle) -> dict:
    """Extract sign/house/dignity for each planet in each computed varga chart."""
    out: dict[str, dict] = {}
    for division, varga_chart in bundle.vargas.items():
        div_data: dict[str, dict] = {}
        asc_rasi = varga_chart.houses[1].rasi if varga_chart.houses else None
        for graha in Graha:
            vp = varga_chart.planets.get(graha.value)
            if vp is None:
                continue
            div_data[graha.value] = {
                "rasi": vp.rasi.rasi.value,
                "house": vp.house,
                "dignity": vp.dignity.value if vp.dignity else None,
            }
        out[division] = {
            "lagna": asc_rasi.value if asc_rasi else None,
            "planets": div_data,
        }
    return out


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

def extract_core_features(bundle: ChartBundle) -> dict:
    """Generate all interpretation-ready features from a ChartBundle.

    Returns a deterministic, JSON-serializable dict with:
    - planets     : per-graha placement + strength + nakshatra + sandhi + varga data
    - houses      : per-house lord, strength, occupants, aspects received
    - aspects     : full graha drishti graph, conjunctions, sign exchanges, mutuals
    - yogas       : kemadruma, gajakesari, raja, dhana, pancha mahapurusha,
                    neechabhanga, viparita
    - sandhi      : per-graha cusp-proximity classification
    - vargas      : D9/D10/etc planet sign+house+dignity
    - lagna       : ascendant details
    - metadata    : engine, ayanamsa, schema version
    """
    strengths = compute_planet_strengths(bundle)
    lordships = compute_house_lordships(bundle)
    aspects = compute_relationship_graph(bundle)
    nak_features = extract_nakshatra_features(bundle)
    sandhi = compute_sandhi_analysis(bundle)
    vargottama = _detect_vargottama(bundle)
    rashi_drishti = compute_rashi_drishti(bundle)
    drishti_matrix = compute_full_drishti_matrix(bundle)
    varga_analysis = extract_varga_analysis(bundle)

    # Build per-planet record
    planets_out: dict[str, dict] = {}
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        s = strengths[graha.value]
        nf = nak_features["planets"][graha.value]
        sh = sandhi[graha.value]
        asp_details = aspects["graha_aspects"][graha.value]

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
            # Aspect details with strength
            "aspects_to_houses": [a["house"] for a in asp_details],
            "aspect_details": asp_details,
            # Position flags
            "in_kendra": p.house in KENDRA_HOUSES,
            "in_trikona": p.house in TRIKONA_HOUSES,
            "in_dusthana": p.house in DUSTHANA_HOUSES,
            # Cusp analysis
            "is_sandhi": sh["is_sandhi"],
            "is_bhava_madhya": sh["is_bhava_madhya"],
            "sandhi_label": sh["label"],
            "distance_from_cusp": sh["distance_from_cusp"],
            # Vargottama flag
            "is_vargottama": vargottama.get(graha.value, False),
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
            "total_aspect_strength": round(aspects["aspect_strength_on_house"][h], 2),
        }

    # Yoga detection
    yogas = {
        "kemadruma": _detect_kemadruma(bundle),
        "gajakesari": _detect_gajakesari(bundle),
        "raja_yogas": _detect_raja_yogas(bundle, lordships),
        "dhana_yogas": _detect_dhana_yogas(bundle, lordships),
        "pancha_mahapurusha": _detect_pancha_mahapurusha(bundle),
        "neechabhanga": _detect_neechabhanga(bundle),
        "viparita_raja_yogas": _detect_viparita_raja_yoga(bundle, lordships),
    }

    return {
        "planets": planets_out,
        "houses": houses_out,
        "aspects": {
            "graha_aspects": aspects["graha_aspects"],
            "conjunctions": aspects["conjunctions"],
            "sign_exchanges": aspects["sign_exchanges"],
            "mutual_house_aspects": aspects["mutual_house_aspects"],
        },
        "drishti": {
            "rashi_drishti": rashi_drishti,
            "matrix": drishti_matrix,
        },
        "yogas": yogas,
        "sandhi": sandhi,
        "vargas": _build_varga_summary(bundle),
        "varga_analysis": varga_analysis,
        "lagna": _build_lagna_features(bundle, lordships),
        "nakshatra_ascendant": nak_features["ascendant"],
        "metadata": {
            "engine": bundle.engine,
            "ayanamsa": bundle.ayanamsa,
            "node_type": bundle.node_type,
            "schema_version": bundle.schema_version,
        },
    }
