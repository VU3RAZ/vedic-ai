"""Integration tests for the local LLM contract.

These tests require a running Ollama or LM Studio instance and are
skipped automatically when no server is reachable.

To run them manually:
    pytest tests/integration/test_local_llm_contract.py -v
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.chart import ChartBundle, DivisionalChart
from vedic_ai.domain.corpus import RetrievedPassage
from vedic_ai.domain.enums import Graha, NakshatraName, Rasi
from vedic_ai.domain.house import HousePlacement
from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement
from vedic_ai.domain.prediction import RuleTrigger
from vedic_ai.llm import (
    LocalLLMClient,
    build_interpretation_prompt,
    repair_llm_output,
    validate_llm_output,
)

# ---------------------------------------------------------------------------
# Availability check — skip all tests if no local LLM is reachable
# ---------------------------------------------------------------------------

_OLLAMA_URL = "http://localhost:11434"
_LMSTUDIO_URL = "http://localhost:1234"
_DEFAULT_MODEL = "qwen2.5:14b"


def _server_reachable(base_url: str) -> bool:
    try:
        import requests
        requests.get(base_url, timeout=2)
        return True
    except Exception:
        return False


ollama_available = _server_reachable(_OLLAMA_URL)
skip_no_llm = pytest.mark.skipif(
    not ollama_available,
    reason="No local LLM server reachable at localhost:11434",
)


# ---------------------------------------------------------------------------
# Fixture helpers (minimal chart, not full fixture suite)
# ---------------------------------------------------------------------------

def _minimal_bundle() -> ChartBundle:
    birth = BirthData(
        birth_datetime=datetime(1985, 6, 15, 6, 30, tzinfo=timezone.utc),
        location=GeoLocation(latitude=28.6, longitude=77.2),
    )
    sun = PlanetPlacement(
        graha=Graha.SUN,
        longitude=62.5,
        rasi=RasiPlacement(rasi=Rasi.GEMINI, degree_in_rasi=2.5),
        nakshatra=NakshatraPlacement(
            nakshatra=NakshatraName.MRIGASHIRSHA,
            pada=1,
            nakshatra_lord=Graha.MARS,
            degree_in_nakshatra=2.5,
        ),
        house=10,
        is_retrograde=False,
    )
    houses = {
        i: HousePlacement(
            number=i,
            rasi=Rasi.ARIES,
            cusp_longitude=float((i - 1) * 30),
            lord=Graha.MARS,
        )
        for i in range(1, 13)
    }
    d1 = DivisionalChart(
        division="D1",
        ascendant_longitude=10.5,
        planets={"Sun": sun},
        houses=houses,
    )
    return ChartBundle(birth=birth, engine="test", ayanamsa="lahiri", d1=d1)


_OUTPUT_SCHEMA = {
    "summary": "str",
    "details": "list",
    "rule_refs": "list",
    "passage_refs": "list",
}


# ---------------------------------------------------------------------------
# Prompt contract tests (no LLM needed — just test prompt shape)
# ---------------------------------------------------------------------------

class TestPromptContract:
    """Validate prompt structure without calling a live LLM."""

    def test_prompt_is_string(self):
        bundle = _minimal_bundle()
        trigger = RuleTrigger(
            rule_id="C001",
            rule_name="Sun in 10th",
            scope="career",
            weight=0.8,
            explanation="Prominence via Sun in 10th.",
        )
        passage = RetrievedPassage(
            chunk_id="bphs_024_0000",
            text="Sun in tenth house gives authority.",
            source="BPHS",
            score=0.9,
        )
        prompt = build_interpretation_prompt(
            bundle=bundle,
            features={"sun_in_10th": True},
            triggers=[trigger],
            passages=[passage],
            scope="career",
            output_schema=_OUTPUT_SCHEMA,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_prompt_contains_instruction_and_schema(self):
        bundle = _minimal_bundle()
        prompt = build_interpretation_prompt(
            bundle=bundle,
            features={},
            triggers=[],
            passages=[],
            scope="personality",
            output_schema=_OUTPUT_SCHEMA,
        )
        assert "unsupported claims" in prompt
        assert '"summary"' in prompt

    def test_prompt_snapshot_stable(self):
        bundle = _minimal_bundle()
        trigger = RuleTrigger(
            rule_id="P001",
            rule_name="Sun dignity",
            scope="personality",
            weight=0.5,
            explanation="Sun is dignified.",
        )
        p1 = build_interpretation_prompt(
            bundle=bundle,
            features={"x": 1},
            triggers=[trigger],
            passages=[],
            scope="personality",
            output_schema=_OUTPUT_SCHEMA,
        )
        p2 = build_interpretation_prompt(
            bundle=bundle,
            features={"x": 1},
            triggers=[trigger],
            passages=[],
            scope="personality",
            output_schema=_OUTPUT_SCHEMA,
        )
        assert p1 == p2


# ---------------------------------------------------------------------------
# Output parser contract tests (no LLM needed)
# ---------------------------------------------------------------------------

class TestOutputParserContract:
    def test_valid_output_passes_validation(self):
        payload = {
            "summary": "Career is strong.",
            "details": ["Sun in 10th confers prominence."],
            "rule_refs": ["C001"],
            "passage_refs": ["bphs_024_0000"],
        }
        errors = validate_llm_output(payload, _OUTPUT_SCHEMA)
        assert errors == []

    def test_missing_summary_fails(self):
        payload = {"details": [], "rule_refs": [], "passage_refs": []}
        errors = validate_llm_output(payload, _OUTPUT_SCHEMA)
        assert any("summary" in e for e in errors)

    def test_unsupported_key_rejected(self):
        payload = {
            "summary": "ok",
            "details": [],
            "rule_refs": [],
            "passage_refs": [],
            "hidden_field": "bad",
        }
        errors = validate_llm_output(payload, _OUTPUT_SCHEMA)
        assert any("hidden_field" in e for e in errors)

    def test_repair_clean_json(self):
        raw = json.dumps({
            "summary": "ok",
            "details": ["item"],
            "rule_refs": [],
            "passage_refs": [],
        })
        result = repair_llm_output(raw, _OUTPUT_SCHEMA)
        assert result["summary"] == "ok"

    def test_repair_json_with_preamble(self):
        payload = {"summary": "yes", "details": [], "rule_refs": [], "passage_refs": []}
        raw = f"Sure, here is the JSON:\n{json.dumps(payload)}"
        result = repair_llm_output(raw, _OUTPUT_SCHEMA)
        assert result["summary"] == "yes"

    def test_repair_markdown_fenced(self):
        payload = {"summary": "wrapped", "details": [], "rule_refs": [], "passage_refs": []}
        raw = f"```json\n{json.dumps(payload)}\n```"
        result = repair_llm_output(raw, _OUTPUT_SCHEMA)
        assert result["summary"] == "wrapped"


# ---------------------------------------------------------------------------
# Live LLM test — skipped unless Ollama is reachable
# ---------------------------------------------------------------------------

class TestLiveLocalLLM:
    @skip_no_llm
    def test_generate_returns_nonempty_string(self):
        client = LocalLLMClient(model_name=_DEFAULT_MODEL, base_url=_OLLAMA_URL)
        response = client.generate("Say 'hello' in one word.", temperature=0.0)
        assert isinstance(response, str)
        assert len(response) > 0

    @skip_no_llm
    def test_generate_structured_interpretation_parseable(self):
        from vedic_ai.llm import generate_structured_interpretation

        bundle = _minimal_bundle()
        prompt = build_interpretation_prompt(
            bundle=bundle,
            features={"sun_in_10th": True},
            triggers=[],
            passages=[],
            scope="career",
            output_schema=_OUTPUT_SCHEMA,
        )
        result = generate_structured_interpretation(
            prompt=prompt,
            model_name=_DEFAULT_MODEL,
            temperature=0.2,
            base_url=_OLLAMA_URL,
        )
        assert isinstance(result, dict)
