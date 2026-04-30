"""Configuration loader for the Vedic AI framework.

Merges configs/app.yaml with environment variables.
Env vars use the VEDIC_AI__ prefix and __ as the nested delimiter.
Example: VEDIC_AI__LOG__LEVEL=DEBUG overrides log.level.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from vedic_ai.core.exceptions import ConfigError

_DEFAULT_CONFIG_PATH = Path("configs/app.yaml")


class LogConfig(BaseModel):
    level: str = "INFO"
    json_logs: bool = False


class StorageConfig(BaseModel):
    db_url: str = "sqlite:///data/vedic_ai.db"
    cache_dir: str = "data/processed/cache"


class AstrologyConfig(BaseModel):
    engine: str = "swisseph"
    ayanamsa: str = "lahiri"
    house_system: str = "whole_sign"
    node_type: str = "mean"
    divisional_charts: list[str] = ["D1"]


class AppConfig(BaseSettings):
    app_name: str = "vedic-ai"
    environment: str = "development"
    log: LogConfig = LogConfig()
    storage: StorageConfig = StorageConfig()
    astrology: AstrologyConfig = AstrologyConfig()

    model_config = SettingsConfigDict(
        env_prefix="VEDIC_AI__",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (env_settings, init_settings)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file and return its contents as a dict."""
    try:
        with path.open() as fh:
            data = yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML at {path}: {exc}") from exc


def load_app_config(config_path: str | None = None) -> AppConfig:
    """Load application settings, merge env vars, and return a validated AppConfig.

    Args:
        config_path: Path to a YAML config file. Defaults to
            the VEDIC_AI_CONFIG env var or configs/app.yaml.

    Raises:
        ConfigError: If the YAML is malformed or required fields are invalid.
    """
    resolved = Path(
        config_path
        or os.environ.get("VEDIC_AI_CONFIG", str(_DEFAULT_CONFIG_PATH))
    )
    yaml_data = _load_yaml(resolved)

    try:
        return AppConfig(**yaml_data)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc
