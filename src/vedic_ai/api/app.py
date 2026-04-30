"""FastAPI application factory for Vedic AI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from vedic_ai.core.config import AppConfig
from vedic_ai.api.routes_chart import router as chart_router
from vedic_ai.api.routes_prediction import router as prediction_router

_STATIC_DIR = Path(__file__).parent.parent / "static"


def create_api_app(config: AppConfig | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        config: Optional AppConfig; if None, loads from default path.

    Returns:
        Configured FastAPI application with chart and prediction routers.
    """
    app = FastAPI(
        title="Vedic AI",
        description="Local-first Vedic astrology prediction API",
        version="1.0.0",
    )

    app.include_router(chart_router, prefix="/charts", tags=["charts"])
    app.include_router(prediction_router, prefix="/predictions", tags=["predictions"])

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "service": "vedic-ai"}

    # Serve static files if the directory exists
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

        @app.get("/", include_in_schema=False)
        def serve_index() -> FileResponse:
            return FileResponse(str(_STATIC_DIR / "index.html"))

    return app
