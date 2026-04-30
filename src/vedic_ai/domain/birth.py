"""Birth data and geographic location domain models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeoLocation(BaseModel):
    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    altitude_m: float = Field(default=0.0)
    place_name: str | None = None


class BirthData(BaseModel):
    model_config = ConfigDict(frozen=True)

    birth_datetime: datetime
    location: GeoLocation
    name: str | None = None
    notes: str | None = None

    @field_validator("birth_datetime")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(
                "birth_datetime must be timezone-aware; "
                "provide an offset such as +05:30 or use UTC."
            )
        return v
