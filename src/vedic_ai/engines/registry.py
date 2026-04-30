"""Engine registry — select and instantiate calculation backends."""

from vedic_ai.core.config import AppConfig
from vedic_ai.core.exceptions import ConfigError
from vedic_ai.engines.base import AstrologyEngine
from vedic_ai.engines.kerykeion_adapter import KerykeionAdapter
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter


def select_engine(engine_name: str, config: AppConfig) -> AstrologyEngine:
    """Instantiate the requested backend using settings from AppConfig.

    Args:
        engine_name: One of "swisseph" or "kerykeion".
        config: Loaded application config (reads config.astrology for defaults).

    Returns:
        A configured AstrologyEngine instance.

    Raises:
        ConfigError: If engine_name is not recognised.
    """
    astro = config.astrology
    match engine_name:
        case "swisseph":
            return SwissEphAdapter(
                ayanamsa=astro.ayanamsa,
                house_system=astro.house_system,
                node_type=astro.node_type,
            )
        case "kerykeion":
            return KerykeionAdapter(ayanamsa=astro.ayanamsa)
        case _:
            raise ConfigError(
                f"Unknown engine {engine_name!r}. Supported: swisseph, kerykeion"
            )
