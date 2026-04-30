"""House placement domain model."""

from pydantic import BaseModel, ConfigDict, Field

from vedic_ai.domain.enums import Graha, Rasi


class HousePlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int = Field(ge=1, le=12)
    rasi: Rasi
    cusp_longitude: float = Field(ge=0.0, lt=360.0)
    lord: Graha
    occupants: list[Graha] = Field(default_factory=list)
