"""Rule evaluator: match rules against extracted features and produce triggers."""

from __future__ import annotations

from typing import Any

from vedic_ai.core.rules import RuleDefinition, RuleOperator
from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.prediction import RuleTrigger


def _resolve_path(features: dict, path: str) -> Any:
    """Navigate a dot-notation path into the feature dict.

    House-number path segments (e.g. "7") are converted to int to match the
    integer-keyed houses sub-dict.

    Raises KeyError when any segment is missing.
    """
    current: Any = features
    for part in path.split("."):
        if not isinstance(current, dict):
            raise KeyError(f"Cannot navigate into {type(current).__name__} at '{part}'")
        key: Any = int(part) if part.isdigit() else part
        current = current[key]
    return current


def _evaluate_condition(features: dict, feature_path: str, op: RuleOperator, value: Any) -> bool:
    """Return True when the resolved feature satisfies the operator/value pair."""
    try:
        actual = _resolve_path(features, feature_path)
    except (KeyError, TypeError):
        return False

    match op:
        case RuleOperator.EQ:
            return actual == value
        case RuleOperator.NE:
            return actual != value
        case RuleOperator.GT:
            return actual > value
        case RuleOperator.LT:
            return actual < value
        case RuleOperator.IN:
            return actual in value
        case RuleOperator.NOT_IN:
            return actual not in value
        case RuleOperator.CONTAINS:
            return value in actual
    return False  # pragma: no cover


def evaluate_rules(
    bundle: ChartBundle,
    features: dict,
    rule_set: list[RuleDefinition],
) -> list[RuleTrigger]:
    """Return all matched rule triggers with their chart evidence payloads.

    Each trigger captures the feature values that satisfied the rule's conditions
    so downstream prompting and evidence layers can trace every claim.
    """
    triggers: list[RuleTrigger] = []

    for rule in rule_set:
        matched_evidence: dict[str, Any] = {}
        all_matched = True

        for cond in rule.conditions:
            try:
                actual = _resolve_path(features, cond.feature)
            except (KeyError, TypeError):
                all_matched = False
                break

            if not _evaluate_condition(features, cond.feature, cond.op, cond.value):
                all_matched = False
                break

            matched_evidence[cond.feature] = actual

        if all_matched:
            triggers.append(RuleTrigger(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                scope=rule.scope,
                weight=rule.weight,
                evidence=matched_evidence,
                explanation=rule.explanation_template,
                source_refs=list(rule.source_refs),
                conflict_policy=rule.conflict_policy.value,
            ))

    return triggers


def score_rule_triggers(triggers: list[RuleTrigger]) -> dict[str, float]:
    """Aggregate trigger weights into a per-scope score.

    Returns the mean weight across all triggered rules for each scope,
    naturally bounded in [0.0, 1.0].  Scopes with no triggers are omitted.
    """
    scope_weights: dict[str, list[float]] = {}
    for t in triggers:
        scope_weights.setdefault(t.scope, []).append(t.weight)

    return {
        scope: round(sum(weights) / len(weights), 4)
        for scope, weights in scope_weights.items()
    }


def resolve_rule_conflicts(triggers: list[RuleTrigger]) -> list[RuleTrigger]:
    """Apply conflict-resolution policy per scope.

    Rules:
    - ``merge``   — always kept.
    - ``override``— always kept; suppresses ``defer`` triggers in the same scope.
    - ``defer``   — dropped when any ``override`` trigger exists in the same scope.

    Ordering of surviving triggers is preserved.
    """
    scopes_with_override: frozenset[str] = frozenset(
        t.scope for t in triggers if t.conflict_policy == "override"
    )
    return [
        t for t in triggers
        if t.conflict_policy != "defer" or t.scope not in scopes_with_override
    ]
