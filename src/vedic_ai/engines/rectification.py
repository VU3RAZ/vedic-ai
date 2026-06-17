"""Birth-time rectification engine.

Given an approximate birth datetime and a set of *known* life-event dates
(marriage, first child, career start, property purchase, …), this engine searches
candidate birth times and selects the one whose chart most strongly activates the
relevant bhāvas on those exact dates — the inverse of the Life Events Timeline.

Method
------
Birth time materially reshapes the chart:
  • the Lagna (ascendant) — hence every bhāva lordship,
  • the Moon's nakṣatra — hence the Vimśottarī daśā balance and *when* each
    daśā/antardaśā runs,
  • all divisional-chart positions (very time-sensitive).

For each candidate time we recompute the chart and, for every supplied event,
score the daśā/varga/gochara activation on that date via
``life_events.score_event_fit`` (with the classical age-prior disabled — the date
is a known fact). Summing across events gives a fitness; the time with the highest
fitness is the rectified birth time.

A two-stage search (coarse then fine) keeps the computation responsive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from vedic_ai.domain.birth import BirthData
from vedic_ai.engines.base import AstrologyEngine, compute_core_chart
from vedic_ai.engines.life_events import (
    compute_chara_karakas,
    compute_indu_lagna,
    score_event_fit,
)
from vedic_ai.domain.enums import Graha

# Divisional charts required for varga confirmation during scoring
_RECT_VARGAS = ["D4", "D7", "D9", "D10", "D16", "D20", "D24"]


@dataclass
class EventInput:
    domain_key: str
    actual_date: date


@dataclass
class RectCandidate:
    offset_minutes: int
    birth_datetime: datetime
    total_fit: float
    lagna_sign: str
    moon_sign: str
    moon_nakshatra: str
    per_event: list[dict] = field(default_factory=list)


@dataclass
class RectificationResult:
    original: RectCandidate
    best: RectCandidate
    candidates: list[RectCandidate]
    window_minutes: int
    coarse_step: int
    fine_step: int
    evaluated: int


def _evaluate(
    base: BirthData,
    engine: AstrologyEngine,
    events: list[EventInput],
    offset_minutes: int,
    use_transits: bool,
) -> RectCandidate:
    """Build the chart for base-time + offset and score it against all events."""
    cand_dt = base.birth_datetime + timedelta(minutes=offset_minutes)
    cand_birth = BirthData(
        birth_datetime=cand_dt,
        location=base.location,
        name=base.name,
    )
    bundle = compute_core_chart(cand_birth, engine, include_vargas=_RECT_VARGAS)
    chara = compute_chara_karakas(bundle)
    indu = compute_indu_lagna(bundle)

    per_event: list[dict] = []
    total = 0.0
    for ev in events:
        fit = score_event_fit(
            bundle, ev.domain_key, ev.actual_date, chara, indu,
            engine if use_transits else None,
        )
        if fit is None:
            per_event.append({
                "domain_key": ev.domain_key,
                "actual_date": ev.actual_date.isoformat(),
                "score": None,
                "note": "no active daśā / unknown domain / date out of range",
            })
            continue
        total += fit["score"]
        per_event.append({
            "domain_key":      ev.domain_key,
            "label":           fit["label"],
            "emoji":           fit["emoji"],
            "actual_date":     ev.actual_date.isoformat(),
            "score":           fit["score"],
            "dasha_score":     fit["dasha_score"],
            "varga_score":     fit["varga_score"],
            "transit_score":   fit["transit_score"],
            "mahadasha_lord":  fit["mahadasha_lord"],
            "antardasha_lord": fit["antardasha_lord"],
            "factors":         fit["factors"][:5],
        })

    moon = bundle.d1.planets[Graha.MOON.value]
    return RectCandidate(
        offset_minutes=offset_minutes,
        birth_datetime=cand_dt,
        total_fit=round(total, 2),
        lagna_sign=bundle.d1.houses[1].rasi.value,
        moon_sign=moon.rasi.rasi.value,
        moon_nakshatra=moon.nakshatra.nakshatra.value,
        per_event=per_event,
    )


def rectify(
    birth: BirthData,
    engine: AstrologyEngine,
    events: list[EventInput],
    window_minutes: int = 120,
    coarse_step: int = 15,
    fine_step: int = 2,
    top_n: int = 6,
    use_transits: bool = True,
) -> RectificationResult:
    """Search ±`window_minutes` around the given birth time for the best fit.

    Stage 1 (coarse): step every `coarse_step` minutes across the window.
    Stage 2 (fine): step every `fine_step` minutes around the best coarse hit.

    Returns the original-time candidate, the best (rectified) candidate, and the
    top-N candidates by fitness.
    """
    if not events:
        raise ValueError("At least one known event date is required for rectification.")

    cache: dict[int, RectCandidate] = {}

    def ev(offset: int) -> RectCandidate:
        if offset not in cache:
            cache[offset] = _evaluate(birth, engine, events, offset, use_transits)
        return cache[offset]

    # Stage 1 — coarse sweep
    coarse_offsets = list(range(-window_minutes, window_minutes + 1, coarse_step))
    coarse = [ev(o) for o in coarse_offsets]
    best_coarse = max(coarse, key=lambda c: c.total_fit)

    # Stage 2 — fine sweep around the best coarse offset
    lo = max(-window_minutes, best_coarse.offset_minutes - coarse_step)
    hi = min(window_minutes, best_coarse.offset_minutes + coarse_step)
    for o in range(lo, hi + 1, fine_step):
        ev(o)

    ordered = sorted(cache.values(), key=lambda c: -c.total_fit)
    original = ev(0)

    return RectificationResult(
        original=original,
        best=ordered[0],
        candidates=ordered[:top_n],
        window_minutes=window_minutes,
        coarse_step=coarse_step,
        fine_step=fine_step,
        evaluated=len(cache),
    )
