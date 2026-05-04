"""Query expansion for multi-query and HyDE retrieval strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vedic_ai.domain.prediction import RuleTrigger

# Scope-anchored vocabulary for baseline semantic queries
_SCOPE_ANCHORS: dict[str, str] = {
    "personality": (
        "lagna ascendant personality character temperament self-identity "
        "nature disposition mental makeup"
    ),
    "career": (
        "career profession vocation tenth house karma livelihood work "
        "occupation achievement public life status"
    ),
    "relationships": (
        "marriage spouse partnership seventh house Venus love union "
        "commitment relationship harmony"
    ),
    "health": (
        "health constitution disease longevity vitality sixth house "
        "eighth house body immunity ailment"
    ),
}

# Per-scope primary houses and their significance
_SCOPE_HOUSE_FOCUS: dict[str, list[int]] = {
    "personality": [1, 5, 9],
    "career": [10, 11, 2],
    "relationships": [7, 5, 11],
    "health": [1, 6, 8, 12],
}


def expand_queries(
    triggers: list[RuleTrigger],
    scope: str,
    features: dict,
    *,
    max_queries: int = 7,
) -> list[str]:
    """Generate diverse retrieval queries without calling an LLM.

    Produces queries targeting all corpus sources: classical texts (BPHS/Raman),
    nakshatra guide, yoga compendium, dasha timing, and aspects/exchanges.

    Returns a deduplicated list of up to max_queries strings, ordered from
    most-focused (specific trigger text) to most-general (scope anchor).
    """
    candidates: list[str] = []

    def _add(q: str) -> None:
        if q and q.strip() and q not in candidates:
            candidates.append(q)

    # Q1 — highest-weight single trigger (most specific, anchors BPHS/Raman)
    if triggers:
        top = max(triggers, key=lambda t: t.weight)
        _add(top.explanation)

    # Q2 — concatenated trigger explanations (breadth across classical texts)
    if triggers:
        _add(" ".join(t.explanation for t in triggers[:6]))

    # Q3 — nakshatra query (targets NAKSHATRA_GUIDE corpus)
    _add(_nakshatra_query(features, scope))

    # Q4 — dasha timing query (targets DASHA_TIMING corpus)
    _add(_dasha_query(features, scope))

    # Q5 — yoga-specific query (targets YOGA_COMPENDIUM corpus)
    _add(_yoga_query(features, scope))

    # Q6 — planet + house focused (reinforces BPHS house chapters)
    for q in _house_focused_queries(features, scope)[:2]:
        _add(q)

    # Q7 — scope anchor / vocabulary baseline
    _add(_SCOPE_ANCHORS.get(scope, scope))

    return candidates[:max_queries]


def hyde_query(
    scope: str,
    triggers: list[RuleTrigger],
    features: dict,
    llm_client: object,
) -> str:
    """Generate a Hypothetical Document Embedding (HyDE) query.

    Asks the LLM for a short synthetic passage it would *expect* to find in a
    classical text for this chart. The passage embedding is then used for
    retrieval — it searches for similar text rather than the original question.

    Returns an empty string on any failure (caller should skip HyDE silently).
    """
    summary = _chart_summary_for_hyde(features, scope, triggers)
    prompt = (
        "Write a 3-sentence passage from a classical Vedic astrology text "
        f"interpreting the following chart for {scope}: {summary}. "
        "Use traditional Jyotish terminology. Output only the passage text, "
        "no explanation, no markdown."
    )
    try:
        raw = llm_client.generate(prompt, temperature=0.1)  # type: ignore[attr-defined]
        return raw.strip()[:800]  # cap to avoid over-long embedding inputs
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _house_focused_queries(features: dict, scope: str) -> list[str]:
    """Build queries anchored to specific planet-house combinations."""
    queries: list[str] = []
    key_houses = _SCOPE_HOUSE_FOCUS.get(scope, [1])
    houses = features.get("houses", {})

    for h in key_houses[:2]:
        hd = houses.get(h, {})
        lord = hd.get("lord")
        lord_house = hd.get("lord_house")
        lord_rasi = hd.get("lord_rasi", "")
        occupants = hd.get("occupants", [])

        if lord and lord_house:
            queries.append(
                f"{lord} in {lord_rasi} house {lord_house} effects {scope}"
            )
        if occupants:
            planets = " ".join(occupants[:2])
            queries.append(f"{planets} in {h}th house {scope}")

    return queries


def _yoga_query(features: dict, scope: str) -> str:
    """Return a yoga-focused query string if notable yogas are active."""
    yogas = features.get("yogas", {})
    parts: list[str] = []

    if yogas.get("gajakesari"):
        parts.append("Gajakesari yoga Jupiter Moon intelligence wealth")
    if yogas.get("kemadruma"):
        parts.append("Kemadruma yoga isolated Moon challenges")

    for y in yogas.get("raja_yogas", [])[:2]:
        tl = y.get("trikona_lord", "")
        kl = y.get("kendra_lord", "")
        if tl and kl:
            parts.append(f"Raja yoga {tl} {kl} power authority")

    for y in yogas.get("pancha_mahapurusha", [])[:1]:
        name = y.get("name", "")
        graha = y.get("graha", "")
        if name:
            parts.append(f"{name} yoga {graha} Pancha Mahapurusha")

    if not parts:
        return ""

    scope_suffix = {
        "personality": "self character personality",
        "career": "career profession success",
        "relationships": "marriage spouse partnership",
        "health": "health vitality constitution",
    }.get(scope, "")

    return " ".join(parts[:2]) + " " + scope_suffix


def _nakshatra_query(features: dict, scope: str) -> str:
    """Query targeting the nakshatra corpus for Moon and Lagna nakshatras."""
    parts: list[str] = []

    lagna = features.get("lagna", {})
    lagna_nak = lagna.get("nakshatra")
    if lagna_nak:
        parts.append(f"{lagna_nak} nakshatra {scope} personality traits")

    planets = features.get("planets", {})
    moon_nak = planets.get("Moon", {}).get("nakshatra")
    if moon_nak and moon_nak != lagna_nak:
        parts.append(f"{moon_nak} nakshatra emotional nature relationships")

    return " ".join(parts)


def _dasha_query(features: dict, scope: str) -> str:
    """Query targeting the dasha timing corpus for current mahadasha/antardasha."""
    ds = features.get("dasha_strength", {})
    maha_lord = ds.get("mahadasha", {}).get("lord")
    antar_lord = ds.get("antardasha", {}).get("lord")

    if not maha_lord:
        return ""

    parts = [f"{maha_lord} mahadasha {scope} effects timing"]
    if antar_lord and antar_lord != maha_lord:
        parts.append(f"{maha_lord} {antar_lord} antardasha")
    return " ".join(parts)


def _chart_summary_for_hyde(
    features: dict,
    scope: str,
    triggers: list[RuleTrigger],
) -> str:
    """Compact chart description for the HyDE prompt."""
    parts: list[str] = []

    lagna = features.get("lagna", {})
    if lagna:
        parts.append(
            f"Lagna {lagna.get('rasi','?')} lord {lagna.get('lord','?')} "
            f"in house {lagna.get('lord_house','?')}"
        )

    # Top 2 triggers
    for t in sorted(triggers, key=lambda x: x.weight, reverse=True)[:2]:
        parts.append(t.explanation[:120])

    return "; ".join(parts) or scope
