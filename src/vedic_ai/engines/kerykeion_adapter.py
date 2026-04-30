"""Secondary adapter stub — kerykeion backend.

Kerykeion is installed and available, but full Vedic sidereal support
requires more mapping work. This stub satisfies the Protocol interface
and will be fully implemented in a future phase.
"""

from __future__ import annotations

from datetime import datetime

from vedic_ai.core.exceptions import EngineError
from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.chart import ChartBundle, DivisionalChart, TransitSnapshot
from vedic_ai.domain.dasha import DashaPeriod


class KerykeionAdapter:
    """AstrologyEngine stub backed by kerykeion (not yet fully implemented)."""

    def __init__(self, ayanamsa: str = "lahiri", **kwargs) -> None:
        self.ayanamsa = ayanamsa

    def _not_implemented(self) -> None:
        raise EngineError(
            "KerykeionAdapter is a stub. Use SwissEphAdapter for full Vedic calculations."
        )

    def compute_birth_chart(
        self, birth: BirthData, options: dict | None = None
    ) -> ChartBundle:
        self._not_implemented()

    def compute_divisional_chart(
        self, birth: BirthData, division: str, options: dict | None = None
    ) -> DivisionalChart:
        self._not_implemented()

    def compute_dashas(
        self, birth: BirthData, options: dict | None = None
    ) -> list[DashaPeriod]:
        self._not_implemented()

    def compute_transits(
        self, birth: BirthData, at_time: datetime, options: dict | None = None
    ) -> TransitSnapshot:
        self._not_implemented()
