"""Timing service: evaluate time-dependent rules and generate forecast windows."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from vedic_ai.core.rule_evaluator import evaluate_rules, resolve_rule_conflicts
from vedic_ai.core.rule_loader import load_rule_set
from vedic_ai.core.rules import RuleDefinition
from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.prediction import (
    ForecastReport,
    ForecastWindow,
    PredictionEvidence,
    RuleTrigger,
)
from vedic_ai.engines.base import compute_core_chart
from vedic_ai.features.core_features import extract_core_features
from vedic_ai.features.dasha_features import compute_timing_features
from vedic_ai.features.transit_features import compute_transit_features

logger = logging.getLogger(__name__)

_TIMING_RULES_PATH = Path(__file__).parents[3] / "data" / "corpus" / "rules" / "timing.yaml"


def _load_timing_rules(rules_path: Path | None = None) -> list[RuleDefinition]:
    path = rules_path or _TIMING_RULES_PATH
    if not path.exists():
        logger.warning("Timing rules file not found: %s", path)
        return []
    return load_rule_set(str(path))


def evaluate_timing_rules(
    bundle: ChartBundle,
    features: dict,
    timing_features: dict,
    rule_set: list[RuleDefinition],
) -> list[RuleTrigger]:
    """Evaluate time-dependent rules against merged natal + timing features.

    Merges natal features and timing_features, then evaluates all rules
    whose scope is 'timing'.
    """
    merged = {**features, **timing_features}
    raw_triggers = evaluate_rules(bundle, merged, rule_set)
    timing_triggers = [t for t in raw_triggers if t.scope == "timing"]
    return resolve_rule_conflicts(timing_triggers)


def generate_forecast_window(
    birth: BirthData,
    start: datetime,
    end: datetime,
    scopes: list[str],
    *,
    engine=None,
    rules_path: Path | None = None,
    step_days: int = 30,
) -> ForecastReport:
    """Generate forecast windows for a date range, stepping by step_days.

    For each step within [start, end], computes timing features and evaluates
    timing rules. One ForecastWindow is emitted per (step, scope) combination.

    Args:
        birth: Birth data for the native.
        start: Forecast start datetime (timezone-aware).
        end: Forecast end datetime (timezone-aware).
        scopes: Prediction scopes to include in each window.
        engine: AstrologyEngine; defaults to SwissEphAdapter.
        rules_path: Override path for timing.yaml.
        step_days: Interval between forecast windows in days.
    """
    if engine is None:
        from vedic_ai.engines.swisseph_adapter import SwissEphAdapter
        engine = SwissEphAdapter()

    bundle = compute_core_chart(birth, engine)
    natal_features = extract_core_features(bundle)
    timing_rules = _load_timing_rules(rules_path)

    windows: list[ForecastWindow] = []
    current = start

    while current <= end:
        timing_feats = compute_timing_features(bundle, current)

        try:
            transit_snapshot = engine.compute_transits(birth, current)
            transit_feats = compute_transit_features(bundle, transit_snapshot)
        except Exception:
            transit_feats = {}

        merged = {**natal_features, **timing_feats, **transit_feats}
        triggers = evaluate_timing_rules(bundle, natal_features, {**timing_feats, **transit_feats}, timing_rules)

        maha_lord = timing_feats.get("timing", {}).get("mahadasha", {}).get("lord")
        antar_lord = timing_feats.get("timing", {}).get("antardasha", {}).get("lord")
        evidence = [
            PredictionEvidence(
                trigger=t,
                chart_facts=[
                    f"Mahadasha: {maha_lord}",
                    f"Antardasha: {antar_lord}",
                ],
            )
            for t in triggers
        ]

        for scope in scopes:
            scope_triggers = [t for t in triggers if t.scope in ("timing", scope)]
            summary = (
                scope_triggers[0].explanation
                if scope_triggers
                else f"No significant timing patterns for {scope} in this period."
            )
            windows.append(
                ForecastWindow(
                    start_date=current.date(),
                    end_date=(current + timedelta(days=step_days - 1)).date(),
                    mahadasha_lord=maha_lord,
                    antardasha_lord=antar_lord,
                    scope=scope,
                    summary=summary,
                    details=[t.explanation for t in scope_triggers],
                    evidence=evidence,
                )
            )

        current += timedelta(days=step_days)

    return ForecastReport(
        birth_name=birth.name,
        generated_at=datetime.now(timezone.utc),
        scopes=scopes,
        windows=windows,
    )
