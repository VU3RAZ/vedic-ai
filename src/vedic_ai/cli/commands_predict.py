"""CLI predict command: birth data → PredictionReport."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from vedic_ai.cli.main import app
from vedic_ai.core.config import load_app_config
from vedic_ai.core.exceptions import ConfigError
from vedic_ai.domain.birth import BirthData, GeoLocation


@app.command()
def predict(
    datetime_str: str = typer.Argument(
        ..., help="Birth datetime ISO-8601 with TZ offset, e.g. '1990-04-05T10:00:00+05:30'"
    ),
    latitude: float = typer.Argument(..., help="Latitude in decimal degrees"),
    longitude: float = typer.Argument(..., help="Longitude in decimal degrees"),
    scope: str = typer.Option("career", "--scope", "-s", help="Prediction scope"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Native's name"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Skip the LLM call; return evidence-only report"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write JSON report to file"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to app.yaml", envvar="VEDIC_AI_CONFIG"
    ),
) -> None:
    """Generate a Vedic astrology prediction report from birth data."""
    try:
        cfg = load_app_config(str(config) if config else None)
    except ConfigError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1)

    try:
        birth_dt = datetime.fromisoformat(datetime_str)
    except ValueError as exc:
        typer.echo(f"Invalid datetime format: {exc}", err=True)
        raise typer.Exit(code=1)

    if birth_dt.tzinfo is None:
        typer.echo("Birth datetime must include a timezone offset (e.g. +05:30).", err=True)
        raise typer.Exit(code=1)

    birth = BirthData(
        birth_datetime=birth_dt,
        location=GeoLocation(latitude=latitude, longitude=longitude),
        name=name,
    )

    from vedic_ai.orchestration.pipeline import run_prediction_pipeline

    llm_client = None
    if not dry_run:
        try:
            from vedic_ai.llm.local_client import LocalLLMClient
            models_config = _load_models_config()
            backend = models_config.get("llm", {}).get("backend", "ollama")
            backend_cfg = models_config.get("llm", {}).get(backend, {})
            llm_client = LocalLLMClient(
                model_name=backend_cfg.get("model", "mistral:7b-instruct"),
                base_url=backend_cfg.get("base_url", "http://localhost:11434"),
                backend=backend,
            )
        except Exception as exc:
            typer.echo(f"LLM setup failed ({exc}); falling back to dry-run.", err=True)
            dry_run = True

    try:
        report = run_prediction_pipeline(
            birth=birth,
            scope=scope,
            llm_client=llm_client,
            dry_run=dry_run,
        )
    except Exception as exc:
        typer.echo(f"Pipeline error: {exc}", err=True)
        raise typer.Exit(code=1)

    report_json = json.dumps(report.model_dump(mode="json"), indent=2)

    if output:
        output.write_text(report_json, encoding="utf-8")
        typer.echo(f"Report written to {output}")
    else:
        typer.echo(report_json)


def _load_models_config() -> dict:
    models_path = Path("configs/models.yaml")
    if not models_path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(models_path.read_text()) or {}
    except Exception:
        return {}
