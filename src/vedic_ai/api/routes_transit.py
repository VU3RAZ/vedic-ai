"""Transit (Gochara) analysis routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.engines.base import compute_core_chart
from vedic_ai.engines.gochara import GocharaReport, compute_gochara
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter

router = APIRouter()


class TransitRequest(BaseModel):
    # Birth data (natal chart)
    birth_datetime: datetime
    birth_latitude: float
    birth_longitude: float
    birth_place_name: str | None = None
    name: str | None = None

    # Transit datetime + optional location (defaults to birth location)
    transit_datetime: datetime
    transit_latitude: float | None = None
    transit_longitude: float | None = None

    ayanamsa: str = "lahiri"
    house_system: str = "whole_sign"


def _serialize_report(report: GocharaReport) -> dict:
    def _result(r):
        return {
            "graha":                    r.graha,
            "transit_sign":             r.transit_sign,
            "transit_house_from_moon":  r.transit_house_from_moon,
            "transit_house_from_lagna": r.transit_house_from_lagna,
            "natal_sign":               r.natal_sign,
            "natal_house":              r.natal_house,
            "result_key":               r.result_key,
            "short_effect":             r.short_effect,
            "detail":                   r.detail,
            "vedha_active":             r.vedha_active,
            "vedha_planet":             r.vedha_planet,
            "is_retrograde":            r.is_retrograde,
            "is_dasha_lord":            r.is_dasha_lord,
            "is_antardasha_lord":       r.is_antardasha_lord,
        }

    sadhe = report.sadhe_sati
    return {
        "transit_datetime":    report.transit_datetime.isoformat(),
        "natal_moon_sign":     report.natal_moon_sign,
        "natal_moon_house":    report.natal_moon_house,
        "natal_lagna_sign":    report.natal_lagna_sign,
        "current_mahadasha":   report.current_mahadasha,
        "current_antardasha":  report.current_antardasha,
        "mahadasha_end":       report.mahadasha_end,
        "antardasha_end":      report.antardasha_end,
        "planet_results":      [_result(r) for r in report.planet_results],
        "sadhe_sati": {
            "active":                 sadhe.active,
            "phase":                  sadhe.phase,
            "description":            sadhe.description,
            "saturn_house_from_moon": sadhe.saturn_house_from_moon,
        },
        "special_alerts": [
            {"name": a.name, "severity": a.severity, "description": a.description}
            for a in report.special_alerts
        ],
        "observations":      report.observations,
        "favorable_count":   report.favorable_count,
        "unfavorable_count": report.unfavorable_count,
        "mixed_count":       report.mixed_count,
        "overall_tone":      report.overall_tone,
        "remedies": [
            {
                "planet":         r.planet,
                "situation":      r.situation,
                "priority":       r.priority,
                "mantra":         r.mantra,
                "mantra_source":  r.mantra_source,
                "vedic_mantra":   r.vedic_mantra,
                "stotra":         r.stotra,
                "fast_day":       r.fast_day,
                "charity":        r.charity,
                "deity_puja":     r.deity_puja,
                "gemstone_note":  r.gemstone_note,
                "behavioral":     r.behavioral,
                "special_actions": r.special_actions,
                "source_refs":    r.source_refs,
            }
            for r in report.remedies
        ],
    }


@router.post("/compute")
def compute_transit(request: TransitRequest) -> dict:
    """Compute Gochara (transit) analysis for a native.

    Accepts birth data and a transit datetime. Returns:
      - Natal chart summary (Moon sign, Lagna, active dasha/antardasha)
      - Per-planet Gochara results (house from Moon, result, Vedha status)
      - Sadhe Sati / Ashtama Shani / Kantaka Shani detection
      - Special transit alerts (Guru Chandala, Mars-Saturn, etc.)
      - Rule-based observations and overall tone (no LLM required)
    """
    if request.birth_datetime.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="birth_datetime must include a timezone offset (e.g. +05:30)",
        )
    if request.transit_datetime.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="transit_datetime must include a timezone offset (e.g. +05:30)",
        )

    birth = BirthData(
        birth_datetime=request.birth_datetime,
        location=GeoLocation(
            latitude=request.birth_latitude,
            longitude=request.birth_longitude,
            place_name=request.birth_place_name,
        ),
        name=request.name,
    )

    # Transit location defaults to birth location if not provided
    transit_lat = request.transit_latitude  if request.transit_latitude  is not None else request.birth_latitude
    transit_lon = request.transit_longitude if request.transit_longitude is not None else request.birth_longitude

    try:
        engine = SwissEphAdapter(
            ayanamsa=request.ayanamsa,
            house_system=request.house_system,
        )
        # Compute natal chart with dashas (no vargas needed for gochara)
        natal_bundle = compute_core_chart(birth, engine, include_vargas=None)

        # Compute transit positions
        transit_snapshot = engine.compute_transits(birth, request.transit_datetime)

    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Gochara analysis — pure computation, no LLM
    try:
        report = compute_gochara(natal_bundle, transit_snapshot)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gochara analysis failed: {exc}")

    return _serialize_report(report)
