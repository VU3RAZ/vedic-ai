"""Unit tests for the configuration loader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from vedic_ai.core.config import AppConfig, load_app_config
from vedic_ai.core.exceptions import ConfigError


def _write_yaml(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "app.yaml"
    p.write_text(yaml.dump(data))
    return p


class TestLoadAppConfig:
    def test_loads_defaults_when_no_file(self, tmp_path: Path) -> None:
        cfg = load_app_config(str(tmp_path / "nonexistent.yaml"))
        assert cfg.app_name == "vedic-ai"
        assert cfg.log.level == "INFO"

    def test_loads_values_from_yaml(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, {"app_name": "test-app", "log": {"level": "DEBUG"}})
        cfg = load_app_config(str(p))
        assert cfg.app_name == "test-app"
        assert cfg.log.level == "DEBUG"

    def test_env_overrides_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        p = _write_yaml(tmp_path, {"log": {"level": "INFO"}})
        monkeypatch.setenv("VEDIC_AI__LOG__LEVEL", "WARNING")
        cfg = load_app_config(str(p))
        assert cfg.log.level == "WARNING"

    def test_env_config_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        p = _write_yaml(tmp_path, {"app_name": "from-env-path"})
        monkeypatch.setenv("VEDIC_AI_CONFIG", str(p))
        cfg = load_app_config()
        assert cfg.app_name == "from-env-path"

    def test_malformed_yaml_raises_config_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("key: [\nunclosed")
        with pytest.raises(ConfigError, match="Failed to parse YAML"):
            load_app_config(str(bad))

    def test_json_logs_default_is_false(self) -> None:
        cfg = load_app_config()
        assert cfg.log.json_logs is False

    def test_json_logs_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VEDIC_AI__LOG__JSON_LOGS", "true")
        cfg = load_app_config()
        assert cfg.log.json_logs is True

    def test_returns_app_config_type(self) -> None:
        cfg = load_app_config()
        assert isinstance(cfg, AppConfig)


class TestAppConfigDefaults:
    def test_storage_defaults(self) -> None:
        cfg = AppConfig()
        assert "sqlite" in cfg.storage.db_url
        assert cfg.storage.cache_dir

    def test_environment_default(self) -> None:
        cfg = AppConfig()
        assert cfg.environment == "development"
