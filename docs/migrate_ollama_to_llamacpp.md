# Migration: Ollama → llama.cpp

llama.cpp's server exposes an OpenAI-compatible HTTP API (`/v1/completions`, `/v1/chat/completions`), the same format LM Studio already uses. The migration is therefore mostly config changes, a small rewrite of the HTTP dispatch in `local_client.py`, and documentation updates.

Default target URL: `http://localhost:8080` (llama.cpp server default port).

---

## 1. `configs/models.yaml` — primary config change

```yaml
# BEFORE
llm:
  backend: ollama
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
    timeout_seconds: 600
  lm_studio:
    base_url: "http://localhost:1234"
    model: "local-model"
    timeout_seconds: 600
  temperature: 0.2
  max_tokens: 2048

# AFTER
llm:
  backend: llamacpp
  llamacpp:
    base_url: "http://localhost:8080"
    model: "default"          # llama.cpp ignores the model field; put anything
    timeout_seconds: 600
  lm_studio:
    base_url: "http://localhost:1234"
    model: "local-model"
    timeout_seconds: 600
  temperature: 0.2
  max_tokens: 2048
```

`configs/models_llamacpp.yaml` already exists but uses a top-level flat structure that does not match the nested `llm.*` structure the code reads — it can be deleted or updated to the nested form above.

---

## 2. `src/vedic_ai/llm/local_client.py` — core logic

### 2a. Class defaults (lines 20-21)
```python
# BEFORE
base_url: str = "http://localhost:11434"
backend: str = "ollama"

# AFTER
base_url: str = "http://localhost:8080"
backend: str = "llamacpp"
```

### 2b. Backend validation (line 24-25)
```python
# BEFORE
if backend not in ("ollama", "lmstudio"):

# AFTER
if backend not in ("ollama", "lmstudio", "llamacpp"):
```

### 2c. Dispatch method (lines 38-40)
```python
# BEFORE
if self.backend == "ollama":
    return self._generate_ollama(prompt, temperature)
return self._generate_lmstudio(prompt, temperature)

# AFTER
if self.backend == "ollama":
    return self._generate_ollama(prompt, temperature)
return self._generate_openai_compat(prompt, temperature)   # covers lmstudio + llamacpp
```

### 2d. Add `_generate_openai_compat` method / rename `_generate_lmstudio`
Rename `_generate_lmstudio` → `_generate_openai_compat` (or add `llamacpp` as an alias).
llama.cpp `/v1/completions` is identical to LM Studio, so no new HTTP code is needed.

### 2e. Default backend fallback (line 88)
```python
# BEFORE
_backend = backend or cfg.get("backend", "ollama")

# AFTER
_backend = backend or cfg.get("backend", "llamacpp")
```

### 2f. Default base_url fallback (line 89 / line 162 in routes / line 83 in CLI)
Every place that hardcodes `"http://localhost:11434"` as a fallback must change to
`"http://localhost:8080"` (or better: read exclusively from config with no hardcoded fallback).

Affected locations:
- `src/vedic_ai/llm/local_client.py` line 89
- `src/vedic_ai/api/routes_prediction.py` line 162
- `src/vedic_ai/cli/commands_predict.py` line 83

---

## 3. `src/vedic_ai/api/routes_prediction.py` (lines 158-165)

```python
# BEFORE
backend = _models_config.get("llm", {}).get("backend", "ollama")
...
base_url=backend_cfg.get("base_url", "http://localhost:11434"),

# AFTER
backend = _models_config.get("llm", {}).get("backend", "llamacpp")
...
base_url=backend_cfg.get("base_url", "http://localhost:8080"),
```

---

## 4. `src/vedic_ai/cli/commands_predict.py` (lines 79-83)

```python
# BEFORE
backend = models_config.get("llm", {}).get("backend", "ollama")
...
base_url=backend_cfg.get("base_url", "http://localhost:11434"),

# AFTER
backend = models_config.get("llm", {}).get("backend", "llamacpp")
...
base_url=backend_cfg.get("base_url", "http://localhost:8080"),
```

