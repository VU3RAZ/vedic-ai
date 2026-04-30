"""Local LLM client supporting Ollama and LM Studio HTTP backends."""

from __future__ import annotations

import json

from vedic_ai.core.exceptions import ConfigError


class LocalLLMClient:
    """HTTP client for a local LLM running on Ollama or LM Studio.

    Ollama:    base_url="http://localhost:11434", backend="ollama"
    LM Studio: base_url="http://localhost:1234",  backend="lmstudio"
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        backend: str = "ollama",
        timeout: int = 120,
    ) -> None:
        if backend not in ("ollama", "lmstudio"):
            raise ConfigError(f"Unknown backend '{backend}'. Use 'ollama' or 'lmstudio'.")
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.backend = backend
        self.timeout = timeout

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """Send prompt to the local model and return the raw response text."""
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise ImportError("requests is required: pip install requests") from exc

        if self.backend == "ollama":
            return self._generate_ollama(prompt, temperature)
        return self._generate_lmstudio(prompt, temperature)

    def _generate_ollama(self, prompt: str, temperature: float) -> str:
        import requests

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _generate_lmstudio(self, prompt: str, temperature: float) -> str:
        import requests

        url = f"{self.base_url}/v1/completions"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": 2048,
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if not choices:
            return ""
        return choices[0].get("text", "")

def generate_structured_interpretation(
    prompt: str,
    model_name: str | None = None,
    temperature: float = 0.2,
    base_url: str | None = None,
    backend: str | None = None,
) -> dict:
    import yaml
    from pathlib import Path
    from vedic_ai.llm.output_parser import repair_llm_output

    cfg_path = Path(__file__).parents[3] / "configs" / "models.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)["llm"]

    _backend  = backend    or cfg.get("backend", "ollama")
    _base_url = base_url   or cfg[_backend]["base_url"]
    _model    = model_name or cfg[_backend]["model"]
    _timeout  = cfg[_backend].get("timeout_seconds", 600)

    client = LocalLLMClient(model_name=_model, base_url=_base_url, backend=_backend, timeout=_timeout)
    raw = client.generate(prompt, temperature=temperature)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return repair_llm_output(raw, schema={})

