"""Planetary placement domain models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vedic_ai.domain.enums import Dignity, Graha, NakshatraName, Rasi


class RasiPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    rasi: Rasi
    degree_in_rasi: float = Field(ge=0.0, lt=30.0)


class NakshatraPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    nakshatra: NakshatraName
    pada: int = Field(ge=1, le=4)
    nakshatra_lord: Graha
    degree_in_nakshatra: float = Field(ge=0.0, lt=13.334)


class PlanetPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)

    graha: Graha
    longitude: float = Field(ge=0.0, lt=360.0)
    latitude: float = Field(default=0.0)
    speed: float = Field(default=0.0, description="Degrees per day; negative = retrograde")
    is_retrograde: bool = False
    rasi: RasiPlacement
    nakshatra: NakshatraPlacement
    house: int = Field(ge=1, le=12)
    dignity: Dignity | None = None

    @model_validator(mode="after")
    def nodes_are_always_retrograde(self) -> "PlanetPlacement":
        if self.graha in (Graha.RAHU, Graha.KETU) and not self.is_retrograde:
            raise ValueError(f"{self.graha.value} must always be retrograde (is_retrograde=True).")
        return self
