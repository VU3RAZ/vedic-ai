"""Pure-Python Vimshottari dasha calculation.

Computes Mahadasha (level 1) and Antardasha (level 2) periods.
"""

from datetime import date, timedelta

from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.domain.enums import Graha

# Vimshottari sequence with period lengths in years (total = 120)
VIMSHOTTARI_SEQUENCE: list[Graha] = [
    Graha.KETU,
    Graha.VENUS,
    Graha.SUN,
    Graha.MOON,
    Graha.MARS,
    Graha.RAHU,
    Graha.JUPITER,
    Graha.SATURN,
    Graha.MERCURY,
]

VIMSHOTTARI_YEARS: dict[Graha, int] = {
    Graha.KETU: 7,
    Graha.VENUS: 20,
    Graha.SUN: 6,
    Graha.MOON: 10,
    Graha.MARS: 7,
    Graha.RAHU: 18,
    Graha.JUPITER: 16,
    Graha.SATURN: 19,
    Graha.MERCURY: 17,
}

# Nakshatra lords in order (index 0 = Ashwini = Ketu, repeats every 9)
_NAKSHATRA_LORDS: list[Graha] = [
    Graha.KETU, Graha.VENUS, Graha.SUN, Graha.MOON, Graha.MARS,
    Graha.RAHU, Graha.JUPITER, Graha.SATURN, Graha.MERCURY,
] * 3  # 27 nakshatras = 3 × 9


def _add_years(d: date, years: float) -> date:
    return d + timedelta(days=round(years * 365.25))


def compute_vimshottari_dashas(
    moon_longitude: float,
    birth_date: date,
    span_years: int = 120,
) -> list[DashaPeriod]:
    """Return all Mahadasha periods from birth covering span_years.

    Args:
        moon_longitude: Moon's sidereal longitude at birth (0-360).
        birth_date: Date of birth.
        span_years: How many years of dashas to generate (default 120).
    """
    nak_span = 360.0 / 27.0  # ≈13.333°
    nak_index = int(moon_longitude / nak_span)  # 0-indexed nakshatra
    degree_in_nak = moon_longitude % nak_span
    progress = degree_in_nak / nak_span  # fraction elapsed in this nakshatra

    start_lord = _NAKSHATRA_LORDS[nak_index]
    start_lord_seq_idx = VIMSHOTTARI_SEQUENCE.index(start_lord)
    balance_years = (1.0 - progress) * VIMSHOTTARI_YEARS[start_lord]

    periods: list[DashaPeriod] = []
    current = birth_date
    end_of_span = _add_years(birth_date, span_years)

    # First dasha: the balance remaining in the birth nakshatra's dasha
    end = _add_years(current, balance_years)
    if current < end_of_span:
        periods.append(DashaPeriod(graha=start_lord, level=1, start_date=current, end_date=end))
    current = end

    # Remaining full dashas in cyclic sequence
    seq_idx = (start_lord_seq_idx + 1) % 9
    while current < end_of_span:
        graha = VIMSHOTTARI_SEQUENCE[seq_idx]
        years = VIMSHOTTARI_YEARS[graha]
        end = _add_years(current, years)
        periods.append(DashaPeriod(graha=graha, level=1, start_date=current, end_date=end))
        current = end
        seq_idx = (seq_idx + 1) % 9

    return periods


def compute_antardasha_periods(mahadasha: DashaPeriod) -> list[DashaPeriod]:
    """Return all Antardasha (level-2) sub-periods within a Mahadasha.

    Antardasha duration = (sub_lord_years / total_years) * mahadasha_duration.
    The sub-period sequence starts with the Mahadasha lord itself, then cycles.
    """
    maha_lord = mahadasha.graha
    maha_start_idx = VIMSHOTTARI_SEQUENCE.index(maha_lord)
    maha_days = (mahadasha.end_date - mahadasha.start_date).days

    sub_periods: list[DashaPeriod] = []
    current = mahadasha.start_date

    for i in range(9):
        sub_lord = VIMSHOTTARI_SEQUENCE[(maha_start_idx + i) % 9]
        sub_fraction = VIMSHOTTARI_YEARS[sub_lord] / 120.0
        sub_days = round(maha_days * sub_fraction)
        end = current + timedelta(days=sub_days)
        if end > mahadasha.end_date:
            end = mahadasha.end_date
        sub_periods.append(
            DashaPeriod(graha=sub_lord, level=2, start_date=current, end_date=end)
        )
        current = end

    return sub_periods
