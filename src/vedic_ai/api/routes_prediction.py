"""Prediction routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.prediction import PredictionReport

router = APIRouter()


class PredictionRequest(BaseModel):
    birth_datetime: datetime
    latitude: float
    longitude: float
    place_name: str | None = None
    name: str | None = None
    scope: str = "career"
    dry_run: bool = False


def export_report(report: PredictionReport, fmt: str = "json") -> str | dict:
    """Export a PredictionReport as JSON dict or Markdown string.

    Args:
        report: The prediction report to export.
        fmt: 'json' (default) or 'markdown'.

    Returns:
        dict when fmt='json', str when fmt='markdown'.
    """
    if fmt == "json":
        return report.model_dump(mode="json")

    lines = [f"# Prediction Report — {report.birth_name or 'Unknown'}"]
    lines.append(f"Generated: {report.generated_at.isoformat()}")
    lines.append(f"Model: {report.model_name}")
    lines.append("")
    for section in report.sections:
        lines.append(f"## {section.scope.capitalize()}")
        lines.append(section.summary)
        for detail in section.details:
            lines.append(f"- {detail}")
        lines.append("")
    return "\n".join(lines)


@router.post("")
def predict(request: PredictionRequest) -> dict:
    """Generate a Vedic astrology prediction report from birth data.

    Returns a serialized PredictionReport with scope-specific sections
    and evidence references.
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

    llm_client = None
    if not request.dry_run:
        try:
            from vedic_ai.llm.local_client import LocalLLMClient
            llm_client = LocalLLMClient(
                model_name="qwen2.5:14b",
                base_url="http://localhost:11434",
                backend="ollama",
            )
        except Exception:
            pass

    try:
        from vedic_ai.orchestration.pipeline import run_prediction_pipeline
        report = run_prediction_pipeline(
            birth=birth,
            scope=request.scope,
            llm_client=llm_client,
            dry_run=request.dry_run or llm_client is None,
        )
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    return report.model_dump(mode="json")
