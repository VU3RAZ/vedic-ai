"""Life Events Timeline API route."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.engines.base import compute_core_chart
from vedic_ai.engines.life_events import (
    LifeEventPrediction,
    compute_chara_karakas,
    compute_indu_lagna,
    compute_life_events,
)
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter
from vedic_ai.features.core_features import extract_core_features

router = APIRouter()

_VARGAS_FOR_LIFE_EVENTS = ["D4", "D7", "D9", "D10", "D16", "D20", "D24"]

# Jaimini chara-kāraka role → meaning (for UI legend)
_KARAKA_MEANING = {
    "AK": "Ātmakāraka — self / soul",
    "AmK": "Amātyakāraka — career",
    "BK": "Bhrātṛkāraka — siblings",
    "MK": "Mātṛkāraka — mother / property",
    "PiK": "Pitṛkāraka — father",
    "PK": "Putrakāraka — children",
    "GK": "Gnātikāraka — disease / obstacles",
    "DK": "Darākāraka — spouse / marriage",
}


class LifeEventsRequest(BaseModel):
    birth_datetime: datetime
    latitude: float
    longitude: float
    place_name: str | None = None
    name: str | None = None
    ayanamsa: str = "lahiri"
    house_system: str = "whole_sign"


def _serialize_event(e: LifeEventPrediction) -> dict:
    return {
        "domain_key":        e.domain_key,
        "label":             e.label,
        "category":          e.category,
        "emoji":             e.emoji,
        "start_date":        e.start_date.isoformat(),
        "end_date":          e.end_date.isoformat(),
        "age_start":         e.age_start,
        "age_end":           e.age_end,
        "score":             e.score,
        "confidence":        e.confidence,
        "mahadasha_lord":    e.mahadasha_lord,
        "antardasha_lord":   e.antardasha_lord,
        "method_note":       e.method_note,
        "supporting_factors": e.supporting_factors,
        "divisional_signal": e.divisional_signal,
        "transit_signal":    e.transit_signal,
    }


@router.post("/compute")
def compute_life_events_route(request: LifeEventsRequest) -> dict:
    """Compute a 120-year life events timeline for a native.

    Combines Vimshottari dashas, natal house lordships, divisional charts
    (D4/D7/D9/D10/D16/D24), and classical karaka theory to predict probable
    timing windows for key life milestones.

    Returns a list of LifeEventPrediction objects sorted by predicted start date.
    """
    if request.birth_datetime.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="birth_datetime must include a timezone offset (e.g. +05:30)",
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

    try:
        engine = SwissEphAdapter(
            ayanamsa=request.ayanamsa,
            house_system=request.house_system,
        )
        bundle = compute_core_chart(birth, engine, include_vargas=_VARGAS_FOR_LIFE_EVENTS)
        bundle.derived_features = extract_core_features(bundle)
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        events = compute_life_events(bundle, engine=engine)
        chara = compute_chara_karakas(bundle)
        indu = compute_indu_lagna(bundle)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Life events computation failed: {exc}")

    # Summary stats
    by_category: dict[str, int] = {}
    for e in events:
        by_category[e.category] = by_category.get(e.category, 0) + 1

    # Jaimini Chara Kārakas (JS) — role → planet, with meaning
    chara_karakas = [
        {"role": role, "planet": graha.value, "meaning": _KARAKA_MEANING.get(role, role)}
        for graha, role in sorted(chara.items(), key=lambda kv: list(_KARAKA_MEANING).index(kv[1]))
    ]

    indu_lagna = None
    if indu is not None:
        indu_house, indu_lord = indu
        indu_lagna = {"house_from_lagna": indu_house, "lord": indu_lord.value}

    return {
        "name":           request.name,
        "birth_datetime": request.birth_datetime.isoformat(),
        "events":         [_serialize_event(e) for e in events],
        "total_events":   len(events),
        "by_category":    by_category,
        "methods": {
            "chara_karakas": chara_karakas,
            "indu_lagna":    indu_lagna,
            "references":    "BPHS 46-47, Jaimini Sūtras 1.1, BPHS 7 (Ṣoḍaśavarga), Jātaka Pārijāta, Phaladīpikā 26",
        },
    }
