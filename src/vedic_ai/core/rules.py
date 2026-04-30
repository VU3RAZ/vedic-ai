"""Rule definition and condition models for the Vedic AI rule engine."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RuleOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"


class ConflictPolicy(str, Enum):
    OVERRIDE = "override"
    DEFER = "defer"
    MERGE = "merge"


class RuleCondition(BaseModel):
    feature: str
    op: RuleOperator
    value: Any


class RuleDefinition(BaseModel):
    rule_id: str
    name: str
    scope: str
    conditions: list[RuleCondition] = Field(min_length=1)
    explanation_template: str
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    source_refs: list[str] = Field(default_factory=list)
    conflict_policy: ConflictPolicy = ConflictPolicy.MERGE

    @model_validator(mode="after")
    def _check_rule_id(self) -> "RuleDefinition":
        if not self.rule_id.strip():
            raise ValueError("rule_id must not be blank")
        return self
