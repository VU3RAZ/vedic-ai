"""Prediction routes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.prediction import PredictionReport

router = APIRouter()

_VALID_SCOPES = ("personality", "career", "relationships", "health")

# ---------------------------------------------------------------------------
# Module-level config + retriever (loaded once at import time)
# ---------------------------------------------------------------------------

def _load_models_config() -> dict:
    models_path = Path("configs/models.yaml")
    if not models_path.exists():
        return {}
    try:
        return yaml.safe_load(models_path.read_text()) or {}
    except Exception:
        return {}


_models_config: dict = _load_models_config()

_DEFAULT_INDEX_DIR = Path("data/processed")
_DEFAULT_CORPUS_DIR = Path("data/processed/corpus")


def _try_load_retriever():
    """Load FAISS retriever if the index exists; return None otherwise."""
    handle_path = _DEFAULT_INDEX_DIR / "handle.json"
    manifest_path = _DEFAULT_CORPUS_DIR / "manifest.json"

    if not handle_path.exists() or not manifest_path.exists():
        return None

    try:
        from vedic_ai.retrieval.corpus_loader import load_manifest
        from vedic_ai.retrieval.chunker import chunk_corpus_documents
        from vedic_ai.retrieval.vector_store import load_vector_index
        from vedic_ai.retrieval.retriever import create_retriever

        manifest = load_manifest(str(manifest_path))
        chunks = chunk_corpus_documents(manifest)
        handle, _ = load_vector_index(str(handle_path))
        return create_retriever(chunks, handle)
    except Exception:
        return None


try:
    _retriever = _try_load_retriever()
except Exception:
    _retriever = None


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    birth_datetime: datetime
    latitude: float
    longitude: float
    place_name: str | None = None
    name: str | None = None
    scope: str = "all"
    dry_run: bool = False
    raman_method: bool = False   # Emphasise B.V. Raman-style house analysis in retrieval


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/scopes")
def list_scopes() -> list[str]:
    """Return the list of supported prediction scopes."""
    return list(_VALID_SCOPES)


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

    # Resolve scope list
    if request.scope == "all":
        scopes = list(_VALID_SCOPES)
    elif request.scope in _VALID_SCOPES:
        scopes = [request.scope]
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown scope {request.scope!r}. Choose: all, {', '.join(_VALID_SCOPES)}"
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

    # Build LLM client from models.yaml config
    llm_client = None
    if not request.dry_run:
        try:
            from vedic_ai.llm.local_client import LocalLLMClient
            backend = _models_config.get("llm", {}).get("backend", "ollama")
            backend_cfg = _models_config.get("llm", {}).get(backend, {})
            llm_client = LocalLLMClient(
                model_name=backend_cfg.get("model", "mistral:7b-instruct"),
                base_url=backend_cfg.get("base_url", "http://localhost:11434"),
                backend=backend,
                timeout=backend_cfg.get("timeout_seconds", 600),
            )
        except Exception:
            pass

    try:
        from vedic_ai.orchestration.pipeline import run_prediction_pipeline

        if len(scopes) == 1:
            report = run_prediction_pipeline(
                birth=birth,
                scope=scopes[0],
                llm_client=llm_client,
                retriever=_retriever,
                top_k=5,
                dry_run=request.dry_run or llm_client is None,
                raman_method=request.raman_method,
            )
        else:
            # Run all scopes and merge sections into one report
            report = None
            for s in scopes:
                r = run_prediction_pipeline(
                    birth=birth,
                    scope=s,
                    llm_client=llm_client,
                    retriever=_retriever,
                    top_k=5,
                    dry_run=request.dry_run or llm_client is None,
                    raman_method=request.raman_method,
                )
                if report is None:
                    report = r
                else:
                    report.sections.extend(r.sections)
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    return report.model_dump(mode="json")
