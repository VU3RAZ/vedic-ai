"""Smoke test — verify all Phase 0 modules import without error."""

from __future__ import annotations


def test_import_package() -> None:
    import vedic_ai
    assert vedic_ai.__version__


def test_import_core_config() -> None:
    from vedic_ai.core.config import load_app_config, AppConfig
    assert callable(load_app_config)
    assert AppConfig


def test_import_core_exceptions() -> None:
    from vedic_ai.core.exceptions import (
        VedicAIError,
        ConfigError,
        EngineError,
        SchemaError,
        LLMError,
        RetrievalError,
        RuleError,
    )
    assert issubclass(ConfigError, VedicAIError)
    assert issubclass(EngineError, VedicAIError)


def test_import_core_logging() -> None:
    from vedic_ai.core.logging import setup_logging
    assert callable(setup_logging)


def test_import_cli() -> None:
    from vedic_ai.cli.main import app, register_cli
    assert app
    assert callable(register_cli)


def test_import_subpackages() -> None:
    import vedic_ai.api
    import vedic_ai.domain
    import vedic_ai.engines
    import vedic_ai.evaluation
    import vedic_ai.features
    import vedic_ai.llm
    import vedic_ai.orchestration
    import vedic_ai.retrieval
    import vedic_ai.storage
    import vedic_ai.utils
