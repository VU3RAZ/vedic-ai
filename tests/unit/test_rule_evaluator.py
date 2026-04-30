"""Phase 4 tests: rule models, loader, and evaluator.

Unit tests use synthetic feature dicts and in-memory rule definitions so no
file I/O or live engine calls are needed.  Integration tests load the real
rule files and evaluate against the shared chart fixtures.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from vedic_ai.core.rule_evaluator import (
    _evaluate_condition,
    _resolve_path,
    evaluate_rules,
    resolve_rule_conflicts,
    score_rule_triggers,
)
from vedic_ai.core.rule_loader import _validate_feature_path, load_rule_set
from vedic_ai.core.rules import (
    ConflictPolicy,
    RuleCondition,
    RuleDefinition,
    RuleOperator,
)
from vedic_ai.core.exceptions import ConfigError, RuleError
from vedic_ai.domain.prediction import RuleTrigger
from vedic_ai.features.core_features import extract_core_features


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(
    rule_id: str = "TEST01",
    scope: str = "career",
    conditions: list[dict] | None = None,
    weight: float = 0.5,
    conflict_policy: str = "merge",
) -> RuleDefinition:
    if conditions is None:
        conditions = [{"feature": "planets.Sun.house", "op": "eq", "value": 10}]
    return RuleDefinition(
        rule_id=rule_id,
        name=f"Test rule {rule_id}",
        scope=scope,
        conditions=[RuleCondition(**c) for c in conditions],
        explanation_template="Test explanation.",
        weight=weight,
        conflict_policy=ConflictPolicy(conflict_policy),
    )


def _make_trigger(
    rule_id: str = "T01",
    scope: str = "career",
    weight: float = 0.6,
    conflict_policy: str = "merge",
) -> RuleTrigger:
    return RuleTrigger(
        rule_id=rule_id,
        rule_name="Test",
        scope=scope,
        weight=weight,
        explanation="explanation",
        conflict_policy=conflict_policy,
    )


# ---------------------------------------------------------------------------
# RuleDefinition model validation
# ---------------------------------------------------------------------------

class TestRuleDefinition:
    def test_valid_rule_parses(self) -> None:
        rule = _make_rule()
        assert rule.rule_id == "TEST01"
        assert rule.weight == 0.5
        assert rule.conflict_policy == ConflictPolicy.MERGE

    def test_blank_rule_id_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_rule(rule_id="   ")

    def test_weight_out_of_range_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_rule(weight=1.5)
        with pytest.raises(Exception):
            _make_rule(weight=-0.1)

    def test_empty_conditions_rejected(self) -> None:
        with pytest.raises(Exception):
            RuleDefinition(
                rule_id="X",
                name="X",
                scope="personality",
                conditions=[],
                explanation_template="x",
            )

    def test_unknown_operator_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_rule(conditions=[{"feature": "planets.Sun.house", "op": "between", "value": 5}])

    def test_default_conflict_policy_is_merge(self) -> None:
        rule = _make_rule()
        assert rule.conflict_policy == ConflictPolicy.MERGE

    def test_source_refs_default_empty(self) -> None:
        rule = _make_rule()
        assert rule.source_refs == []


# ---------------------------------------------------------------------------
# Feature path validator
# ---------------------------------------------------------------------------

class TestValidateFeaturePath:
    def test_valid_planet_path(self) -> None:
        _validate_feature_path("planets.Sun.house", "X")
        _validate_feature_path("planets.Saturn.in_kendra", "X")

    def test_valid_house_path(self) -> None:
        _validate_feature_path("houses.1.lord", "X")
        _validate_feature_path("houses.12.is_occupied", "X")

    def test_valid_top_level_paths(self) -> None:
        for top in ("yogas", "lagna", "aspects", "nakshatra_ascendant", "metadata"):
            _validate_feature_path(f"{top}.something", "X")

    def test_unknown_namespace_raises(self) -> None:
        with pytest.raises(RuleError, match="unknown feature namespace"):
            _validate_feature_path("invalid_top.Sun.house", "X")

    def test_unknown_graha_raises(self) -> None:
        with pytest.raises(RuleError, match="unknown graha"):
            _validate_feature_path("planets.Pluto.house", "X")

    def test_invalid_house_number_raises(self) -> None:
        with pytest.raises(RuleError, match="invalid house number"):
            _validate_feature_path("houses.13.lord", "X")
        with pytest.raises(RuleError, match="invalid house number"):
            _validate_feature_path("houses.0.lord", "X")

    def test_non_digit_house_segment_raises(self) -> None:
        with pytest.raises(RuleError, match="invalid house number"):
            _validate_feature_path("houses.seventh.lord", "X")

    def test_empty_path_raises(self) -> None:
        with pytest.raises(RuleError, match="empty"):
            _validate_feature_path("", "X")


# ---------------------------------------------------------------------------
# Rule loader
# ---------------------------------------------------------------------------

class TestLoadRuleSet:
    def test_loads_single_yaml_file(self, tmp_path: Path) -> None:
        f = tmp_path / "rules.yaml"
        f.write_text(textwrap.dedent("""\
            - rule_id: T001
              name: Test
              scope: career
              weight: 0.5
              conditions:
                - feature: planets.Sun.house
                  op: eq
                  value: 10
              explanation_template: "Sun in 10th."
        """))
        rules = load_rule_set(str(f))
        assert len(rules) == 1
        assert rules[0].rule_id == "T001"

    def test_loads_directory_of_yaml_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").write_text(textwrap.dedent("""\
            - rule_id: A01
              name: A
              scope: career
              weight: 0.4
              conditions:
                - feature: planets.Jupiter.house
                  op: eq
                  value: 10
              explanation_template: "Jupiter 10th."
        """))
        (tmp_path / "b.yaml").write_text(textwrap.dedent("""\
            - rule_id: B01
              name: B
              scope: personality
              weight: 0.6
              conditions:
                - feature: planets.Moon.house
                  op: eq
                  value: 1
              explanation_template: "Moon in 1st."
        """))
        rules = load_rule_set(str(tmp_path))
        assert len(rules) == 2
        assert {r.rule_id for r in rules} == {"A01", "B01"}

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        assert load_rule_set(str(tmp_path)) == []

    def test_nonexistent_path_raises_config_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError):
            load_rule_set(str(tmp_path / "missing.yaml"))

    def test_non_list_yaml_raises_config_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text("rule_id: X\nname: bad\n")
        with pytest.raises(ConfigError, match="must contain a YAML list"):
            load_rule_set(str(f))

    def test_duplicate_rule_ids_raises_rule_error(self, tmp_path: Path) -> None:
        f = tmp_path / "dup.yaml"
        f.write_text(textwrap.dedent("""\
            - rule_id: SAME
              name: First
              scope: career
              weight: 0.5
              conditions:
                - feature: planets.Sun.house
                  op: eq
                  value: 10
              explanation_template: "First."
            - rule_id: SAME
              name: Second
              scope: career
              weight: 0.5
              conditions:
                - feature: planets.Sun.house
                  op: eq
                  value: 10
              explanation_template: "Second."
        """))
        with pytest.raises(RuleError, match="Duplicate rule_id"):
            load_rule_set(str(f))

    def test_unknown_feature_namespace_raises_rule_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad_path.yaml"
        f.write_text(textwrap.dedent("""\
            - rule_id: BAD01
              name: Bad
              scope: career
              weight: 0.5
              conditions:
                - feature: unknown_namespace.Sun.house
                  op: eq
                  value: 10
              explanation_template: "Bad."
        """))
        with pytest.raises(RuleError, match="unknown feature namespace"):
            load_rule_set(str(f))

    def test_unknown_graha_in_path_raises_rule_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad_graha.yaml"
        f.write_text(textwrap.dedent("""\
            - rule_id: BAD02
              name: Bad
              scope: career
              weight: 0.5
              conditions:
                - feature: planets.Uranus.house
                  op: eq
                  value: 10
              explanation_template: "Bad."
        """))
        with pytest.raises(RuleError, match="unknown graha"):
            load_rule_set(str(f))

    def test_invalid_schema_raises_rule_error(self, tmp_path: Path) -> None:
        f = tmp_path / "schema_err.yaml"
        f.write_text(textwrap.dedent("""\
            - rule_id: SCHM
              name: Schm
              scope: career
              weight: 99.9
              conditions:
                - feature: planets.Sun.house
                  op: eq
                  value: 10
              explanation_template: "Weight out of range."
        """))
        with pytest.raises(RuleError):
            load_rule_set(str(f))


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------

class TestResolvePath:
    def test_simple_string_key(self) -> None:
        features = {"planets": {"Sun": {"house": 3}}}
        assert _resolve_path(features, "planets.Sun.house") == 3

    def test_integer_key_for_house(self) -> None:
        features = {"houses": {7: {"lord": "Venus"}}}
        assert _resolve_path(features, "houses.7.lord") == "Venus"

    def test_missing_top_key_raises(self) -> None:
        with pytest.raises(KeyError):
            _resolve_path({}, "planets.Sun.house")

    def test_missing_nested_key_raises(self) -> None:
        with pytest.raises(KeyError):
            _resolve_path({"planets": {"Sun": {}}}, "planets.Sun.house")

    def test_navigating_into_non_dict_raises(self) -> None:
        with pytest.raises(KeyError, match="Cannot navigate"):
            _resolve_path({"planets": {"Sun": {"house": 1}}}, "planets.Sun.house.extra")


# ---------------------------------------------------------------------------
# _evaluate_condition
# ---------------------------------------------------------------------------

class TestEvaluateCondition:
    _features = {"planets": {"Sun": {
        "house": 10,
        "is_exalted": True,
        "total_strength": 0.8,
        "rasi": "Aries",
        "aspects_to_houses": [4, 7, 10],
    }}}

    def test_eq_match(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.house", RuleOperator.EQ, 10)

    def test_eq_no_match(self) -> None:
        assert not _evaluate_condition(self._features, "planets.Sun.house", RuleOperator.EQ, 1)

    def test_ne_match(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.house", RuleOperator.NE, 1)

    def test_gt_match(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.total_strength", RuleOperator.GT, 0.5)

    def test_gt_no_match(self) -> None:
        assert not _evaluate_condition(self._features, "planets.Sun.total_strength", RuleOperator.GT, 0.9)

    def test_lt_match(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.total_strength", RuleOperator.LT, 0.9)

    def test_in_match(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.rasi", RuleOperator.IN, ["Aries", "Leo"])

    def test_in_no_match(self) -> None:
        assert not _evaluate_condition(self._features, "planets.Sun.rasi", RuleOperator.IN, ["Taurus"])

    def test_not_in_match(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.rasi", RuleOperator.NOT_IN, ["Taurus"])

    def test_contains_match(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.aspects_to_houses", RuleOperator.CONTAINS, 7)

    def test_contains_no_match(self) -> None:
        assert not _evaluate_condition(self._features, "planets.Sun.aspects_to_houses", RuleOperator.CONTAINS, 1)

    def test_boolean_eq_true(self) -> None:
        assert _evaluate_condition(self._features, "planets.Sun.is_exalted", RuleOperator.EQ, True)

    def test_boolean_eq_false(self) -> None:
        assert not _evaluate_condition(self._features, "planets.Sun.is_exalted", RuleOperator.EQ, False)

    def test_missing_feature_path_returns_false(self) -> None:
        assert not _evaluate_condition(self._features, "planets.Mars.house", RuleOperator.EQ, 10)

    def test_missing_nested_path_returns_false(self) -> None:
        assert not _evaluate_condition(self._features, "yogas.kemadruma", RuleOperator.EQ, True)


# ---------------------------------------------------------------------------
# evaluate_rules
# ---------------------------------------------------------------------------

class TestEvaluateRules:
    _features = {
        "planets": {
            "Sun": {"house": 10, "is_exalted": False},
            "Moon": {"house": 4, "is_exalted": False},
        },
        "houses": {
            10: {"is_occupied": True, "lord_in_kendra": True, "lord_dignity": "exalted"},
        },
        "yogas": {"kemadruma": False, "gajakesari": True},
        "lagna": {"lord_house": 10},
    }

    def test_single_rule_match_produces_trigger(self) -> None:
        rules = [_make_rule(conditions=[{"feature": "planets.Sun.house", "op": "eq", "value": 10}])]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert len(triggers) == 1
        assert triggers[0].rule_id == "TEST01"

    def test_single_rule_no_match_empty_result(self) -> None:
        rules = [_make_rule(conditions=[{"feature": "planets.Sun.house", "op": "eq", "value": 1}])]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert triggers == []

    def test_multi_condition_all_match(self) -> None:
        rules = [_make_rule(conditions=[
            {"feature": "planets.Sun.house", "op": "eq", "value": 10},
            {"feature": "houses.10.is_occupied", "op": "eq", "value": True},
        ])]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert len(triggers) == 1

    def test_multi_condition_partial_match_no_trigger(self) -> None:
        rules = [_make_rule(conditions=[
            {"feature": "planets.Sun.house", "op": "eq", "value": 10},
            {"feature": "planets.Sun.is_exalted", "op": "eq", "value": True},
        ])]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert triggers == []

    def test_trigger_carries_evidence(self) -> None:
        rules = [_make_rule(conditions=[{"feature": "planets.Sun.house", "op": "eq", "value": 10}])]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert triggers[0].evidence == {"planets.Sun.house": 10}

    def test_trigger_scope_and_weight_match_rule(self) -> None:
        rules = [_make_rule(scope="career", weight=0.7)]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert triggers[0].scope == "career"
        assert triggers[0].weight == 0.7

    def test_missing_feature_path_does_not_trigger(self) -> None:
        rules = [_make_rule(conditions=[{"feature": "planets.Rahu.house", "op": "eq", "value": 1}])]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert triggers == []

    def test_multiple_rules_evaluated_independently(self) -> None:
        rules = [
            _make_rule("R1", conditions=[{"feature": "planets.Sun.house", "op": "eq", "value": 10}]),
            _make_rule("R2", conditions=[{"feature": "planets.Moon.house", "op": "eq", "value": 1}]),
            _make_rule("R3", conditions=[{"feature": "yogas.gajakesari", "op": "eq", "value": True}]),
        ]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        ids = {t.rule_id for t in triggers}
        assert ids == {"R1", "R3"}

    def test_trigger_conflict_policy_propagated(self) -> None:
        rules = [_make_rule(conflict_policy="override")]
        triggers = evaluate_rules(None, self._features, rules)  # type: ignore[arg-type]
        assert triggers[0].conflict_policy == "override"


# ---------------------------------------------------------------------------
# score_rule_triggers
# ---------------------------------------------------------------------------

class TestScoreRuleTriggers:
    def test_single_scope_score_equals_weight(self) -> None:
        triggers = [_make_trigger("T1", "career", 0.8)]
        scores = score_rule_triggers(triggers)
        assert scores == {"career": 0.8}

    def test_multiple_triggers_same_scope_is_mean(self) -> None:
        triggers = [
            _make_trigger("T1", "career", 0.8),
            _make_trigger("T2", "career", 0.4),
        ]
        scores = score_rule_triggers(triggers)
        assert scores["career"] == pytest.approx(0.6, abs=1e-4)

    def test_multiple_scopes_scored_independently(self) -> None:
        triggers = [
            _make_trigger("T1", "career", 0.8),
            _make_trigger("T2", "personality", 0.6),
        ]
        scores = score_rule_triggers(triggers)
        assert "career" in scores
        assert "personality" in scores
        assert scores["career"] == pytest.approx(0.8)
        assert scores["personality"] == pytest.approx(0.6)

    def test_empty_triggers_returns_empty_dict(self) -> None:
        assert score_rule_triggers([]) == {}

    def test_score_bounded_by_weights(self) -> None:
        triggers = [_make_trigger("T1", "career", 1.0), _make_trigger("T2", "career", 1.0)]
        scores = score_rule_triggers(triggers)
        assert scores["career"] <= 1.0


# ---------------------------------------------------------------------------
# resolve_rule_conflicts
# ---------------------------------------------------------------------------

class TestResolveRuleConflicts:
    def test_all_merge_policies_kept(self) -> None:
        triggers = [_make_trigger("T1", "career", conflict_policy="merge"),
                    _make_trigger("T2", "career", conflict_policy="merge")]
        result = resolve_rule_conflicts(triggers)
        assert len(result) == 2

    def test_defer_dropped_when_override_in_same_scope(self) -> None:
        triggers = [
            _make_trigger("T1", "career", conflict_policy="override"),
            _make_trigger("T2", "career", conflict_policy="defer"),
        ]
        result = resolve_rule_conflicts(triggers)
        assert len(result) == 1
        assert result[0].rule_id == "T1"

    def test_defer_kept_when_no_override_in_scope(self) -> None:
        triggers = [
            _make_trigger("T1", "career", conflict_policy="merge"),
            _make_trigger("T2", "career", conflict_policy="defer"),
        ]
        result = resolve_rule_conflicts(triggers)
        assert len(result) == 2

    def test_defer_in_different_scope_not_affected_by_override(self) -> None:
        triggers = [
            _make_trigger("T1", "career", conflict_policy="override"),
            _make_trigger("T2", "personality", conflict_policy="defer"),
        ]
        result = resolve_rule_conflicts(triggers)
        assert len(result) == 2
        assert {t.rule_id for t in result} == {"T1", "T2"}

    def test_multiple_overrides_all_kept(self) -> None:
        triggers = [
            _make_trigger("T1", "career", conflict_policy="override"),
            _make_trigger("T2", "career", conflict_policy="override"),
            _make_trigger("T3", "career", conflict_policy="defer"),
        ]
        result = resolve_rule_conflicts(triggers)
        assert len(result) == 2
        assert all(t.conflict_policy == "override" for t in result)

    def test_empty_triggers_returns_empty(self) -> None:
        assert resolve_rule_conflicts([]) == []

    def test_order_preserved(self) -> None:
        triggers = [
            _make_trigger("T1", "career", conflict_policy="merge"),
            _make_trigger("T2", "career", conflict_policy="override"),
            _make_trigger("T3", "career", conflict_policy="merge"),
        ]
        result = resolve_rule_conflicts(triggers)
        assert [t.rule_id for t in result] == ["T1", "T2", "T3"]


# ---------------------------------------------------------------------------
# Integration: load real rules and evaluate against fixture charts
# ---------------------------------------------------------------------------

RULES_DIR = Path(__file__).parent.parent.parent / "data" / "corpus" / "rules"


class TestRuleIntegration:
    def test_loads_all_rule_files(self) -> None:
        rules = load_rule_set(str(RULES_DIR))
        assert len(rules) >= 20, f"Expected ≥20 rules, got {len(rules)}"

    def test_no_duplicate_rule_ids(self) -> None:
        rules = load_rule_set(str(RULES_DIR))
        ids = [r.rule_id for r in rules]
        assert len(ids) == len(set(ids))

    def test_all_scopes_covered(self) -> None:
        rules = load_rule_set(str(RULES_DIR))
        scopes = {r.scope for r in rules}
        assert "personality" in scopes
        assert "career" in scopes
        assert "relationships" in scopes

    def test_chart_a_fires_expected_rules(self, chart_a) -> None:
        """Chart A: Aries lagna, exalted Sun in H1, Mars/Saturn in H10."""
        rules = load_rule_set(str(RULES_DIR))
        features = extract_core_features(chart_a)
        triggers = evaluate_rules(chart_a, features, rules)
        fired = {t.rule_id for t in triggers}

        assert "P001" in fired, "Sun in Lagna should fire"
        assert "P008" in fired, "Exalted Sun should fire"
        assert "C002" in fired, "Saturn in 10th should fire"
        assert "C006" in fired, "Mars in 10th should fire"
        assert "C007" in fired, "10th house occupied should fire"
        assert "C008" in fired, "Lagna lord (Mars) in 10th should fire"

    def test_chart_b_fires_expected_rules(self, chart_b) -> None:
        """Chart B: Cancer lagna, Kemadruma yoga, Saturn in H7."""
        rules = load_rule_set(str(RULES_DIR))
        features = extract_core_features(chart_b)
        triggers = evaluate_rules(chart_b, features, rules)
        fired = {t.rule_id for t in triggers}

        assert "P002" in fired, "Moon in Lagna should fire"
        assert "P005" in fired, "Lagna lord (Moon) in own sign should fire"
        assert "P006" in fired, "Kemadruma yoga should fire"
        assert "C001" in fired, "Sun in 10th should fire"
        assert "R003" in fired, "Saturn in 7th should fire"
        assert "R007" in fired, "7th house occupied should fire"

    def test_chart_b_conflict_resolution_drops_defer(self, chart_b) -> None:
        """P011 (defer) should be suppressed by P005 (override) in personality scope."""
        rules = load_rule_set(str(RULES_DIR))
        features = extract_core_features(chart_b)
        triggers = evaluate_rules(chart_b, features, rules)
        resolved = resolve_rule_conflicts(triggers)
        resolved_ids = {t.rule_id for t in resolved}
        fired_ids = {t.rule_id for t in triggers}

        # P011 fires (Saturn in H7 aspects H1) but should be dropped after resolution
        if "P011" in fired_ids:
            assert "P011" not in resolved_ids, "P011 (defer) should be dropped by P005 (override)"

    def test_chart_c_fires_gajakesari(self, chart_c) -> None:
        """Chart C: Libra lagna, Jupiter in H8, Moon in H2 — Gajakesari active."""
        rules = load_rule_set(str(RULES_DIR))
        features = extract_core_features(chart_c)
        triggers = evaluate_rules(chart_c, features, rules)
        fired = {t.rule_id for t in triggers}

        assert "P007" in fired, "Gajakesari yoga should fire for Chart C"

    def test_scores_returned_per_scope(self, chart_a) -> None:
        rules = load_rule_set(str(RULES_DIR))
        features = extract_core_features(chart_a)
        triggers = evaluate_rules(chart_a, features, rules)
        scores = score_rule_triggers(triggers)

        assert isinstance(scores, dict)
        for scope, score in scores.items():
            assert 0.0 <= score <= 1.0, f"Score for {scope} out of range: {score}"

    def test_all_triggers_have_evidence(self, chart_a) -> None:
        rules = load_rule_set(str(RULES_DIR))
        features = extract_core_features(chart_a)
        triggers = evaluate_rules(chart_a, features, rules)

        for t in triggers:
            assert t.evidence, f"Trigger {t.rule_id} has empty evidence"
