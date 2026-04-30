"""Typed exceptions for the Vedic AI framework."""


class VedicAIError(Exception):
    """Base exception for all framework errors."""


class ConfigError(VedicAIError):
    """Raised when configuration is missing, invalid, or inconsistent."""


class EngineError(VedicAIError):
    """Raised when the astrology calculation engine fails or returns unexpected output."""


class SchemaError(VedicAIError):
    """Raised when a domain object fails validation."""


class LLMError(VedicAIError):
    """Raised when the local LLM client fails or returns unparseable output."""


class RetrievalError(VedicAIError):
    """Raised when the vector retrieval layer fails."""


class RuleError(VedicAIError):
    """Raised when a rule definition is invalid or cannot be evaluated."""
