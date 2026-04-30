"""Assemble evidence and generate PredictionSection from LLM interpretation."""

from __future__ import annotations

from vedic_ai.domain.chart import ChartBundle
from vedic_ai.domain.corpus import RetrievedPassage
from vedic_ai.domain.prediction import (
    PredictionEvidence,
    PredictionSection,
    RuleTrigger,
)


def build_prediction_evidence(
    bundle: ChartBundle,
    features: dict,
    triggers: list[RuleTrigger],
    passages: list[RetrievedPassage],
) -> list[PredictionEvidence]:
    """Assemble evidence references for the final report.

    Each rule trigger and each retrieved passage becomes one PredictionEvidence
    entry.  Chart facts (planet sign + house) are captured on every entry so
    downstream renderers can trace every claim back to the raw chart data.
    """
    chart_facts = [
        f"{name}: sign={p.rasi.rasi.value}, house={p.house}"
        for name, p in sorted(bundle.d1.planets.items())
    ]

    evidence: list[PredictionEvidence] = []

    for trigger in triggers:
        evidence.append(
            PredictionEvidence(
                trigger=trigger,
                chart_facts=chart_facts,
            )
        )

    for passage in passages:
        evidence.append(
            PredictionEvidence(
                passage=passage.text,
                source=passage.source,
                chart_facts=chart_facts,
            )
        )

    return evidence


def generate_scope_report(
    scope: str,
    interpretation: dict,
    evidence: list[PredictionEvidence],
) -> PredictionSection:
    """Create a PredictionSection from a parsed LLM interpretation dict.

    Expects interpretation to carry at minimum a 'summary' key (str) and
    optionally 'details' (list[str]).  Missing keys fall back to empty defaults.
    """
    summary = interpretation.get("summary", "")
    if not isinstance(summary, str):
        summary = str(summary)

    raw_details = interpretation.get("details", [])
    if isinstance(raw_details, list):
        details = [str(d) for d in raw_details]
    else:
        details = [str(raw_details)]

    return PredictionSection(
        scope=scope,
        summary=summary,
        details=details,
        evidence=evidence,
    )
