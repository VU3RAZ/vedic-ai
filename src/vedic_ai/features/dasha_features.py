"""Dasha timing features: active Mahadasha / Antardasha at a given date."""

from __future__ import annotations

from datetime import date, datetime, timezone

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.engines.vimshottari import compute_antardasha_periods


def get_active_mahadasha(dashas: list[DashaPeriod], at_date: date) -> DashaPeriod | None:
    """Return the level-1 Mahadasha period that contains at_date, or None."""
    for period in dashas:
        if period.level == 1 and period.start_date <= at_date < period.end_date:
            return period
    return None


def get_active_antardasha(mahadasha: DashaPeriod, at_date: date) -> DashaPeriod | None:
    """Return the level-2 Antardasha within mahadasha that contains at_date, or None."""
    sub_periods = compute_antardasha_periods(mahadasha)
    for sub in sub_periods:
        if sub.start_date <= at_date < sub.end_date:
            return sub
    return None


def compute_timing_features(bundle: ChartBundle, at_time: datetime) -> dict:
    """Return active dasha timing facts for a given moment as a nested feature dict.

    Returns a dict with a single top-level key 'timing' containing nested dicts
    for 'mahadasha', 'antardasha', and 'reference_date', compatible with the
    dot-notation rule evaluator (e.g. timing.mahadasha.lord).
    """
    at_date = at_time.astimezone(timezone.utc).date()

    dashas = bundle.dashas
    maha = get_active_mahadasha(dashas, at_date)

    maha_dict: dict = {
        "lord": maha.graha.value if maha else None,
        "start": maha.start_date.isoformat() if maha else None,
        "end": maha.end_date.isoformat() if maha else None,
    }

    antar_dict: dict = {"lord": None, "start": None, "end": None}
    if maha is not None:
        antar = get_active_antardasha(maha, at_date)
        if antar:
            antar_dict = {
                "lord": antar.graha.value,
                "start": antar.start_date.isoformat(),
                "end": antar.end_date.isoformat(),
            }

    return {
        "timing": {
            "reference_date": at_date.isoformat(),
            "mahadasha": maha_dict,
            "antardasha": antar_dict,
        }
    }
