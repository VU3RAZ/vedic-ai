"""Planetary dignity lookup tables and computation.

Covers: exalted, debilitated, moolatrikona, own sign.
Friend/neutral/enemy relationships are computed in Phase 3 feature extraction.
"""

from vedic_ai.domain.enums import Dignity, Graha, Rasi

# Rasi → natural lord (Vedic system)
RASI_LORDS: dict[Rasi, Graha] = {
    Rasi.ARIES: Graha.MARS,
    Rasi.TAURUS: Graha.VENUS,
    Rasi.GEMINI: Graha.MERCURY,
    Rasi.CANCER: Graha.MOON,
    Rasi.LEO: Graha.SUN,
    Rasi.VIRGO: Graha.MERCURY,
    Rasi.LIBRA: Graha.VENUS,
    Rasi.SCORPIO: Graha.MARS,
    Rasi.SAGITTARIUS: Graha.JUPITER,
    Rasi.CAPRICORN: Graha.SATURN,
    Rasi.AQUARIUS: Graha.SATURN,
    Rasi.PISCES: Graha.JUPITER,
}

# Exaltation: (sign, peak_degree)
_EXALTATION: dict[Graha, tuple[Rasi, float]] = {
    Graha.SUN: (Rasi.ARIES, 10.0),
    Graha.MOON: (Rasi.TAURUS, 3.0),
    Graha.MARS: (Rasi.CAPRICORN, 28.0),
    Graha.MERCURY: (Rasi.VIRGO, 15.0),
    Graha.JUPITER: (Rasi.CANCER, 5.0),
    Graha.VENUS: (Rasi.PISCES, 27.0),
    Graha.SATURN: (Rasi.LIBRA, 20.0),
    Graha.RAHU: (Rasi.TAURUS, 20.0),
    Graha.KETU: (Rasi.SCORPIO, 20.0),
}

# Debilitation sign
_DEBILITATION: dict[Graha, Rasi] = {
    Graha.SUN: Rasi.LIBRA,
    Graha.MOON: Rasi.SCORPIO,
    Graha.MARS: Rasi.CANCER,
    Graha.MERCURY: Rasi.PISCES,
    Graha.JUPITER: Rasi.CAPRICORN,
    Graha.VENUS: Rasi.VIRGO,
    Graha.SATURN: Rasi.ARIES,
    Graha.RAHU: Rasi.SCORPIO,
    Graha.KETU: Rasi.TAURUS,
}

# Own signs
_OWN_SIGNS: dict[Graha, list[Rasi]] = {
    Graha.SUN: [Rasi.LEO],
    Graha.MOON: [Rasi.CANCER],
    Graha.MARS: [Rasi.ARIES, Rasi.SCORPIO],
    Graha.MERCURY: [Rasi.GEMINI, Rasi.VIRGO],
    Graha.JUPITER: [Rasi.SAGITTARIUS, Rasi.PISCES],
    Graha.VENUS: [Rasi.TAURUS, Rasi.LIBRA],
    Graha.SATURN: [Rasi.CAPRICORN, Rasi.AQUARIUS],
    Graha.RAHU: [],
    Graha.KETU: [],
}

# Moolatrikona: (sign, degree_start, degree_end)
_MOOLATRIKONA: dict[Graha, tuple[Rasi, float, float]] = {
    Graha.SUN: (Rasi.LEO, 0.0, 20.0),
    Graha.MOON: (Rasi.TAURUS, 4.0, 20.0),
    Graha.MARS: (Rasi.ARIES, 0.0, 12.0),
    Graha.MERCURY: (Rasi.VIRGO, 16.0, 20.0),
    Graha.JUPITER: (Rasi.SAGITTARIUS, 0.0, 10.0),
    Graha.VENUS: (Rasi.LIBRA, 0.0, 15.0),
    Graha.SATURN: (Rasi.AQUARIUS, 0.0, 20.0),
}


def compute_dignity(graha: Graha, rasi: Rasi, degree_in_rasi: float) -> Dignity | None:
    """Return the dignity of a graha in a given sign position.

    Priority: exalted > debilitated > moolatrikona > own.
    Friend/neutral/enemy is deferred to Phase 3 feature extraction.
    Returns None when no special dignity applies.
    """
    if graha in _EXALTATION and _EXALTATION[graha][0] == rasi:
        return Dignity.EXALTED

    if graha in _DEBILITATION and _DEBILITATION[graha] == rasi:
        return Dignity.DEBILITATED

    if graha in _MOOLATRIKONA:
        mt_rasi, mt_start, mt_end = _MOOLATRIKONA[graha]
        if rasi == mt_rasi and mt_start <= degree_in_rasi <= mt_end:
            return Dignity.MOOLATRIKONA

    if rasi in _OWN_SIGNS.get(graha, []):
        return Dignity.OWN

    return None
