"""Prediction, rule trigger, and evidence domain models."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from vedic_ai.domain.chart import SCHEMA_VERSION


class RuleTrigger(BaseModel):
    rule_id: str
    rule_name: str
    scope: str
    weight: float = Field(ge=0.0, le=1.0)
    evidence: dict = Field(default_factory=dict)
    explanation: str
    source_refs: list[str] = Field(default_factory=list)
    conflict_policy: str = "merge"


class PredictionEvidence(BaseModel):
    trigger: RuleTrigger | None = None
    passage: str | None = None
    source: str | None = None
    chart_facts: list[str] = Field(default_factory=list)


class PredictionSection(BaseModel):
    scope: str
    summary: str
    details: list[str] = Field(default_factory=list)
    evidence: list[PredictionEvidence] = Field(default_factory=list)


class PredictionReport(BaseModel):
    birth_name: str | None = None
    chart_bundle_id: str | None = None
    generated_at: datetime
    sections: list[PredictionSection] = Field(default_factory=list)
    model_name: str
    schema_version: str = SCHEMA_VERSION


class ForecastWindow(BaseModel):
    start_date: date
    end_date: date
    mahadasha_lord: str | None = None
    antardasha_lord: str | None = None
    scope: str
    summary: str = ""
    details: list[str] = Field(default_factory=list)
    evidence: list[PredictionEvidence] = Field(default_factory=list)


class ForecastReport(BaseModel):
    birth_name: str | None = None
    generated_at: datetime
    scopes: list[str] = Field(default_factory=list)
    windows: list[ForecastWindow] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
