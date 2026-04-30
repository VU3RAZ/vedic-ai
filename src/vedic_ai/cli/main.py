"""CLI entrypoint for the Vedic AI framework."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from vedic_ai.core.config import load_app_config
from vedic_ai.core.exceptions import ConfigError
from vedic_ai.core.logging import setup_logging

app = typer.Typer(
    name="vedic-ai",
    help="Local Vedic astrology AI framework.",
    add_completion=False,
)

_config_option = typer.Option(
    None,
    "--config",
    "-c",
    help="Path to app.yaml config file.",
    envvar="VEDIC_AI_CONFIG",
)


def _bootstrap(config_path: Optional[Path]) -> None:
    """Load config and set up logging. Called at the start of every command."""
    try:
        cfg = load_app_config(str(config_path) if config_path else None)
    except ConfigError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1)
    setup_logging(cfg.log.level, cfg.log.json_logs)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Optional[Path] = _config_option,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit."),
) -> None:
    """Vedic AI — local-first Jyotish horoscope analysis."""
    if version:
        from vedic_ai import __version__
        typer.echo(f"vedic-ai {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def info(
    config: Optional[Path] = _config_option,
) -> None:
    """Show resolved configuration."""
    _bootstrap(config)
    try:
        cfg = load_app_config(str(config) if config else None)
    except ConfigError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1)
    import json
    typer.echo(json.dumps(cfg.model_dump(), indent=2))


def register_cli() -> typer.Typer:
    """Return the root CLI app object.

    Later phases register their sub-commands against this app.
    """
    return app
