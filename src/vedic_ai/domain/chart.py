"""Chart bundle, divisional chart, and transit snapshot models.

ChartBundle is the central data contract that flows through every pipeline stage.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, ValidationError

from vedic_ai.core.exceptions import SchemaError
from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.dasha import DashaPeriod
from vedic_ai.domain.house import HousePlacement
from vedic_ai.domain.planet import PlanetPlacement

SCHEMA_VERSION = "1.0.0"


class DivisionalChart(BaseModel):
    division: str = Field(description="Varga label, e.g. D1, D9, D10")
    ascendant_longitude: float = Field(ge=0.0, lt=360.0)
    planets: dict[str, PlanetPlacement] = Field(
        default_factory=dict,
        description="Graha name → PlanetPlacement",
    )
    houses: dict[int, HousePlacement] = Field(
        default_factory=dict,
        description="House number (1-12) → HousePlacement",
    )


class TransitSnapshot(BaseModel):
    at_time: datetime
    planets: dict[str, PlanetPlacement] = Field(default_factory=dict)


class ChartBundle(BaseModel):
    schema_version: str = SCHEMA_VERSION
    birth: BirthData
    engine: str
    ayanamsa: str
    node_type: str = "mean"
    d1: DivisionalChart
    vargas: dict[str, DivisionalChart] = Field(default_factory=dict)
    dashas: list[DashaPeriod] = Field(default_factory=list)
    derived_features: dict = Field(default_factory=dict)
    provenance: dict = Field(default_factory=dict)
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Serializer / deserializer functions
# ---------------------------------------------------------------------------

def build_chart_schema_version() -> str:
    """Return the active ChartBundle schema version string."""
    return SCHEMA_VERSION


def serialize_chart_bundle(bundle: ChartBundle) -> dict:
    """Convert a ChartBundle to a canonical JSON-safe dict."""
    return bundle.model_dump(mode="json")


def deserialize_chart_bundle(payload: dict) -> ChartBundle:
    """Parse and validate a dict into a ChartBundle.

    Raises:
        SchemaError: If validation fails.
    """
    try:
        return ChartBundle.model_validate(payload)
    except ValidationError as exc:
        raise SchemaError(f"Invalid ChartBundle payload: {exc}") from exc


def validate_chart_bundle(payload: dict) -> list[str]:
    """Validate a dict against the ChartBundle schema.

    Returns:
        A list of human-readable error strings, or an empty list when valid.
    """
    try:
        ChartBundle.model_validate(payload)
        return []
    except ValidationError as exc:
        return [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()]
