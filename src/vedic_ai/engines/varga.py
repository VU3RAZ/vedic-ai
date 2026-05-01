"""Divisional chart (Varga) sign computation.

Given a planet's natal rasi and degree within that sign, returns the sign
it occupies in the requested divisional chart.

Supported divisions: D3 (Drekkana), D7 (Saptamsha), D9 (Navamsa),
                     D10 (Dasamsa), D12 (Dvadashamsha)
"""

from __future__ import annotations

from vedic_ai.domain.enums import Rasi

_RASI_SEQUENCE: list[Rasi] = list(Rasi)

_ODD_SIGNS: frozenset[Rasi] = frozenset({
    Rasi.ARIES, Rasi.GEMINI, Rasi.LEO,
    Rasi.LIBRA, Rasi.SAGITTARIUS, Rasi.AQUARIUS,
})
_FIRE_SIGNS: frozenset[Rasi] = frozenset({Rasi.ARIES, Rasi.LEO, Rasi.SAGITTARIUS})
_EARTH_SIGNS: frozenset[Rasi] = frozenset({Rasi.TAURUS, Rasi.VIRGO, Rasi.CAPRICORN})
_AIR_SIGNS: frozenset[Rasi] = frozenset({Rasi.GEMINI, Rasi.LIBRA, Rasi.AQUARIUS})
# Water signs are the remainder: Cancer, Scorpio, Pisces


def compute_varga_rasi(natal_rasi: Rasi, degree_in_sign: float, division: str) -> Rasi:
    """Return the varga sign for a planet at a given natal position.

    Args:
        natal_rasi: The planet's natal zodiac sign.
        degree_in_sign: Degrees within that sign (0 to <30).
        division: One of 'D3', 'D7', 'D9', 'D10', 'D12'.

    Returns:
        The Rasi the planet occupies in the divisional chart.

    Raises:
        ValueError: For an unsupported division code.
    """
    idx = _RASI_SEQUENCE.index(natal_rasi)
    deg = min(max(degree_in_sign, 0.0), 29.9999)  # guard against edge cases

    if division == "D3":
        # Drekkana — 3 × 10°: sign itself / 5th / 9th from sign
        part = min(int(deg / 10), 2)
        return _RASI_SEQUENCE[(idx + [0, 4, 8][part]) % 12]

    if division == "D7":
        # Saptamsha — 7 × 4°17': odd signs start from sign, even from 7th
        part = min(int(deg * 7 / 30), 6)
        start = idx if natal_rasi in _ODD_SIGNS else (idx + 6) % 12
        return _RASI_SEQUENCE[(start + part) % 12]

    if division == "D9":
        # Navamsa — 9 × 3°20'
        # Fire → Aries (0), Earth → Capricorn (9), Air → Libra (6), Water → Cancer (3)
        part = min(int(deg * 9 / 30), 8)
        if natal_rasi in _FIRE_SIGNS:
            start = 0
        elif natal_rasi in _EARTH_SIGNS:
            start = 9
        elif natal_rasi in _AIR_SIGNS:
            start = 6
        else:
            start = 3  # water
        return _RASI_SEQUENCE[(start + part) % 12]

    if division == "D10":
        # Dasamsa — 10 × 3°: odd from sign, even from 9th (index + 8)
        part = min(int(deg / 3), 9)
        start = idx if natal_rasi in _ODD_SIGNS else (idx + 8) % 12
        return _RASI_SEQUENCE[(start + part) % 12]

    if division == "D12":
        # Dvadashamsha — 12 × 2°30', always from the sign itself
        part = min(int(deg / 2.5), 11)
        return _RASI_SEQUENCE[(idx + part) % 12]

    raise ValueError(
        f"Unsupported varga {division!r}. Supported: D3, D7, D9, D10, D12"
    )
