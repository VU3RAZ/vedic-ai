"""End-to-end tests for the CLI predict command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Ensure the predict command is registered before importing app
import vedic_ai.cli.commands_predict  # noqa: F401
from vedic_ai.cli.main import app
from vedic_ai.domain.chart import deserialize_chart_bundle

runner = CliRunner()

FIXTURES_DIR = Path(__file__).parents[2] / "data" / "fixtures"

_CLI_ARGS = [
    "predict",
    "1990-04-05T10:00:00+05:30",
    "28.6",
    "77.2",
]


@pytest.fixture(autouse=True)
def _mock_engine(request):
    """Inject a fixture-backed mock engine into every test in this module."""
    path = FIXTURES_DIR / "sample_chart_a.json"
    if not path.exists():
        pytest.skip("Fixture sample_chart_a.json not generated")
    bundle = deserialize_chart_bundle(json.loads(path.read_text()))
    engine = MagicMock()
    engine.compute_birth_chart.return_value = bundle
    engine.compute_dashas.return_value = []
    with patch(
        "vedic_ai.orchestration.pipeline.KerykeionAdapter", return_value=engine
    ):
        yield engine


class TestCLIPredictCommand:
    def test_predict_dry_run_succeeds(self):
        result = runner.invoke(app, [*_CLI_ARGS, "--scope", "career", "--dry-run"])
        assert result.exit_code == 0, result.output

    def test_predict_output_is_json(self):
        result = runner.invoke(app, [*_CLI_ARGS, "--scope", "career", "--dry-run"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "sections" in payload

    def test_predict_section_scope_matches(self):
        result = runner.invoke(app, [*_CLI_ARGS, "--scope", "personality", "--dry-run"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["sections"][0]["scope"] == "personality"

    def test_predict_with_name(self):
        result = runner.invoke(app, [*_CLI_ARGS, "--name", "Arjuna", "--dry-run"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["birth_name"] == "Arjuna"

    def test_predict_output_to_file(self, tmp_path):
        out_file = tmp_path / "report.json"
        result = runner.invoke(
            app, [*_CLI_ARGS, "--dry-run", "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        payload = json.loads(out_file.read_text())
        assert "sections" in payload

    def test_predict_invalid_datetime_fails(self):
        result = runner.invoke(app, ["predict", "not-a-date", "28.6", "77.2", "--dry-run"])
        assert result.exit_code != 0

    def test_predict_naive_datetime_fails(self):
        result = runner.invoke(
            app, ["predict", "1990-04-05T10:00:00", "28.6", "77.2", "--dry-run"]
        )
        assert result.exit_code != 0

    def test_predict_report_has_schema_version(self):
        result = runner.invoke(app, [*_CLI_ARGS, "--dry-run"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "schema_version" in payload
