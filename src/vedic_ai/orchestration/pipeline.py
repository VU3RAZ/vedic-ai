"""End-to-end prediction pipeline: birth data → PredictionReport."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.prediction import PredictionReport
from vedic_ai.engines.kerykeion_adapter import KerykeionAdapter
from vedic_ai.engines.base import AstrologyEngine, compute_core_chart
from vedic_ai.features.core_features import extract_core_features
from vedic_ai.orchestration.evidence_builder import (
    build_prediction_evidence,
    generate_scope_report,
)
from vedic_ai.orchestration.prediction_service import (
    call_llm_for_interpretation,
    evaluate_scope_rules,
)

logger = logging.getLogger(__name__)

_ARTIFACTS_DIR = Path("data/processed/artifacts")


def _persist_artifact(name: str, payload: dict, artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / name
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.debug("Artifact saved: %s", path)


def run_prediction_pipeline(
    birth: BirthData,
    scope: str,
    *,
    engine: AstrologyEngine | None = None,
    retriever: Any | None = None,
    llm_client: Any | None = None,
    at_time: datetime | None = None,
    top_k: int = 5,
    dry_run: bool = False,
    artifacts_dir: Path | None = None,
    rules_dir: Path | None = None,
) -> PredictionReport:
    """Execute the full chart-to-report workflow.

    Parameters
    ----------
    birth:
        Birth data for the native.
    scope:
        Prediction domain: 'personality', 'career', or 'relationships'.
    engine:
        Pre-instantiated AstrologyEngine; defaults to KerykeionAdapter.
    retriever:
        Pre-built Retriever; when None, retrieval is skipped (passages=[]).
    llm_client:
        Object implementing generate(prompt) -> str; when None or dry_run=True,
        a synthetic fallback interpretation is used instead.
    at_time:
        Optional reference time for transit overlays (not used in Phase 7).
    top_k:
        Number of passages to retrieve (if retriever provided).
    dry_run:
        Skip the LLM call and return evidence-only report.
    artifacts_dir:
        Directory for debugging artifacts; defaults to data/processed/artifacts.
    rules_dir:
        Override the rules YAML directory (used in tests).
    """
    adir = artifacts_dir or _ARTIFACTS_DIR

    # 1. Compute chart
    if engine is None:
        engine = KerykeionAdapter()
    logger.info("Computing chart for scope=%r", scope)
    bundle = compute_core_chart(birth, engine)

    # 2. Extract features
    features = extract_core_features(bundle)
    logger.debug("Features extracted: %d keys", len(features))
    _persist_artifact("features.json", features, adir)

    # 3. Evaluate rules
    triggers = evaluate_scope_rules(bundle, features, scope, rules_dir=rules_dir)
    logger.info("Rules triggered: %d", len(triggers))
    _persist_artifact(
        "triggers.json",
        [t.model_dump() for t in triggers],
        adir,
    )

    # 4. Retrieve supporting passages
    passages = []
    if retriever is not None:
        query = " ".join(t.explanation for t in triggers) or scope
        passages = retriever.retrieve(query, top_k=top_k)
        logger.info("Passages retrieved: %d", len(passages))
    else:
        logger.info("No retriever provided; skipping passage retrieval")

    # 5. LLM interpretation
    if dry_run or llm_client is None:
        interpretation: dict = {
            "summary": f"Dry-run interpretation for scope '{scope}'.",
            "details": [t.explanation for t in triggers],
            "rule_refs": [t.rule_id for t in triggers],
            "passage_refs": [p.chunk_id for p in passages],
        }
        logger.info("Dry-run mode: LLM call skipped")
    else:
        interpretation = call_llm_for_interpretation(
            bundle, features, triggers, passages, scope, llm_client
        )

    _persist_artifact("interpretation.json", interpretation, adir)

    # 6. Assemble evidence and section
    evidence = build_prediction_evidence(bundle, features, triggers, passages)
    section = generate_scope_report(scope, interpretation, evidence)

    # 7. Build report
    report = PredictionReport(
        birth_name=birth.name,
        chart_bundle_id=str(bundle.computed_at.timestamp()),
        generated_at=datetime.now(timezone.utc),
        sections=[section],
        model_name=getattr(llm_client, "model_name", "dry-run"),
    )
    logger.info("PredictionReport assembled: %d section(s)", len(report.sections))
    _persist_artifact("report.json", report.model_dump(mode="json"), adir)

    return report
