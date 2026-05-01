"""Divisional chart (Varga) sign computation.

Given a planet's natal rasi and degree within that sign, returns the sign
it occupies in the requested divisional chart.

Supported divisions:
  D2  Hora           — wealth / luminaries
  D3  Drekkana       — siblings, courage, longevity
  D4  Chaturthamsha  — property, fixed assets, fortune
  D6  Shashthamsha   — health, disease, enemies
  D7  Saptamsha      — children, progeny
  D8  Ashtamsha      — longevity, obstacles, calamities
  D9  Navamsa        — marriage, dharma, chart strength (most important)
  D10 Dasamsa        — career, profession, status
  D12 Dvadashamsha   — parents, ancestral lineage
  D16 Shodashamsha   — vehicles, comforts, happiness
  D20 Vimshamsha     — spiritual progress, religious life
  D24 Chaturvimshamsha — education, learning, knowledge
  D27 Saptavimshamsha  — strength, vitality, physical constitution
  D30 Trimshamsha    — misfortune, disease, past karma
  D60 Shashtiamsha   — general karma, overall life themes
"""

from __future__ import annotations

from vedic_ai.domain.enums import Rasi

_RASI_SEQUENCE: list[Rasi] = list(Rasi)

_ODD_SIGNS: frozenset[Rasi] = frozenset({
    Rasi.ARIES, Rasi.GEMINI, Rasi.LEO,
    Rasi.LIBRA, Rasi.SAGITTARIUS, Rasi.AQUARIUS,
})
_MOVEABLE_SIGNS: frozenset[Rasi] = frozenset({
    Rasi.ARIES, Rasi.CANCER, Rasi.LIBRA, Rasi.CAPRICORN,
})
_FIXED_SIGNS: frozenset[Rasi] = frozenset({
    Rasi.TAURUS, Rasi.LEO, Rasi.SCORPIO, Rasi.AQUARIUS,
})
_FIRE_SIGNS: frozenset[Rasi] = frozenset({Rasi.ARIES, Rasi.LEO, Rasi.SAGITTARIUS})
_EARTH_SIGNS: frozenset[Rasi] = frozenset({Rasi.TAURUS, Rasi.VIRGO, Rasi.CAPRICORN})
_AIR_SIGNS: frozenset[Rasi] = frozenset({Rasi.GEMINI, Rasi.LIBRA, Rasi.AQUARIUS})
# Water signs: Cancer, Scorpio, Pisces (remainder)

# D30 Trimshamsha: section boundaries and sign assignments per sign parity
# Odd signs: Mars(0-5°)→Aries, Saturn(5-10°)→Aquarius, Jupiter(10-18°)→Sagittarius,
#            Mercury(18-25°)→Gemini, Venus(25-30°)→Libra
# Even signs: Venus(0-5°)→Taurus, Mercury(5-12°)→Virgo, Jupiter(12-20°)→Pisces,
#             Saturn(20-25°)→Capricorn, Mars(25-30°)→Scorpio
_D30_ODD: list[tuple[float, int]] = [
    (5.0, 0),   # Aries
    (10.0, 10), # Aquarius
    (18.0, 8),  # Sagittarius
    (25.0, 2),  # Gemini
    (30.0, 6),  # Libra
]
_D30_EVEN: list[tuple[float, int]] = [
    (5.0, 1),   # Taurus
    (12.0, 5),  # Virgo
    (20.0, 11), # Pisces
    (25.0, 9),  # Capricorn
    (30.0, 7),  # Scorpio
]


def _clamp(deg: float) -> float:
    return min(max(deg, 0.0), 29.9999)


