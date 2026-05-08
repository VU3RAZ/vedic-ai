"""Cloud LLM clients — Gemini (Google GenAI SDK).

Interface: same as LocalLLMClient — a single generate(prompt) -> str method.
The caller is the same call_llm_for_interpretation() pipeline step; nothing
else in the codebase needs to know which backend is active.

Setup (Gemini free tier):
  1. pip install google-genai
  2. Get a free API key at https://aistudio.google.com/apikey
  3. Set GEMINI_API_KEY=<your_key> in the environment (or .env file)
  4. In configs/models.yaml set:  llm.backend: gemini
"""

from __future__ import annotations

import os


class GeminiClient:
    """Wraps Google GenAI SDK for Gemini models.

    Free tier (as of 2025): gemini-flash-lite-latest — 1,500 req/day, 30 RPM, no charge.
    API key: GEMINI_API_KEY env var (or GOOGLE_API_KEY — both are checked).
    """

    def __init__(
        self,
        model_name: str = "gemini-flash-lite-latest",
        api_key: str | None = None,
        max_tokens: int = 4096,
        timeout: int = 60,
    ) -> None:
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.timeout    = timeout
        self._api_key   = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or self._key_from_yaml()
        )
        if not self._api_key:
            raise EnvironmentError(
                "Gemini API key not found. "
                "Set GEMINI_API_KEY in your environment, or add\n"
                "  gemini:\n    api_key: AIza...\n"
                "to configs/models.yaml (keep that file out of git).\n"
                "Free key: https://aistudio.google.com/apikey"
            )

    @staticmethod
    def _key_from_yaml() -> str | None:
        """Read api_key from configs/models.yaml gemini block if present."""
        try:
            from pathlib import Path
            import yaml
            cfg_path = Path(__file__).parents[3] / "configs" / "models.yaml"
            cfg = yaml.safe_load(cfg_path.read_text()) or {}
            return cfg.get("llm", {}).get("gemini", {}).get("api_key")
        except Exception:
            return None

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """Send prompt to Gemini and return the response text."""
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ImportError(
                "google-genai package is required: pip install google-genai"
            ) from exc

        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=self.max_tokens,
                # Ask Gemini to return plain JSON — matches our prompt instruction
                response_mime_type="application/json",
            ),
        )
        return response.text or ""
