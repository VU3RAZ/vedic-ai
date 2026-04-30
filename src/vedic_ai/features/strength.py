"""Planetary strength computation.

Combines structural dignities (exalted/moolatrikona/own/debilitated from
engines/dignity.py) with natural relationship dignity (friend/neutral/enemy)
derived from planetary friendship tables.
"""

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.enums import Dignity, Graha, Rasi
from vedic_ai.engines.dignity import RASI_LORDS, compute_dignity
from vedic_ai.features.base import HOUSE_TYPES

# ---------------------------------------------------------------------------
# Natural planetary friendship tables (Naisargika Maitri)
# ---------------------------------------------------------------------------
_NATURAL_FRIENDS: dict[Graha, frozenset[Graha]] = {
    Graha.SUN:     frozenset({Graha.MOON, Graha.MARS, Graha.JUPITER}),
    Graha.MOON:    frozenset({Graha.SUN, Graha.MERCURY}),
    Graha.MARS:    frozenset({Graha.SUN, Graha.MOON, Graha.JUPITER}),
    Graha.MERCURY: frozenset({Graha.SUN, Graha.VENUS}),
    Graha.JUPITER: frozenset({Graha.SUN, Graha.MOON, Graha.MARS}),
    Graha.VENUS:   frozenset({Graha.MERCURY, Graha.SATURN}),
    Graha.SATURN:  frozenset({Graha.MERCURY, Graha.VENUS}),
    Graha.RAHU:    frozenset({Graha.MERCURY, Graha.VENUS, Graha.SATURN}),
    Graha.KETU:    frozenset({Graha.MARS, Graha.VENUS, Graha.SATURN}),
}

_NATURAL_ENEMIES: dict[Graha, frozenset[Graha]] = {
    Graha.SUN:     frozenset({Graha.VENUS, Graha.SATURN}),
    Graha.MOON:    frozenset(),
    Graha.MARS:    frozenset({Graha.MERCURY}),
    Graha.MERCURY: frozenset({Graha.MOON}),
    Graha.JUPITER: frozenset({Graha.MERCURY, Graha.VENUS}),
    Graha.VENUS:   frozenset({Graha.SUN, Graha.MOON}),
    Graha.SATURN:  frozenset({Graha.SUN, Graha.MOON, Graha.MARS}),
    Graha.RAHU:    frozenset({Graha.SUN, Graha.MOON, Graha.MARS}),
    Graha.KETU:    frozenset({Graha.SUN, Graha.MOON}),
}

# Dignity → numeric score for strength aggregation
DIGNITY_SCORES: dict[str, float] = {
    Dignity.EXALTED.value:      1.00,
    Dignity.MOOLATRIKONA.value: 0.75,
    Dignity.OWN.value:          0.50,
    "friend":                   0.25,
    "neutral":                  0.00,
    "enemy":                   -0.25,
    Dignity.DEBILITATED.value: -0.50,
}

_HOUSE_STRENGTH: dict[str, float] = {
    "angular":   0.30,
    "succedent": 0.15,
    "cadent":    0.00,
}

_RETROGRADE_PENALTY = 0.10


def natural_relationship(graha: Graha, sign_lord: Graha) -> str:
    """Return 'friend', 'neutral', or 'enemy' based on natural planetary friendship."""
    if graha == sign_lord:
        return "own"
    if sign_lord in _NATURAL_FRIENDS[graha]:
        return "friend"
    if sign_lord in _NATURAL_ENEMIES[graha]:
        return "enemy"
    return "neutral"


def full_dignity(graha: Graha, rasi: Rasi, degree_in_rasi: float) -> str | None:
    """Return the highest-priority dignity string for a planet in a sign.

    Priority: exalted > debilitated > moolatrikona > own > friend/neutral/enemy.
    Returns None when placement is neutral and no special condition applies.
    """
    structural = compute_dignity(graha, rasi, degree_in_rasi)
    if structural is not None:
        return structural.value

    sign_lord = RASI_LORDS[rasi]
    rel = natural_relationship(graha, sign_lord)
    return rel if rel != "neutral" else None


def compute_planet_strengths(bundle: ChartBundle) -> dict[str, dict]:
    """Compute dignity and house-based strength indicators for each graha.

    Returns:
        dict keyed by Graha name with strength metadata.
    """
    result: dict[str, dict] = {}
    for graha in Graha:
        p = bundle.d1.planets[graha.value]
        dignity_str = full_dignity(graha, p.rasi.rasi, p.rasi.degree_in_rasi)
        dignity_score = DIGNITY_SCORES.get(dignity_str, 0.0) if dignity_str else 0.0

        house_type = HOUSE_TYPES[p.house]
        house_bonus = _HOUSE_STRENGTH[house_type]
        retrograde_penalty = _RETROGRADE_PENALTY if p.is_retrograde else 0.0
        total = round(dignity_score + house_bonus - retrograde_penalty, 4)

        result[graha.value] = {
            "graha": graha.value,
            "dignity": dignity_str,
            "dignity_score": dignity_score,
            "house_type": house_type,
            "house_strength_bonus": house_bonus,
            "is_retrograde": p.is_retrograde,
            "retrograde_penalty": retrograde_penalty,
            "total_strength": total,
            "is_exalted": dignity_str == Dignity.EXALTED.value,
            "is_debilitated": dignity_str == Dignity.DEBILITATED.value,
            "is_own_sign": dignity_str in (Dignity.OWN.value, Dignity.MOOLATRIKONA.value),
            "in_friend_sign": dignity_str == "friend",
            "in_enemy_sign": dignity_str == "enemy",
        }
    return result
