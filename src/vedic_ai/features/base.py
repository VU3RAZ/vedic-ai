"""Base definitions for the feature extraction layer."""

from typing import Protocol

from vedic_ai.domain.chart import ChartBundle

# House types by number
HOUSE_TYPES: dict[int, str] = {
    1: "angular", 4: "angular", 7: "angular", 10: "angular",
    2: "succedent", 5: "succedent", 8: "succedent", 11: "succedent",
    3: "cadent", 6: "cadent", 9: "cadent", 12: "cadent",
}

# Trikona and kendra house sets (used for yoga detection)
TRIKONA_HOUSES: frozenset[int] = frozenset({1, 5, 9})
KENDRA_HOUSES: frozenset[int] = frozenset({1, 4, 7, 10})
DUSTHANA_HOUSES: frozenset[int] = frozenset({6, 8, 12})


class FeatureExtractor(Protocol):
    """Structural interface for a feature extraction callable."""

    def __call__(self, bundle: ChartBundle) -> dict: ...
