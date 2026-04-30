"""Unit tests for llm/prompt_builder.py and llm/output_parser.py."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.domain.chart import ChartBundle, DivisionalChart
from vedic_ai.domain.corpus import RetrievedPassage
from vedic_ai.domain.enums import Dignity, Graha, NakshatraName, Rasi
from vedic_ai.domain.house import HousePlacement
from vedic_ai.domain.planet import NakshatraPlacement, PlanetPlacement, RasiPlacement
from vedic_ai.domain.prediction import RuleTrigger
from vedic_ai.llm.output_parser import repair_llm_output, validate_llm_output
from vedic_ai.llm.prompt_builder import (
    _SECTION_CHART_FACTS,
    _SECTION_DERIVED,
    _SECTION_PASSAGES,
    _SECTION_RULES,
    _SECTION_TASK,
    build_interpretation_prompt,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_planet(
    graha: Graha,
    longitude: float,
    rasi: Rasi,
    nakshatra: NakshatraName,
    house: int,
    dignity: Dignity | None = None,
    is_retrograde: bool = False,
) -> PlanetPlacement:
    degree_in_rasi = longitude % 30
    degree_in_nak = longitude % 13.334
    return PlanetPlacement(
        graha=graha,
        longitude=longitude,
        rasi=RasiPlacement(rasi=rasi, degree_in_rasi=degree_in_rasi),
        nakshatra=NakshatraPlacement(
            nakshatra=nakshatra,
            pada=1,
            nakshatra_lord=Graha.SUN,
            degree_in_nakshatra=degree_in_nak,
        ),
        house=house,
        dignity=dignity,
        is_retrograde=is_retrograde,
    )


def _make_rahu(longitude: float, rasi: Rasi, house: int) -> PlanetPlacement:
    degree_in_rasi = longitude % 30
    degree_in_nak = longitude % 13.334
    return PlanetPlacement(
        graha=Graha.RAHU,
        longitude=longitude,
        rasi=RasiPlacement(rasi=rasi, degree_in_rasi=degree_in_rasi),
        nakshatra=NakshatraPlacement(
            nakshatra=NakshatraName.ASHWINI,
            pada=2,
            nakshatra_lord=Graha.SUN,
            degree_in_nakshatra=degree_in_nak,
        ),
        house=house,
        is_retrograde=True,
    )


@pytest.fixture()
def chart_bundle() -> ChartBundle:
    birth = BirthData(
        birth_datetime=datetime(1985, 6, 15, 6, 30, tzinfo=timezone.utc),
        location=GeoLocation(latitude=28.6, longitude=77.2, place_name="Delhi"),
        name="Test Native",
    )
    sun = _make_planet(Graha.SUN, 62.5, Rasi.GEMINI, NakshatraName.MRIGASHIRSHA, 10)
    moon = _make_planet(Graha.MOON, 120.0, Rasi.LEO, NakshatraName.MAGHA, 2)
    jupiter = _make_planet(Graha.JUPITER, 195.0, Rasi.LIBRA, NakshatraName.SWATI, 3)
    saturn = _make_planet(
        Graha.SATURN, 240.0, Rasi.SAGITTARIUS, NakshatraName.MULA, 4,
        dignity=Dignity.ENEMY
    )
    rahu = _make_rahu(315.0, Rasi.AQUARIUS, 6)

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
        planets={
            Graha.SUN.value: sun,
            Graha.MOON.value: moon,
            Graha.JUPITER.value: jupiter,
            Graha.SATURN.value: saturn,
            Graha.RAHU.value: rahu,
        },
        houses=houses,
    )
    return ChartBundle(birth=birth, engine="test", ayanamsa="lahiri", d1=d1)


@pytest.fixture()
def triggers() -> list[RuleTrigger]:
    return [
        RuleTrigger(
            rule_id="C001",
            rule_name="Sun in 10th house",
            scope="career",
            weight=0.8,
            explanation="Sun occupies the 10th house, conferring prominence.",
        ),
        RuleTrigger(
            rule_id="P001",
            rule_name="Moon in Lagna",
            scope="personality",
            weight=0.6,
            explanation="Moon in the Lagna gives emotional sensitivity.",
        ),
    ]


@pytest.fixture()
def passages() -> list[RetrievedPassage]:
    return [
        RetrievedPassage(
            chunk_id="bphs_024_0001",
            text="The Sun in the tenth house confers prominence and authority.",
            source="BPHS",
            score=0.92,
            metadata={"chapter": 24},
        ),
        RetrievedPassage(
            chunk_id="bphs_015_0000",
            text="Moon in Lagna gives emotional depth.",
            source="BPHS",
            score=0.85,
            metadata={"chapter": 15},
        ),
    ]


@pytest.fixture()
def output_schema() -> dict:
    return {
        "summary": "str",
        "details": "list",
        "rule_refs": "list",
        "passage_refs": "list",
    }


@pytest.fixture()
def prompt(chart_bundle, triggers, passages, output_schema) -> str:
    return build_interpretation_prompt(
        bundle=chart_bundle,
        features={"sun_in_10th": True, "moon_lagna": False},
        triggers=triggers,
        passages=passages,
        scope="career",
        output_schema=output_schema,
    )


# ---------------------------------------------------------------------------
# TestPromptSectionOrdering
# ---------------------------------------------------------------------------

class TestPromptSectionOrdering:
    def test_contains_all_five_sections(self, prompt):
        for section in [
            _SECTION_CHART_FACTS,
            _SECTION_DERIVED,
            _SECTION_RULES,
            _SECTION_PASSAGES,
            _SECTION_TASK,
        ]:
            assert section in prompt

    def test_chart_facts_before_derived(self, prompt):
        assert prompt.index(_SECTION_CHART_FACTS) < prompt.index(_SECTION_DERIVED)

    def test_derived_before_rules(self, prompt):
        assert prompt.index(_SECTION_DERIVED) < prompt.index(_SECTION_RULES)

    def test_rules_before_passages(self, prompt):
        assert prompt.index(_SECTION_RULES) < prompt.index(_SECTION_PASSAGES)

    def test_passages_before_task(self, prompt):
        assert prompt.index(_SECTION_PASSAGES) < prompt.index(_SECTION_TASK)

    def test_instruction_at_start(self, prompt):
        assert prompt.startswith("You are a Vedic astrology analyst.")


# ---------------------------------------------------------------------------
# TestPromptContent
# ---------------------------------------------------------------------------

class TestPromptContent:
    def test_ascendant_longitude_in_prompt(self, prompt):
        assert "10.5000" in prompt

    def test_sun_in_prompt(self, prompt):
        assert "Sun:" in prompt

    def test_planet_sorted_alphabetically(self, prompt):
        # Jupiter comes before Moon, Moon before Rahu, etc.
        idx_j = prompt.index("Jupiter:")
        idx_m = prompt.index("Moon:")
        assert idx_j < idx_m

    def test_features_serialised_as_json(self, prompt):
        # Derived features section contains JSON
        assert '"sun_in_10th"' in prompt

    def test_features_keys_sorted(self, prompt):
        # sort_keys=True — "moon_lagna" before "sun_in_10th" alphabetically
        idx_moon = prompt.index('"moon_lagna"')
        idx_sun = prompt.index('"sun_in_10th"')
        assert idx_moon < idx_sun

    def test_rule_id_present(self, prompt):
        assert "[C001]" in prompt and "[P001]" in prompt

    def test_rules_sorted_by_id(self, prompt):
        assert prompt.index("[C001]") < prompt.index("[P001]")

    def test_passage_chunk_id_present(self, prompt):
        assert "bphs_024_0001" in prompt and "bphs_015_0000" in prompt

    def test_passages_sorted_by_chunk_id(self, prompt):
        # bphs_015_0000 < bphs_024_0001 lexicographically
        assert prompt.index("bphs_015_0000") < prompt.index("bphs_024_0001")

    def test_scope_in_task_section(self, prompt):
        task_start = prompt.index(_SECTION_TASK)
        assert "career" in prompt[task_start:]

    def test_output_schema_in_task_section(self, prompt):
        task_start = prompt.index(_SECTION_TASK)
        assert '"summary"' in prompt[task_start:]

    def test_none_rules_shows_none_marker(self, chart_bundle, passages, output_schema):
        p = build_interpretation_prompt(
            bundle=chart_bundle,
            features={},
            triggers=[],
            passages=passages,
            scope="career",
            output_schema=output_schema,
        )
        rules_start = p.index(_SECTION_RULES)
        task_start = p.index(_SECTION_TASK)
        rules_block = p[rules_start:task_start]
        assert "(none)" in rules_block

    def test_none_passages_shows_none_marker(self, chart_bundle, triggers, output_schema):
        p = build_interpretation_prompt(
            bundle=chart_bundle,
            features={},
            triggers=triggers,
            passages=[],
            scope="career",
            output_schema=output_schema,
        )
        passages_start = p.index(_SECTION_PASSAGES)
        task_start = p.index(_SECTION_TASK)
        passages_block = p[passages_start:task_start]
        assert "(none)" in passages_block


# ---------------------------------------------------------------------------
# TestPromptDeterminism
# ---------------------------------------------------------------------------

class TestPromptDeterminism:
    def test_same_inputs_produce_identical_prompt(self, chart_bundle, triggers, passages, output_schema):
        p1 = build_interpretation_prompt(chart_bundle, {"a": 1}, triggers, passages, "career", output_schema)
        p2 = build_interpretation_prompt(chart_bundle, {"a": 1}, triggers, passages, "career", output_schema)
        assert p1 == p2

    def test_different_features_produce_different_prompt(self, chart_bundle, triggers, passages, output_schema):
        p1 = build_interpretation_prompt(chart_bundle, {"a": 1}, triggers, passages, "career", output_schema)
        p2 = build_interpretation_prompt(chart_bundle, {"a": 2}, triggers, passages, "career", output_schema)
        assert p1 != p2

    def test_different_scope_produces_different_prompt(self, chart_bundle, triggers, passages, output_schema):
        p1 = build_interpretation_prompt(chart_bundle, {}, triggers, passages, "career", output_schema)
        p2 = build_interpretation_prompt(chart_bundle, {}, triggers, passages, "relationships", output_schema)
        assert p1 != p2


# ---------------------------------------------------------------------------
# TestValidateLLMOutput
# ---------------------------------------------------------------------------

class TestValidateLLMOutput:
    def test_valid_payload_no_errors(self):
        schema = {"summary": "str", "details": "list"}
        payload = {"summary": "Some text", "details": ["item1"]}
        assert validate_llm_output(payload, schema) == []

    def test_missing_key_flagged(self):
        schema = {"summary": "str", "details": "list"}
        payload = {"summary": "text"}
        errors = validate_llm_output(payload, schema)
        assert any("Missing" in e and "details" in e for e in errors)

    def test_wrong_type_flagged(self):
        schema = {"summary": "str"}
        payload = {"summary": 42}
        errors = validate_llm_output(payload, schema)
        assert any("summary" in e and "str" in e for e in errors)

    def test_unsupported_key_flagged(self):
        schema = {"summary": "str"}
        payload = {"summary": "ok", "extra_key": "bad"}
        errors = validate_llm_output(payload, schema)
        assert any("extra_key" in e for e in errors)

    def test_empty_schema_passes_anything(self):
        assert validate_llm_output({"whatever": 123}, {}) == []

    def test_multiple_errors_reported(self):
        schema = {"summary": "str", "count": "int"}
        payload = {"summary": 99, "count": "wrong", "extra": True}
        errors = validate_llm_output(payload, schema)
        assert len(errors) >= 3

    def test_correct_types_all_pass(self):
        schema = {"s": "str", "i": "int", "f": "float", "l": "list", "d": "dict", "b": "bool"}
        payload = {"s": "x", "i": 1, "f": 1.0, "l": [], "d": {}, "b": True}
        assert validate_llm_output(payload, schema) == []


# ---------------------------------------------------------------------------
# TestRepairLLMOutput
# ---------------------------------------------------------------------------

class TestRepairLLMOutput:
    def test_clean_json_returned_directly(self):
        raw = '{"summary": "text", "details": []}'
        result = repair_llm_output(raw, schema={})
        assert result["summary"] == "text"

    def test_json_with_leading_text(self):
        raw = 'Here is your answer:\n{"summary": "ok"}'
        result = repair_llm_output(raw, schema={})
        assert result["summary"] == "ok"

    def test_markdown_fenced_json(self):
        raw = "```json\n{\"summary\": \"wrapped\"}\n```"
        result = repair_llm_output(raw, schema={})
        assert result["summary"] == "wrapped"

    def test_markdown_fence_no_language(self):
        raw = "```\n{\"key\": \"value\"}\n```"
        result = repair_llm_output(raw, schema={})
        assert result["key"] == "value"

    def test_trailing_text_after_json(self):
        raw = '{"score": 0.9} Some extra text at the end.'
        result = repair_llm_output(raw, schema={})
        assert result["score"] == pytest.approx(0.9)

    def test_irreparable_text_raises_value_error(self):
        with pytest.raises(ValueError, match="Cannot repair"):
            repair_llm_output("This is not JSON at all.", schema={})

    def test_nested_json_preserved(self):
        raw = '{"outer": {"inner": [1, 2, 3]}}'
        result = repair_llm_output(raw, schema={})
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            repair_llm_output("", schema={})