def compute_varga_rasi(natal_rasi: Rasi, degree_in_sign: float, division: str) -> Rasi:
    """Return the varga sign for a planet at a given natal position.

    Args:
        natal_rasi: The planet's natal zodiac sign.
        degree_in_sign: Degrees within that sign (0 to <30).
        division: Varga code — see module docstring for supported values.

    Returns:
        The Rasi the planet occupies in the divisional chart.

    Raises:
        ValueError: For an unsupported division code.
    """
    idx = _RASI_SEQUENCE.index(natal_rasi)
    deg = _clamp(degree_in_sign)

    # ── D2 Hora ────────────────────────────────────────────────────────────
    if division == "D2":
        # Odd signs: 0-15° → Leo (4), 15-30° → Cancer (3)
        # Even signs: 0-15° → Cancer (3), 15-30° → Leo (4)
        if natal_rasi in _ODD_SIGNS:
            return _RASI_SEQUENCE[4 if deg < 15.0 else 3]
        else:
            return _RASI_SEQUENCE[3 if deg < 15.0 else 4]

    # ── D3 Drekkana ────────────────────────────────────────────────────────
    if division == "D3":
        part = min(int(deg / 10), 2)
        return _RASI_SEQUENCE[(idx + [0, 4, 8][part]) % 12]

    # ── D4 Chaturthamsha ───────────────────────────────────────────────────
    if division == "D4":
        # 4 × 7.5° — each part adds 3 signs (kendra sequence) from natal sign
        part = min(int(deg / 7.5), 3)
        return _RASI_SEQUENCE[(idx + part * 3) % 12]

    # ── D6 Shashthamsha ────────────────────────────────────────────────────
    if division == "D6":
        # 6 × 5° — odd signs start from sign itself, even from 7th (opposite)
        part = min(int(deg / 5), 5)
        start = idx if natal_rasi in _ODD_SIGNS else (idx + 6) % 12
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D7 Saptamsha ───────────────────────────────────────────────────────
    if division == "D7":
        part = min(int(deg * 7 / 30), 6)
        start = idx if natal_rasi in _ODD_SIGNS else (idx + 6) % 12
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D8 Ashtamsha ───────────────────────────────────────────────────────
    if division == "D8":
        # 8 × 3°45' — moveable from sign, fixed from 9th (+8), dual from 5th (+4)
        part = min(int(deg / 3.75), 7)
        if natal_rasi in _MOVEABLE_SIGNS:
            start = idx
        elif natal_rasi in _FIXED_SIGNS:
            start = (idx + 8) % 12
        else:  # dual/mutable
            start = (idx + 4) % 12
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D9 Navamsa ─────────────────────────────────────────────────────────
    if division == "D9":
        part = min(int(deg * 9 / 30), 8)
        if natal_rasi in _FIRE_SIGNS:
            start = 0   # Aries
        elif natal_rasi in _EARTH_SIGNS:
            start = 9   # Capricorn
        elif natal_rasi in _AIR_SIGNS:
            start = 6   # Libra
        else:
            start = 3   # Cancer (water)
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D10 Dasamsa ────────────────────────────────────────────────────────
    if division == "D10":
        part = min(int(deg / 3), 9)
        start = idx if natal_rasi in _ODD_SIGNS else (idx + 8) % 12
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D12 Dvadashamsha ───────────────────────────────────────────────────
    if division == "D12":
        part = min(int(deg / 2.5), 11)
        return _RASI_SEQUENCE[(idx + part) % 12]

    # ── D16 Shodashamsha ───────────────────────────────────────────────────
    if division == "D16":
        # 16 × 1°52.5' — odd from Aries (0), even from Cancer (3)
        part = min(int(deg / 1.875), 15)
        start = 0 if natal_rasi in _ODD_SIGNS else 3
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D20 Vimshamsha ─────────────────────────────────────────────────────
    if division == "D20":
        # 20 × 1.5° — moveable from Aries(0), fixed from Leo(4), dual from Sagittarius(8)
        part = min(int(deg / 1.5), 19)
        if natal_rasi in _MOVEABLE_SIGNS:
            start = 0
        elif natal_rasi in _FIXED_SIGNS:
            start = 4
        else:
            start = 8
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D24 Chaturvimshamsha ───────────────────────────────────────────────
    if division == "D24":
        # 24 × 1.25° — odd from Leo(4), even from Cancer(3)
        part = min(int(deg / 1.25), 23)
        start = 4 if natal_rasi in _ODD_SIGNS else 3
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D27 Saptavimshamsha ────────────────────────────────────────────────
    if division == "D27":
        # 27 × 1°6.67' — fire→Aries(0), earth→Cancer(3), air→Libra(6), water→Capricorn(9)
        part = min(int(deg * 27 / 30), 26)
        if natal_rasi in _FIRE_SIGNS:
            start = 0
        elif natal_rasi in _EARTH_SIGNS:
            start = 3
        elif natal_rasi in _AIR_SIGNS:
            start = 6
        else:
            start = 9
        return _RASI_SEQUENCE[(start + part) % 12]

    # ── D30 Trimshamsha ────────────────────────────────────────────────────
    if division == "D30":
        table = _D30_ODD if natal_rasi in _ODD_SIGNS else _D30_EVEN
        for (boundary, sign_idx) in table:
            if deg < boundary:
                return _RASI_SEQUENCE[sign_idx]
        return _RASI_SEQUENCE[table[-1][1]]

    # ── D60 Shashtiamsha ───────────────────────────────────────────────────
    if division == "D60":
        # 60 × 0.5° — odd signs: sequential from Aries; even signs: sequential from Pisces (reverse)
        part = min(int(deg / 0.5), 59)
        if natal_rasi in _ODD_SIGNS:
            return _RASI_SEQUENCE[part % 12]
        else:
            return _RASI_SEQUENCE[(11 - part % 12) % 12]

    raise ValueError(
        f"Unsupported varga {division!r}. Supported: "
        "D2, D3, D4, D6, D7, D8, D9, D10, D12, D16, D20, D24, D27, D30, D60"
    )
