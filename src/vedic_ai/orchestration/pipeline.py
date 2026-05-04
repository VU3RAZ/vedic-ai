"""End-to-end prediction pipeline: birth data → PredictionReport."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.prediction import PredictionReport
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter
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
    transit_datetime: datetime | None = None,
    top_k: int = 5,
    dry_run: bool = False,
    raman_method: bool = False,
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

    # 1. Compute chart (include all vargas for rich varga-based analysis)
    _ALL_VARGAS = ["D2","D3","D4","D6","D7","D8","D9","D10","D12",
                   "D16","D20","D24","D27","D30","D60"]
    if engine is None:
        engine = SwissEphAdapter()
    logger.info("Computing chart for scope=%r raman=%s", scope, raman_method)
    bundle = compute_core_chart(birth, engine, include_vargas=_ALL_VARGAS)

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

    # 4. Retrieve supporting passages — multi-query for better coverage
    passages = []
    if retriever is not None:
        from vedic_ai.retrieval.query_expander import expand_queries
        queries = expand_queries(triggers, scope, features, max_queries=5)
        if raman_method:
            queries = [f"Raman house signification {scope} {q}" for q in queries]
        logger.debug("Multi-query retrieval with %d queries", len(queries))
        passages = retriever.retrieve_multi(queries, top_k=top_k)
        logger.info("Passages retrieved: %d (multi-query)", len(passages))
    else:
        logger.info("No retriever provided; skipping passage retrieval")

    # 5. Gochara (transit) context — pre-computed, injected as structured input
    gochara_context: dict | None = None
    if transit_datetime is not None:
        try:
            from vedic_ai.engines.gochara import compute_gochara
            from vedic_ai.api.routes_transit import _serialize_report as _ser_gochara
            transit_snapshot = engine.compute_transits(birth, transit_datetime)
            gochara_report   = compute_gochara(bundle, transit_snapshot)
            gochara_context  = _ser_gochara(gochara_report)
            _persist_artifact("gochara.json", gochara_context, adir)
            logger.info("Gochara context computed for transit_datetime=%s", transit_datetime)
        except Exception as exc:
            logger.warning("Gochara computation failed (continuing without transit context): %s", exc)

    # 6. LLM interpretation (synthesis only — engine findings are the factual base)
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
            bundle, features, triggers, passages, scope, llm_client,
            raman_method=raman_method,
            gochara_context=gochara_context,
        )

    _persist_artifact("interpretation.json", interpretation, adir)

    # 7. Assemble evidence and section
    evidence = build_prediction_evidence(bundle, features, triggers, passages)
    section = generate_scope_report(scope, interpretation, evidence)

    # 8. Build report
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
