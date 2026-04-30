"""Evaluation dataset: labeled chart cases and expected outputs."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from vedic_ai.core.exceptions import ConfigError
from vedic_ai.domain.prediction import PredictionReport


class EvaluationCase(BaseModel):
    case_id: str
    birth_name: str | None = None
    scope: str
    expected_rule_ids: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    forbidden_keywords: list[str] = Field(default_factory=list)
    notes: str = ""
    chart_fixture: str | None = None


class EvaluationSet(BaseModel):
    name: str
    version: str = "1.0"
    cases: list[EvaluationCase] = Field(default_factory=list)


def load_evaluation_set(path: str) -> EvaluationSet:
    """Load labeled evaluation cases from a JSON file.

    The file must contain a dict with 'name', 'version', and 'cases' keys.

    Raises:
        ConfigError: If the file cannot be parsed or fails schema validation.
    """
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Evaluation set not found: {path}")
    try:
        raw = json.loads(p.read_text())
        return EvaluationSet.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Failed to load evaluation set from {path}: {exc}") from exc
