"""Birth-time rectification API route."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.engines.life_events import list_domains
from vedic_ai.engines.rectification import (
    EventInput,
    RectCandidate,
    rectify,
)
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter

router = APIRouter()


class KnownEvent(BaseModel):
    domain_key: str
    actual_date: date


class RectifyRequest(BaseModel):
    birth_datetime: datetime
    latitude: float
    longitude: float
    place_name: str | None = None
    name: str | None = None
    ayanamsa: str = "lahiri"
    house_system: str = "whole_sign"
    events: list[KnownEvent] = Field(default_factory=list)
    window_minutes: int = Field(default=120, ge=5, le=720)
    coarse_step: int = Field(default=15, ge=1, le=60)
    fine_step: int = Field(default=2, ge=1, le=30)


@router.get("/domains")
def rectify_domains() -> dict:
    """Return the event-domain catalog usable as rectification anchors."""
    return {"domains": list_domains()}


def _serialize_candidate(c: RectCandidate) -> dict:
    return {
        "offset_minutes":  c.offset_minutes,
        "birth_datetime":  c.birth_datetime.isoformat(),
        "total_fit":       c.total_fit,
        "lagna_sign":      c.lagna_sign,
        "moon_sign":       c.moon_sign,
        "moon_nakshatra":  c.moon_nakshatra,
        "per_event":       c.per_event,
    }


@router.post("/compute")
def compute_rectification(request: RectifyRequest) -> dict:
    """Rectify the birth time against a set of known life-event dates.

    Searches candidate birth times within ±window_minutes and returns the time
    whose chart most strongly activates the supplied events (inverse of the Life
    Events Timeline). No LLM is used.
    """
    if request.birth_datetime.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="birth_datetime must include a timezone offset (e.g. +05:30)",
        )
    if not request.events:
        raise HTTPException(
            status_code=422,
            detail="At least one known event date is required for rectification.",
        )
    if request.fine_step > request.coarse_step:
        raise HTTPException(
            status_code=422,
            detail="fine_step must be ≤ coarse_step.",
        )

    birth = BirthData(
        birth_datetime=request.birth_datetime,
        location=GeoLocation(
            latitude=request.latitude,
            longitude=request.longitude,
            place_name=request.place_name,
        ),
        name=request.name,
    )
    events = [EventInput(domain_key=e.domain_key, actual_date=e.actual_date)
              for e in request.events]

    try:
        engine = SwissEphAdapter(
            ayanamsa=request.ayanamsa,
            house_system=request.house_system,
        )
        result = rectify(
            birth, engine, events,
            window_minutes=request.window_minutes,
            coarse_step=request.coarse_step,
            fine_step=request.fine_step,
        )
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Rectification failed: {exc}")

    delta = result.best.offset_minutes
    improvement = round(result.best.total_fit - result.original.total_fit, 2)

    return {
        "name":            request.name,
        "original":        _serialize_candidate(result.original),
        "best":            _serialize_candidate(result.best),
        "candidates":      [_serialize_candidate(c) for c in result.candidates],
        "delta_minutes":   delta,
        "fit_improvement": improvement,
        "lagna_changed":   result.best.lagna_sign != result.original.lagna_sign,
        "moon_sign_changed": result.best.moon_sign != result.original.moon_sign,
        "search": {
            "window_minutes": result.window_minutes,
            "coarse_step":    result.coarse_step,
            "fine_step":      result.fine_step,
            "evaluated":      result.evaluated,
        },
        "disclaimer": (
            "Rectification suggests the birth time best matching the supplied events "
            "per classical timing rules. It is probabilistic, not a substitute for an "
            "accurate birth record."
        ),
    }
