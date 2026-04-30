"""Chart computation routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.chart import ChartBundle, serialize_chart_bundle
from vedic_ai.engines.base import compute_core_chart
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter

router = APIRouter()


class ComputeChartRequest(BaseModel):
    birth_datetime: datetime
    latitude: float
    longitude: float
    place_name: str | None = None
    name: str | None = None
    ayanamsa: str = "lahiri"
    house_system: str = "whole_sign"


@router.post("/compute")
def compute_chart(request: ComputeChartRequest) -> dict:
    """Compute a natal chart from birth data.

    Returns a serialized ChartBundle including planets, houses, and dashas.
    """
    if request.birth_datetime.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="birth_datetime must include a timezone offset (e.g. +05:30)"
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
        bundle = compute_core_chart(birth, engine)
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return serialize_chart_bundle(bundle)
