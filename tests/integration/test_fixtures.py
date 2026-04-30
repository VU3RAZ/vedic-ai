"""Integration tests: load JSON fixture files and validate them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vedic_ai.domain.chart import deserialize_chart_bundle, validate_chart_bundle
from vedic_ai.domain.enums import Graha

FIXTURES_DIR = Path(__file__).parent.parent.parent / "data" / "fixtures"
FIXTURE_FILES = ["sample_chart_a.json", "sample_chart_b.json", "sample_chart_c.json"]


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.mark.parametrize("filename", FIXTURE_FILES)
def test_fixture_file_exists(filename: str) -> None:
    assert (FIXTURES_DIR / filename).exists(), (
        f"Fixture not found: {FIXTURES_DIR / filename}. "
        "Run: python scripts/gen_fixtures.py"
    )


@pytest.mark.parametrize("filename", FIXTURE_FILES)
def test_fixture_validates_cleanly(filename: str) -> None:
    if not (FIXTURES_DIR / filename).exists():
        pytest.skip("fixture file not generated yet")
    errors = validate_chart_bundle(_load(filename))
    assert errors == [], f"{filename} validation errors: {errors}"


@pytest.mark.parametrize("filename", FIXTURE_FILES)
def test_fixture_deserializes(filename: str) -> None:
    if not (FIXTURES_DIR / filename).exists():
        pytest.skip("fixture file not generated yet")
    bundle = deserialize_chart_bundle(_load(filename))
    assert bundle.schema_version
    assert bundle.birth.birth_datetime.tzinfo is not None


@pytest.mark.parametrize("filename", FIXTURE_FILES)
def test_fixture_has_all_nine_grahas(filename: str) -> None:
    if not (FIXTURES_DIR / filename).exists():
        pytest.skip("fixture file not generated yet")
    bundle = deserialize_chart_bundle(_load(filename))
    assert set(bundle.d1.planets.keys()) == {g.value for g in Graha}


@pytest.mark.parametrize("filename", FIXTURE_FILES)
def test_fixture_has_twelve_houses(filename: str) -> None:
    if not (FIXTURES_DIR / filename).exists():
        pytest.skip("fixture file not generated yet")
    bundle = deserialize_chart_bundle(_load(filename))
    assert set(bundle.d1.houses.keys()) == set(range(1, 13))


def test_chart_a_sun_is_exalted() -> None:
    if not (FIXTURES_DIR / "sample_chart_a.json").exists():
        pytest.skip("fixture file not generated yet")
    bundle = deserialize_chart_bundle(_load("sample_chart_a.json"))
    assert bundle.d1.planets[Graha.SUN.value].dignity is not None
    assert bundle.d1.planets[Graha.SUN.value].dignity.value == "exalted"


def test_chart_b_kemadruma_houses_empty() -> None:
    """H2 (Leo) and H12 (Gemini) must be empty for Kemadruma yoga."""
    if not (FIXTURES_DIR / "sample_chart_b.json").exists():
        pytest.skip("fixture file not generated yet")
    bundle = deserialize_chart_bundle(_load("sample_chart_b.json"))
    assert bundle.d1.houses[2].occupants == []
    assert bundle.d1.houses[12].occupants == []
