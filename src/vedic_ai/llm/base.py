"""LLM client abstraction: protocol and shared types."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal protocol for a local LLM backend."""

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """Send a prompt and return the raw text response."""
        ...
