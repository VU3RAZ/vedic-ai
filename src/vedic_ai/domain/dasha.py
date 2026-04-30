"""Dasha (planetary period) domain model."""

from datetime import date

from pydantic import BaseModel, Field

from vedic_ai.domain.enums import Graha


class DashaPeriod(BaseModel):
    graha: Graha
    level: int = Field(ge=1, le=3, description="1=Mahadasha, 2=Antardasha, 3=Pratyantardasha")
    start_date: date
    end_date: date
    sub_periods: list["DashaPeriod"] = Field(default_factory=list)


DashaPeriod.model_rebuild()
