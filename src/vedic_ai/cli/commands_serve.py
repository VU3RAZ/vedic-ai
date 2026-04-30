"""CLI serve command: launch the FastAPI web server."""

from __future__ import annotations

from typing import Optional
from pathlib import Path

import typer

from vedic_ai.cli.main import app


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Bind address"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (development)"),
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to app.yaml", envvar="VEDIC_AI_CONFIG"
    ),
) -> None:
    """Launch the FastAPI web server."""
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "uvicorn is not installed. Install the api extras: pip install 'vedic-ai[api]'",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Vedic AI server running at http://{host}:{port}")
    uvicorn.run(
        "vedic_ai.api.app:create_api_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
