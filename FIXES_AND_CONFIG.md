# Bug Fixes & Configuration — Session Summary

## Status: LLM Layer Working ✅

The local LLM pipeline is confirmed working end-to-end:

```
Python code → Ollama (port 11434) → qwen2.5:14b → JSON response ✅
```

---

## Environment

| Item | Value |
|---|---|
| Machine | Dell OptiPlex 5090 |
| RAM | 76 GB |
| GPU | Intel UHD 750 (display only) + NVIDIA GT 730 (2GB, unusable for LLM) |
| CPU inference | Yes — CPU-only |
| OS | Ubuntu (latest) |
| Python | 3.14 (system) + .venv |
| Project root | `/home/rahul/code/astrology` |

---

## LLM Backend: Ollama

Ollama is installed as a **systemd service** and auto-starts on boot.

```bash
# Status
sudo systemctl status ollama

# Start / stop
sudo systemctl start ollama
sudo systemctl stop ollama

# List loaded models
ollama ps

# List downloaded models
ollama list
```

Ollama listens on: `http://localhost:11434`

---

## Model in Use

```
Name:    qwen2.5:14b
Size:    9.0 GB
Why:     Best JSON schema adherence, strong multi-step reasoning,
         follows negative instructions, handles Sanskrit terms.
         14B is the sweet spot for CPU-only inference on this machine.
         Expect ~3-5 tokens/sec on CPU. A 500-token report takes ~2 min.
```

Pull command (already done):
```bash
ollama pull qwen2.5:14b
```

---

## configs/models.yaml — Correct Structure

```yaml
llm:
  backend: ollama           # ollama | lm_studio
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
    timeout_seconds: 120
  lm_studio:
    base_url: "http://localhost:1234/v1"
    model: "local-model"
    timeout_seconds: 120
  temperature: 0.2
  max_tokens: 2048
```

**Critical:** The YAML is nested under `llm.ollama.model` — NOT flat keys like
`llm_model_name`. Any code reading this config must use:

```python
cfg["llm"]["ollama"]["model"]       # correct
cfg["llm"]["ollama"]["base_url"]    # correct
cfg["llm_model_name"]               # WRONG — flat key does not exist
```

---

## Bug Fixes Applied

### Bug 1 — `generate_structured_interpretation` used wrong model name

**File:** `src/vedic_ai/llm/local_client.py`

**Root cause:** Function signature has `model_name` as a required positional
argument. Test calls passed `'test'` as the model name, which Ollama rejected
with 404 because no model named `"test"` exists.

**Fix:** Made all arguments optional and added auto-loading from config:

```python
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

    client = LocalLLMClient(model_name=_model, base_url=_base_url, backend=_backend)
    raw = client.generate(prompt, temperature=temperature)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return repair_llm_output(raw, schema={})
```

**Key detail:** `parents[3]` resolves to `/home/rahul/code/astrology` from
`src/vedic_ai/llm/local_client.py`. Using `parents[4]` incorrectly resolved
to `/home/rahul/code` (one level too high).

---

### Bug 2 — Integration test used wrong model name `llama3`

**File:** `tests/integration/test_local_llm_contract.py`

**Root cause:** `_DEFAULT_MODEL = "llama3"` was hardcoded but `llama3` was
never pulled. Ollama returned 404.

**Fix:**
```python
# Before
_DEFAULT_MODEL = "llama3"

# After
_DEFAULT_MODEL = "qwen2.5:14b"
```

---

### Bug 3 — `KerykeionAdapter` imported inside function, not at module level

**File:** `src/vedic_ai/orchestration/pipeline.py`

**Root cause:** The e2e tests patch `vedic_ai.orchestration.pipeline.KerykeionAdapter`
but `patch()` requires the target to exist at **module level** at import time.
The import was inside the function body (`if engine is None: from ... import ...`)
so `patch()` raised `AttributeError`.

Additionally a duplicate import was accidentally added during debugging.

**Fix:** Move import to module level and remove the duplicate:

```python
# At top of pipeline.py with other imports — line 13
from vedic_ai.engines.kerykeion_adapter import KerykeionAdapter

# Inside run_prediction_pipeline() — remove local import, keep usage
if engine is None:
    engine = KerykeionAdapter()   # ✅ uses module-level import
```

---

## Smoke Test — Run This to Confirm LLM Works

```bash
cd /home/rahul/code/astrology

python -c "
from src.vedic_ai.llm.local_client import generate_structured_interpretation
result = generate_structured_interpretation(
    'Return only this JSON object: {\"status\": \"ok\", \"model\": \"ready\"}'
)
print(result)
"
# Expected: {'status': 'ok', 'model': 'ready'}
```

Direct Ollama curl test (bypasses Python entirely):
```bash
curl -s http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:14b", "prompt": "say hi", "stream": false}' \
  | python3 -m json.tool | grep response
```

---

## Always Run From Project Root

```bash
# ✅ Always
cd /home/rahul/code/astrology
pytest tests/ -q

# ❌ Never run Python from subdirectories
cd configs && python ...    # breaks all imports
cd src && python ...        # breaks all imports
```

---

## Test Status After Fixes

```
pytest tests/ -q

ERRORS:  0   (was 8 — KerykeionAdapter patch fixed)
FAILED:  0   (was 2 — llama3 model name + parents[4] path fixed)
PASSED:  all remaining
```

---

## Next Phase Checklist

Before continuing with Phase 8 (Timing Engine) or later phases:

- [ ] `ollama list` shows `qwen2.5:14b` 
- [ ] `sudo systemctl status ollama` shows `active (running)`
- [ ] Smoke test above returns valid JSON
- [ ] `pytest tests/ -q` shows 0 errors and 0 failures
- [ ] All work done from `/home/rahul/code/astrology`

---

## If Ollama Stops Responding

```bash
sudo systemctl restart ollama
# Wait 5 seconds
curl http://localhost:11434/api/tags
```

## If Model Is Unloaded From Memory (after idle)

Ollama auto-unloads models after 5 minutes of inactivity. The next request
will reload it automatically — just expect a 10-15 second cold-start delay
on the first call after idle.

To keep model warm during development:
```bash
# Set keep-alive to 1 hour
curl http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:14b", "keep_alive": "1h", "prompt": "", "stream": false}'
```
