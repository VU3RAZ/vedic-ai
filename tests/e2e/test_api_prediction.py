"""End-to-end tests for the FastAPI prediction and chart endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vedic_ai.api.app import create_api_app
from vedic_ai.domain.chart import deserialize_chart_bundle
from vedic_ai.domain.prediction import PredictionReport

FIXTURES_DIR = Path(__file__).parents[2] / "data" / "fixtures"

_BIRTH_PAYLOAD = {
    "birth_datetime": "1990-04-05T10:00:00+05:30",
    "latitude": 28.6,
    "longitude": 77.2,
    "place_name": "Delhi",
    "name": "Test Native",
    "scope": "career",
    "dry_run": True,
}


@pytest.fixture(scope="module")
def fixture_bundle():
    path = FIXTURES_DIR / "sample_chart_a.json"
    if not path.exists():
        pytest.skip("sample_chart_a.json not available")
    return deserialize_chart_bundle(json.loads(path.read_text()))


@pytest.fixture(scope="module")
def client(fixture_bundle):
    app = create_api_app()
    engine_mock = MagicMock()
    engine_mock.compute_birth_chart.return_value = fixture_bundle
    engine_mock.compute_dashas.return_value = []

    with patch("vedic_ai.orchestration.pipeline.KerykeionAdapter", return_value=engine_mock):
        with patch("vedic_ai.api.routes_chart.SwissEphAdapter", return_value=engine_mock):
            with TestClient(app) as c:
                yield c


class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestPredictEndpoint:
    def test_predict_returns_200(self, client):
        resp = client.post("/predictions", json=_BIRTH_PAYLOAD)
        assert resp.status_code == 200, resp.text

    def test_predict_returns_sections(self, client):
        resp = client.post("/predictions", json=_BIRTH_PAYLOAD)
        payload = resp.json()
        assert "sections" in payload
        assert len(payload["sections"]) == 1

    def test_predict_scope_matches(self, client):
        resp = client.post("/predictions", json=_BIRTH_PAYLOAD)
        payload = resp.json()
        assert payload["sections"][0]["scope"] == "career"

    def test_predict_has_schema_version(self, client):
        resp = client.post("/predictions", json=_BIRTH_PAYLOAD)
        payload = resp.json()
        assert "schema_version" in payload

    def test_predict_personality_scope(self, client):
        body = {**_BIRTH_PAYLOAD, "scope": "personality"}
        resp = client.post("/predictions", json=body)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["sections"][0]["scope"] == "personality"

    def test_predict_naive_datetime_fails(self, client):
        body = {**_BIRTH_PAYLOAD, "birth_datetime": "1990-04-05T10:00:00"}
        resp = client.post("/predictions", json=body)
        assert resp.status_code == 422

    def test_predict_birth_name_in_response(self, client):
        body = {**_BIRTH_PAYLOAD, "name": "Arjuna"}
        resp = client.post("/predictions", json=body)
        payload = resp.json()
        assert payload["birth_name"] == "Arjuna"


class TestExportReport:
    def test_export_json_returns_dict(self):
        from datetime import datetime, timezone
        from vedic_ai.domain.prediction import PredictionSection
        from vedic_ai.api.routes_prediction import export_report

        report = PredictionReport(
            birth_name="Test",
            generated_at=datetime.now(timezone.utc),
            sections=[PredictionSection(scope="career", summary="s", details=["d"])],
            model_name="test",
        )
        result = export_report(report, "json")
        assert isinstance(result, dict)
        assert "sections" in result

    def test_export_markdown_returns_string(self):
        from datetime import datetime, timezone
        from vedic_ai.domain.prediction import PredictionSection
        from vedic_ai.api.routes_prediction import export_report

        report = PredictionReport(
            birth_name="Test",
            generated_at=datetime.now(timezone.utc),
            sections=[PredictionSection(scope="career", summary="Career is strong", details=["detail"])],
            model_name="test",
        )
        result = export_report(report, "markdown")
        assert isinstance(result, str)
        assert "Career" in result
        assert "Career is strong" in result

    def test_export_markdown_contains_details(self):
        from datetime import datetime, timezone
        from vedic_ai.domain.prediction import PredictionSection
        from vedic_ai.api.routes_prediction import export_report

        report = PredictionReport(
            birth_name="Test",
            generated_at=datetime.now(timezone.utc),
            sections=[PredictionSection(scope="career", summary="s", details=["my detail"])],
            model_name="test",
        )
        result = export_report(report, "markdown")
        assert "my detail" in result
