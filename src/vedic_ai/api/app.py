"""FastAPI application factory for Vedic AI."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from vedic_ai.core.config import AppConfig
from vedic_ai.api.routes_chart import router as chart_router
from vedic_ai.api.routes_prediction import router as prediction_router


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

    return app