---

## 5. `tests/integration/test_local_llm_contract.py`

```python
# BEFORE
_OLLAMA_URL   = "http://localhost:11434"
_LMSTUDIO_URL = "http://localhost:1234"
_DEFAULT_MODEL = "qwen2.5:14b"
ollama_available = _server_reachable(_OLLAMA_URL)

# AFTER
_LLAMACPP_URL  = "http://localhost:8080"
_LMSTUDIO_URL  = "http://localhost:1234"
_DEFAULT_MODEL  = "default"         # or the GGUF filename you load
llamacpp_available = _server_reachable(_LLAMACPP_URL)
```

All `LocalLLMClient(... base_url=_OLLAMA_URL)` calls must change to use `_LLAMACPP_URL`
and `backend="llamacpp"`.
The `skip_no_llm` marker should check `llamacpp_available` instead of `ollama_available`.

---

## 6. Documentation files

### `README.md`
| Location | Change |
|---|---|
| Line 31 | Replace "Ollama / LM Studio — qwen2.5:14b" with "llama.cpp / LM Studio" |
| Line 230 | Update `models.yaml` description |
| Line 253 | Update `LocalLLMClient` description |
| Line 280 | Replace Ollama row in tech table |
| Lines 290-298 | Update YAML example to use `llamacpp` backend |
| Line 299 | Replace `ollama pull qwen2.5:14b` with llama.cpp server startup command |

### `FIXES_AND_CONFIG.md`
The entire "## LLM Backend: Ollama" section (lines 27-264) should be rewritten for llama.cpp:
- Replace `http://localhost:11434` with `http://localhost:8080`
- Replace `systemctl status ollama` with llama.cpp server process management
- Replace `ollama list` / `ollama ps` with equivalent (`ps aux | grep llama-server`)
- Replace curl examples pointing at `/api/generate` with `/v1/completions`

### `docs/usage_guide.md`
| Location | Change |
|---|---|
| Lines 39-47 | Replace Ollama prerequisite with llama.cpp server startup |
| Lines 103-110 | Update YAML config example |
| Lines 117-121 | Update "switch backend" instructions |
| Line 265 | Update Python example base_url |
| Lines 475-490 | Update architecture description |
| Lines 769-772 | Update "LLM not running" troubleshooting steps |
| Lines 785-792 | Update timeout section |
| Lines 850-865 | Update curl examples |

---

## 7. llama.cpp server startup (replaces `ollama serve`)

```bash
# load a GGUF model and start the OpenAI-compatible server
llama-server \
  --model /path/to/model.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 4096 \
  --n-predict 2048
```

Key differences from Ollama:
- No model registry — you point directly at a `.gguf` file path.
- The `model` field in JSON requests is ignored by llama.cpp server; the loaded model is always used.
- API endpoint for text completion: `POST /v1/completions` (same as LM Studio).
- No keep-alive or auto-unload configuration; the model stays loaded as long as the process runs.

---

## Summary of files to change

| File | Nature of change |
|---|---|
| `configs/models.yaml` | Add `llamacpp` backend block, change default backend |
| `configs/models_llamacpp.yaml` | Delete or rewrite to match nested structure |
| `src/vedic_ai/llm/local_client.py` | Add `llamacpp` to valid backends, update defaults, unify dispatch |
| `src/vedic_ai/api/routes_prediction.py` | Update default backend/URL strings |
| `src/vedic_ai/cli/commands_predict.py` | Update default backend/URL strings |
| `tests/integration/test_local_llm_contract.py` | Swap Ollama URL/skip marker for llama.cpp |
| `README.md` | Update setup instructions and tech table |
| `FIXES_AND_CONFIG.md` | Rewrite Ollama section for llama.cpp |
| `docs/usage_guide.md` | Update prerequisites, config examples, troubleshooting |
