"""Per-bhava dasha activation and transit pressure analysis.

For each of the 12 bhavas, computes:
  - dasha_activation: is the current mahadasha/antardasha lord activating this bhava?
  - transit_pressure: which planets are transiting through this bhava's sign?
"""

from __future__ import annotations

_BHAVA_NAMES = {
    1:  "Lagna — Self, constitution, personality, appearance",
    2:  "Dhana — Wealth, speech, family, accumulated assets",
    3:  "Sahaja — Siblings, courage, communication, short journeys",
    4:  "Sukha — Mother, home, property, domestic happiness",
    5:  "Putra — Children, intelligence, creativity, past karma",
    6:  "Ari — Enemies, disease, debt, service, litigation",
    7:  "Kalatra — Spouse, partnerships, business, public",
    8:  "Ayu — Longevity, transformation, hidden matters, occult",
    9:  "Dharma — Father, guru, fortune, religion, higher learning",
    10: "Karma — Career, status, authority, public reputation",
    11: "Labha — Gains, elder siblings, desires, social network",
    12: "Vyaya — Losses, liberation, foreign lands, expenses, moksha",
}

_DUSTHANA = {6, 8, 12}
_KENDRA   = {1, 4, 7, 10}
_TRIKONA  = {1, 5, 9}


def get_bhava_name(bhava: int) -> str:
    return _BHAVA_NAMES.get(bhava, f"Bhava {bhava}")


def compute_bhava_dasha_activation(features: dict, bhava: int) -> dict:
    """Determine how strongly the current dasha activates a given bhava.

    Checks both mahadasha and antardasha lords against:
      1. Is the lord the bhava lord?
      2. Does the lord occupy the bhava?
      3. Does the lord aspect the bhava (graha or rashi drishti)?
      4. Is the bhava lord in a kendra/trikona (strengthens activation)?

    Returns a structured dict with activation flags and notes.
    """
    houses = features.get("houses", {})
    bhava_data = houses.get(bhava, {})
    bhava_lord = bhava_data.get("lord")
    occupants = bhava_data.get("occupants", [])
    aspects_received = bhava_data.get("aspects_received_from", [])

    dasha_strength = features.get("dasha_strength", {})
    maha = dasha_strength.get("mahadasha", {})
    antar = dasha_strength.get("antardasha", {})

    maha_lord = maha.get("lord")
    antar_lord = antar.get("lord")

    def _check_lord(lord: str | None) -> dict:
        if not lord:
            return {"lord": None, "is_bhava_lord": False, "occupies_bhava": False,
                    "aspects_bhava": False, "activation_score": 0, "notes": []}
        notes = []
        score = 0

        is_bhava_lord = (lord == bhava_lord)
        if is_bhava_lord:
            notes.append(f"{lord} is the lord of bhava {bhava}")
            score += 3

        occupies = lord in occupants
        if occupies:
            notes.append(f"{lord} occupies bhava {bhava}")
            score += 3

        aspects = lord in aspects_received
        if aspects:
            notes.append(f"{lord} aspects bhava {bhava}")
            score += 2

        # Bhava lord placement bonus
        if is_bhava_lord:
            lord_house = features.get("planets", {}).get(lord, {}).get("house")
            if lord_house in _KENDRA:
                notes.append(f"Bhava lord {lord} is in a kendra (H{lord_house}) — strong activation")
                score += 1
            elif lord_house in _TRIKONA:
                notes.append(f"Bhava lord {lord} is in a trikona (H{lord_house}) — good activation")
                score += 1
            elif lord_house in _DUSTHANA:
                notes.append(f"Bhava lord {lord} is in a dusthana (H{lord_house}) — challenged activation")
                score -= 1

        return {
            "lord": lord,
            "is_bhava_lord": is_bhava_lord,
            "occupies_bhava": occupies,
            "aspects_bhava": aspects,
            "activation_score": max(0, score),
            "notes": notes,
        }

    maha_check  = _check_lord(maha_lord)
    antar_check = _check_lord(antar_lord)

    total_score = maha_check["activation_score"] + antar_check["activation_score"]
    level = "high" if total_score >= 5 else "moderate" if total_score >= 2 else "low"

    return {
        "bhava": bhava,
        "bhava_name": get_bhava_name(bhava),
        "bhava_lord": bhava_lord,
        "bhava_occupants": occupants,
        "mahadasha": {
            "lord": maha_lord,
            "period": f"{maha.get('start','')} – {maha.get('end','')}",
            **{k: v for k, v in maha_check.items() if k != "lord"},
        },
        "antardasha": {
            "lord": antar_lord,
            **{k: v for k, v in antar_check.items() if k != "lord"},
        },
        "total_activation_score": total_score,
        "activation_level": level,
    }


def compute_bhava_transit_pressure(features: dict, bhava: int,
                                   gochara_context: dict | None) -> dict:
    """Summarise which planets are currently transiting through a bhava's sign.

    Uses gochara_context (pre-computed by the Gochara engine) when available,
    otherwise falls back to the transit snapshot embedded in features.
    """
    houses = features.get("houses", {})
    bhava_sign = houses.get(bhava, {}).get("rasi") or houses.get(bhava, {}).get("sign")

    transiting_planets: list[dict] = []

    if gochara_context:
        # Pull from pre-computed gochara findings
        for planet_report in gochara_context.get("planet_reports", []):
            if planet_report.get("transit_house") == bhava:
                transiting_planets.append({
                    "planet": planet_report.get("planet"),
                    "transit_sign": planet_report.get("transit_sign"),
                    "effect": planet_report.get("overall_effect", ""),
                    "score": planet_report.get("score"),
                })

    return {
        "bhava": bhava,
        "bhava_sign": bhava_sign,
        "transiting_planets": transiting_planets,
        "has_transit_pressure": len(transiting_planets) > 0,
    }


def build_bhava_context_block(features: dict, bhava: int,
                               gochara_context: dict | None = None) -> str:
    """Build the BHAVA ACTIVATION text block for injection into LLM prompts."""
    activation = compute_bhava_dasha_activation(features, bhava)
    transit    = compute_bhava_transit_pressure(features, bhava, gochara_context)

    lines = [
        f"BHAVA {bhava} — {get_bhava_name(bhava)}",
        f"  Lord: {activation['bhava_lord'] or '—'}  |  Occupants: {', '.join(activation['bhava_occupants']) or 'none'}",
        f"  Dasha activation: {activation['activation_level'].upper()} (score {activation['total_activation_score']})",
    ]

    for note in activation["mahadasha"].get("notes", []):
        lines.append(f"  • Mahadasha — {note}")
    for note in activation["antardasha"].get("notes", []):
        lines.append(f"  • Antardasha — {note}")

    if transit["transiting_planets"]:
        lines.append("  Current transits through this bhava:")
        for tp in transit["transiting_planets"]:
            effect = f" [{tp['effect']}]" if tp.get("effect") else ""
            lines.append(f"    - {tp['planet']} in {tp.get('transit_sign','?')}{effect}")
    else:
        lines.append("  No planets currently transiting this bhava.")

    return "\n".join(lines)
