"""AstrologyEngine protocol and pipeline helper."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.chart import ChartBundle, DivisionalChart, TransitSnapshot
from vedic_ai.domain.dasha import DashaPeriod


@runtime_checkable
class AstrologyEngine(Protocol):
    """Structural interface all calculation backends must satisfy."""

    def compute_birth_chart(
        self, birth: BirthData, options: dict | None = None
    ) -> ChartBundle: ...

    def compute_divisional_chart(
        self, birth: BirthData, division: str, options: dict | None = None
    ) -> DivisionalChart: ...

    def compute_dashas(
        self, birth: BirthData, options: dict | None = None
    ) -> list[DashaPeriod]: ...

    def compute_transits(
        self, birth: BirthData, at_time: datetime, options: dict | None = None
    ) -> TransitSnapshot: ...


def compute_core_chart(
    birth: BirthData,
    engine: AstrologyEngine,
    include_dashas: bool = True,
    include_vargas: list[str] | None = None,
) -> ChartBundle:
    """Compute and assemble an interpretation-ready ChartBundle.

    Args:
        birth: Birth data including time, location, and timezone.
        engine: The calculation backend to use.
        include_dashas: When True, compute Vimshottari Mahadashas.
        include_vargas: Optional list of divisional chart codes (e.g. ["D9"]).

    Returns:
        A fully populated ChartBundle ready for feature extraction.
    """
    bundle = engine.compute_birth_chart(birth)

    if include_dashas:
        bundle.dashas = engine.compute_dashas(birth)

    if include_vargas:
        for varga in include_vargas:
            d = engine.compute_divisional_chart(birth, varga)
            bundle.vargas[varga] = d

    return bundle
