"""Integration tests for Phase 12: cache, repository, and reproducibility."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.prediction import (
    PredictionReport,
    PredictionSection,
)
from vedic_ai.storage.cache import (
    build_cache_key,
    cache_chart_bundle,
    invalidate_cache_entry,
    load_cached_chart_bundle,
)
from vedic_ai.storage.repository import list_reports, load_report, save_report
from vedic_ai.utils.repro import build_reproducibility_manifest

FIXTURES_DIR = Path(__file__).parents[2] / "data" / "fixtures"


@pytest.fixture
def fixture_bundle():
    path = FIXTURES_DIR / "sample_chart_a.json"
    if not path.exists():
        pytest.skip("sample_chart_a.json not available")
    from vedic_ai.domain.chart import deserialize_chart_bundle
    return deserialize_chart_bundle(json.loads(path.read_text()))


@pytest.fixture
def sample_report() -> PredictionReport:
    return PredictionReport(
        birth_name="Test Native",
        chart_bundle_id="abc123",
        generated_at=datetime.now(timezone.utc),
        sections=[PredictionSection(scope="career", summary="Career summary", details=[])],
        model_name="test-model",
    )


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestChartCache:
    def test_cache_and_load(self, fixture_bundle, tmp_path):
        db = tmp_path / "cache.db"
        key = "test_key_001"
        cache_chart_bundle(key, fixture_bundle, db_path=db)
        loaded = load_cached_chart_bundle(key, db_path=db)
        assert loaded is not None
        assert loaded.engine == fixture_bundle.engine

    def test_cache_miss_returns_none(self, tmp_path):
        db = tmp_path / "cache.db"
        result = load_cached_chart_bundle("missing_key", db_path=db)
        assert result is None

    def test_cache_miss_when_db_absent(self, tmp_path):
        db = tmp_path / "nonexistent.db"
        result = load_cached_chart_bundle("any_key", db_path=db)
        assert result is None

    def test_cached_bundle_passes_schema_validation(self, fixture_bundle, tmp_path):
        db = tmp_path / "cache.db"
        key = "validate_key"
        cache_chart_bundle(key, fixture_bundle, db_path=db)
        loaded = load_cached_chart_bundle(key, db_path=db)
        assert loaded is not None
        assert loaded.schema_version == fixture_bundle.schema_version

    def test_invalidate_removes_entry(self, fixture_bundle, tmp_path):
        db = tmp_path / "cache.db"
        key = "delete_me"
        cache_chart_bundle(key, fixture_bundle, db_path=db)
        assert load_cached_chart_bundle(key, db_path=db) is not None
        invalidate_cache_entry(key, db_path=db)
        assert load_cached_chart_bundle(key, db_path=db) is None

    def test_build_cache_key_is_deterministic(self):
        birth = BirthData(
            birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone.utc),
            location=GeoLocation(latitude=28.6, longitude=77.2),
        )
        k1 = build_cache_key(birth, {"engine": "swisseph"})
        k2 = build_cache_key(birth, {"engine": "swisseph"})
        assert k1 == k2

    def test_different_births_give_different_keys(self):
        birth_a = BirthData(
            birth_datetime=datetime(1990, 4, 5, 10, 0, tzinfo=timezone.utc),
            location=GeoLocation(latitude=28.6, longitude=77.2),
        )
        birth_b = BirthData(
            birth_datetime=datetime(1985, 1, 1, 6, 0, tzinfo=timezone.utc),
            location=GeoLocation(latitude=19.0, longitude=72.8),
        )
        assert build_cache_key(birth_a) != build_cache_key(birth_b)

    def test_replace_existing_entry(self, fixture_bundle, tmp_path):
        db = tmp_path / "cache.db"
        key = "replace_me"
        cache_chart_bundle(key, fixture_bundle, db_path=db)
        cache_chart_bundle(key, fixture_bundle, db_path=db)  # should not raise
        loaded = load_cached_chart_bundle(key, db_path=db)
        assert loaded is not None


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestReportRepository:
    def test_save_and_load(self, sample_report, tmp_path):
        db = tmp_path / "reports.db"
        rid = save_report(sample_report, db_path=db)
        loaded = load_report(rid, db_path=db)
        assert loaded is not None
        assert loaded.birth_name == "Test Native"

    def test_load_missing_returns_none(self, tmp_path):
        db = tmp_path / "reports.db"
        result = load_report("nonexistent_id", db_path=db)
        assert result is None

    def test_load_when_db_absent_returns_none(self, tmp_path):
        db = tmp_path / "no.db"
        result = load_report("any_id", db_path=db)
        assert result is None

    def test_list_reports_returns_list(self, sample_report, tmp_path):
        db = tmp_path / "reports.db"
        save_report(sample_report, db_path=db)
        listing = list_reports(db_path=db)
        assert isinstance(listing, list)
        assert len(listing) == 1

    def test_list_reports_has_metadata_keys(self, sample_report, tmp_path):
        db = tmp_path / "reports.db"
        save_report(sample_report, db_path=db)
        listing = list_reports(db_path=db)
        entry = listing[0]
        assert "report_id" in entry
        assert "birth_name" in entry
        assert "scope" in entry

    def test_list_empty_when_db_absent(self, tmp_path):
        db = tmp_path / "no.db"
        assert list_reports(db_path=db) == []

    def test_saved_report_round_trips(self, sample_report, tmp_path):
        db = tmp_path / "reports.db"
        rid = save_report(sample_report, db_path=db)
        loaded = load_report(rid, db_path=db)
        assert loaded is not None
        payload = loaded.model_dump(mode="json")
        assert json.dumps(payload)


# ---------------------------------------------------------------------------
# Reproducibility manifest tests
# ---------------------------------------------------------------------------

class TestReproManifest:
    def test_returns_dict(self, sample_report):
        manifest = build_reproducibility_manifest(sample_report)
        assert isinstance(manifest, dict)

    def test_has_required_keys(self, sample_report):
        manifest = build_reproducibility_manifest(sample_report)
        for key in ("schema_version", "model_name", "generated_at", "packages", "corpus_hash", "sections"):
            assert key in manifest, f"Missing key: {key}"

    def test_schema_version_matches_report(self, sample_report):
        manifest = build_reproducibility_manifest(sample_report)
        assert manifest["schema_version"] == sample_report.schema_version

    def test_model_name_matches_report(self, sample_report):
        manifest = build_reproducibility_manifest(sample_report)
        assert manifest["model_name"] == sample_report.model_name

    def test_sections_list_correct(self, sample_report):
        manifest = build_reproducibility_manifest(sample_report)
        assert manifest["sections"] == ["career"]

    def test_manifest_serialises(self, sample_report):
        manifest = build_reproducibility_manifest(sample_report)
        assert json.dumps(manifest)

    def test_corpus_hash_no_corpus(self, sample_report, tmp_path):
        manifest = build_reproducibility_manifest(sample_report, corpus_dir=tmp_path / "nodir")
        assert manifest["corpus_hash"] == "no-corpus"

    def test_corpus_hash_with_corpus(self, sample_report, tmp_path):
        corpus_dir = tmp_path / "texts"
        corpus_dir.mkdir()
        (corpus_dir / "test.txt").write_text("nakshatra text")
        manifest = build_reproducibility_manifest(sample_report, corpus_dir=corpus_dir)
        assert manifest["corpus_hash"] != "no-corpus"
        assert len(manifest["corpus_hash"]) == 16
