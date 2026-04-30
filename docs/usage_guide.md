# Vedic AI — Usage Guide

*From user input to prediction report: a complete walkthrough.*

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Installation and index build](#2-installation-and-index-build)
3. [Configuration](#3-configuration)
4. [Three ways to run predictions](#4-three-ways-to-run-predictions)
   - 4a. Command-line interface (CLI)
   - 4b. Python API (direct)
   - 4c. REST API (FastAPI server)
5. [What happens inside the pipeline](#5-what-happens-inside-the-pipeline)
   - Step 1 · Validate birth input
   - Step 2 · Compute the birth chart
   - Step 3 · Extract derived features
   - Step 4 · Evaluate interpretation rules
   - Step 5 · Retrieve supporting passages (RAG)
   - Step 6 · Build the LLM prompt
   - Step 7 · Generate structured interpretation
   - Step 8 · Assemble evidence and report
6. [Understanding the output](#6-understanding-the-output)
7. [Timing and forecast reports](#7-timing-and-forecast-reports)
8. [Debugging with artifacts](#8-debugging-with-artifacts)
9. [Caching and storage](#9-caching-and-storage)
10. [Evaluation and reproducibility](#10-evaluation-and-reproducibility)
11. [Common issues](#11-common-issues)

---

## 1. Prerequisites

| Requirement | Detail |
|---|---|
| Python | 3.11 or later |
| Ollama | Running on `http://localhost:11434` |
| Model pulled | `ollama pull qwen2.5:14b` |
| System RAM | ≥ 16 GB recommended (14B model loads ~9 GB) |

Verify Ollama is ready:

```bash
ollama list              # should show qwen2.5:14b
curl http://localhost:11434/api/tags   # should return JSON
```

---

## 2. Installation and index build

```bash
git clone https://github.com/VU3RAZ/vedic-ai.git
cd vedic-ai

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# Install with all optional feature sets
pip install -e ".[dev,engine,retrieval,llm,api]"

# Verify
vedic-ai --help
pytest tests/unit -q               # should be 100% green
```

### Build the retrieval index (required once before first use)

```bash
vedic-ai build-index
# [1/4] Ingesting corpus from data/corpus/texts/ ...
#        9 sources — 1,525,642 total chars
# [2/4] Chunking ...
#        3,054 chunks produced
# [3/4] Embedding with 'all-MiniLM-L6-v2' (this may take a few minutes) ...
#        3,054 vectors — dim=384
# [4/4] Building FAISS index in data/processed ...
# Index ready: data/processed/faiss.index

# Check status anytime:
vedic-ai corpus-info

# Force rebuild (e.g. after adding new text files):
vedic-ai build-index --force
```

The index is built fully offline — no HuggingFace Hub calls are made at runtime (controlled by `HF_HUB_OFFLINE=1` set automatically by the CLI).

---

## 3. Configuration

All configuration lives in `configs/`. You rarely need to edit these for basic use.

### `configs/models.yaml` — LLM backend

```yaml
llm:
  backend: ollama          # ollama | lm_studio
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
    timeout_seconds: 600   # CPU inference — increase if needed
  temperature: 0.2
  max_tokens: 2048
```

To switch to a different model (e.g. `llama3.1:8b`):
```yaml
model: "llama3.1:8b"
```

To use LM Studio instead of Ollama:
```yaml
backend: lm_studio
lm_studio:
  base_url: "http://localhost:1234/v1"
  model: "local-model"
```

### `configs/app.yaml` — Engine and logging

```yaml
astrology:
  engine: swisseph         # primary calculation engine
  ayanamsa: lahiri         # Vedic sidereal correction
  house_system: whole_sign
  node_type: mean          # mean or true nodes (Rahu/Ketu)

log:
  level: INFO              # DEBUG for verbose pipeline output
  json_logs: false
```

### `configs/retrieval.yaml` — Vector store

```yaml
backend: faiss             # faiss | chroma
embedding_model: all-MiniLM-L6-v2
chunk_size: 600
overlap: 100
top_k: 5
```

Environment variable overrides use `__` as the separator:
```bash
VEDIC_AI__LOG__LEVEL=DEBUG vedic-ai predict ...
```

---

## 4. Four ways to run predictions

### 4a. Web UI (easiest)

```bash
vedic-ai serve            # starts http://127.0.0.1:8000
vedic-ai serve --port 8080
vedic-ai serve --host 0.0.0.0 --port 8080   # accessible on your LAN
```

Open the printed URL in any browser. The interface provides:

- **Birth Data form** — name, date/time, timezone selector (14 presets), lat/lon, scope, dry-run toggle
- **Quick Fill chips** — one-click example charts (Nagpur 1972, Delhi 1985, Mumbai 2000)
- **Compute Chart** button — shows the natal chart table (planet, sign, degree, house, retrograde), house table (sign, lord, occupants), and Vimshottari dasha table
- **Generate Prediction** button — runs the full pipeline and shows one prediction card per scope, each with summary, details, and a collapsible evidence accordion (rule triggers + BPHS passages)

The web UI talks to the same FastAPI backend as the REST API below.

### 4b. Command-line interface (CLI)

The `vedic-ai predict` command is the fastest text-based entry point.

**Syntax:**
```
vedic-ai predict <birth_datetime> <latitude> <longitude> [options]
```

**Arguments:**
| Argument | Format | Example |
|---|---|---|
| `birth_datetime` | ISO-8601 with timezone offset | `"1990-04-05T10:30:00+05:30"` |
| `latitude` | Decimal degrees, N positive | `28.6139` |
| `longitude` | Decimal degrees, E positive | `77.2090` |

**Options:**
| Flag | Default | Purpose |
|---|---|---|
| `--scope` / `-s` | *(all three)* | `personality`, `career`, or `relationships`. Omit to run all. |
| `--name` / `-n` | — | Native's name (included in report) |
| `--dry-run` | off | Skip LLM; return evidence-only report (fast) |
| `--no-rag` | off | Disable FAISS retrieval (faster, less grounded) |
| `--top-k` / `-k` | 5 | Number of corpus passages to retrieve |
| `--output` / `-o` | stdout | Write JSON report to a file |

**Examples:**

```bash
# All three scopes — full LLM run with RAG
vedic-ai predict "1972-08-27T19:45:00+05:30" 21.15 79.08 --name "Rahul"

# Single scope
vedic-ai predict "1990-04-05T10:30:00+05:30" 28.61 77.21 --scope career

# Fast dry-run (no LLM, instant, good for debugging rules)
vedic-ai predict "1972-08-27T19:45:00+05:30" 21.15 79.08 --dry-run

# Save to file
vedic-ai predict "1985-11-15T06:00:00+05:30" 19.07 72.87 \
    --name "Draupadi" --scope personality -o report.json

# Disable RAG for a quicker result
vedic-ai predict "1990-04-05T10:30:00+05:30" 28.61 77.21 --no-rag
```

**Birth datetime rules:**
- Must be ISO-8601 format.
- **Must include a timezone offset** — `+05:30` for IST, `+00:00` for UTC, `-05:00` for US Eastern, etc.
- Naive datetimes (without offset) are rejected.

---

### 4c. Python API (direct)

Use this when you want to embed prediction in a script or integrate with other systems.

#### Minimal example

```python
from datetime import datetime, timezone
from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.orchestration.pipeline import run_prediction_pipeline

# 1. Build birth data
birth = BirthData(
    birth_datetime=datetime(1990, 4, 5, 10, 30, tzinfo=timezone.utc),
    location=GeoLocation(latitude=28.61, longitude=77.21, place_name="Delhi"),
    name="Arjuna",
)

# 2. Run pipeline (dry_run=True skips the LLM call)
report = run_prediction_pipeline(birth=birth, scope="career", dry_run=True)

# 3. Access the report
print(report.birth_name)                     # Arjuna
print(report.sections[0].summary)            # interpretation text
print(report.sections[0].scope)              # career
for ev in report.sections[0].evidence:
    if ev.trigger:
        print(ev.trigger.rule_id, ev.trigger.explanation)
```

#### With real LLM (full pipeline)

```python
from vedic_ai.llm.local_client import LocalLLMClient

llm = LocalLLMClient(
    model_name="qwen2.5:14b",
    base_url="http://localhost:11434",
    backend="ollama",
)

report = run_prediction_pipeline(
    birth=birth,
    scope="personality",
    llm_client=llm,
)

print(report.sections[0].summary)
```

#### With retrieval (RAG enabled)

Build the corpus index once, then reuse the retriever across calls:

```python
from pathlib import Path
from vedic_ai.retrieval.corpus_loader import ingest_corpus
from vedic_ai.retrieval.chunker import chunk_corpus_documents
from vedic_ai.retrieval.embedder import embed_corpus_chunks
from vedic_ai.retrieval.vector_store import build_vector_index
from vedic_ai.retrieval.retriever import create_retriever

# Build index (do this once; persist to disk)
manifest = ingest_corpus(
    source_paths=["data/corpus/texts/"],
    output_dir="data/processed/corpus",
)
chunks = chunk_corpus_documents(manifest)
batch = embed_corpus_chunks(chunks, model_name="all-MiniLM-L6-v2")
handle = build_vector_index(batch, backend="faiss")

# Create retriever
retriever = create_retriever(chunks, handle)

# Use in pipeline
report = run_prediction_pipeline(
    birth=birth,
    scope="career",
    retriever=retriever,
    llm_client=llm,
    top_k=5,
)
```

#### Multi-scope report (call three times)

```python
import json

scopes = ["personality", "career", "relationships"]
all_sections = []

for scope in scopes:
    rep = run_prediction_pipeline(birth=birth, scope=scope, llm_client=llm)
    all_sections.extend(rep.sections)

# Combine into one JSON blob
combined = {
    "birth_name": birth.name,
    "sections": [s.model_dump(mode="json") for s in all_sections],
}
print(json.dumps(combined, indent=2))
```

---

### 4d. REST API (FastAPI server)

Start the server:

```bash
vedic-ai serve                  # recommended
# or directly via uvicorn:
uvicorn vedic_ai.api.app:create_api_app --factory --port 8000 --reload
```

The API is now available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

**Endpoints:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Web UI (HTML frontend) |
| GET | `/health` | Liveness check |
| GET | `/predictions/scopes` | List valid scopes |
| POST | `/predictions` | Run full prediction pipeline |
| POST | `/charts/compute` | Compute chart only (no prediction) |

---

#### `POST /predictions`

**Request body:**
```json
{
  "birth_datetime": "1990-04-05T10:30:00+05:30",
  "latitude": 28.61,
  "longitude": 77.21,
  "place_name": "Delhi",
  "name": "Arjuna",
  "scope": "all",
  "dry_run": false
}
```
`scope` accepts `"all"` (default — runs all three and merges sections), `"personality"`, `"career"`, or `"relationships"`.

**`curl` example:**
```bash
curl -s -X POST http://localhost:8000/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "birth_datetime": "1990-04-05T10:30:00+05:30",
    "latitude": 28.61,
    "longitude": 77.21,
    "name": "Arjuna",
    "scope": "career",
    "dry_run": true
  }' | python3 -m json.tool
```

**Python `httpx` example:**
```python
import httpx, json

resp = httpx.post("http://localhost:8000/predictions", json={
    "birth_datetime": "1990-04-05T10:30:00+05:30",
    "latitude": 28.61,
    "longitude": 77.21,
    "name": "Arjuna",
    "scope": "career",
    "dry_run": True,
})
report = resp.json()
print(report["sections"][0]["summary"])
```

---

#### `POST /charts/compute`

Returns only the `ChartBundle` (no prediction). Use this when you want raw planetary positions.

```bash
curl -s -X POST http://localhost:8000/charts/compute \
  -H "Content-Type: application/json" \
  -d '{
    "birth_datetime": "1990-04-05T10:30:00+05:30",
    "latitude": 28.61,
    "longitude": 77.21,
    "ayanamsa": "lahiri",
    "house_system": "whole_sign"
  }' | python3 -m json.tool
```

---

## 5. What happens inside the pipeline

When you call `run_prediction_pipeline()` (or `vedic-ai predict`), the following sequence executes in order. Each step persists a debugging artifact to `data/processed/artifacts/`.

```
BirthData
    │
    ▼ Step 1
[Validate input]
  • timezone-aware datetime required
  • lat/lon in valid range
    │
    ▼ Step 2
[Compute birth chart]  ←── SwissEphAdapter (pyswisseph, Moshier ephemeris)
  • Sidereal positions for 9 grahas (Sun–Saturn + Rahu/Ketu)
  • 12 whole-sign houses
  • Lahiri ayanamsa correction
  • Vimshottari Mahadasha periods (120-year span)
  → ChartBundle (schema-versioned JSON, Pydantic-validated)
    │
    ▼ Step 3
[Extract features]  ←── core_features.py
  • Planet strengths, dignity (exalted / own / debilitated / …)
  • House lordships (which graha rules each house, and where it sits)
  • Aspect graph (graha drishti, conjunctions, sign exchanges)
  • Nakshatra placements + pada + nakshatra lord for each graha
  • Yoga detection (Gajakesari, Kemadruma, Raja yogas, Dhana yogas)
  → features dict  ──── saved → artifacts/features.json
    │
    ▼ Step 4
[Evaluate rules]  ←── rule_evaluator.py + data/corpus/rules/<scope>.yaml
  • Loads YAML rules for the requested scope
  • Evaluates each rule's conditions against the features dict
  • Operators: eq, ne, gt, lt, in, not_in, contains
  • Applies conflict resolution (merge / override / defer)
  → list[RuleTrigger]  ── saved → artifacts/triggers.json
    │
    ▼ Step 5  (skipped if no retriever provided)
[Retrieve passages]  ←── FAISS index + sentence-transformers
  • Builds query from triggered rule explanations
  • Embeds query with all-MiniLM-L6-v2 (384-dim)
  • Cosine search over indexed corpus chunks
  → list[RetrievedPassage] (BPHS, Phaladeepika, nakshatra notes, …)
    │
    ▼ Step 6
[Build prompt]  ←── prompt_builder.py
  • Fixed section order: CHART FACTS → DERIVED FEATURES →
    TRIGGERED RULES → SUPPORTING PASSAGES → TASK
  • Deterministic for fixed input (snapshot-testable)
    │
    ▼ Step 7
[Generate interpretation]  ←── LocalLLMClient → Ollama → qwen2.5:14b
  • Sends prompt via HTTP to Ollama (or LM Studio)
  • Expects valid JSON response: {summary, details, rule_refs, passage_refs}
  • Falls back through json5 → regex extract → minimal fallback on parse error
  → interpretation dict  ── saved → artifacts/interpretation.json
    │
    ▼ Step 8
[Assemble report]  ←── evidence_builder.py
  • One PredictionEvidence per triggered rule (carries chart_facts)
  • One PredictionEvidence per retrieved passage (carries source)
  • Wraps everything in a PredictionSection for the scope
  • Wraps in PredictionReport with schema_version + generated_at
  → PredictionReport  ──── saved → artifacts/report.json
```

**Dry-run mode** skips Step 7. The interpretation is synthetically built from rule explanations alone — no LLM call, no Ollama dependency, near-instant response.

---

## 6. Understanding the output

All three entry points produce the same `PredictionReport` structure:

```json
{
  "birth_name": "Arjuna",
  "chart_bundle_id": "1746366600.123456",
  "generated_at": "2026-04-30T10:30:00+00:00",
  "model_name": "qwen2.5:14b",
  "schema_version": "1.0.0",
  "sections": [
    {
      "scope": "career",
      "summary": "Sun placed in the 10th house confers prominence and authority ...",
      "details": [
        "Sun in the 10th house is a powerful yoga for government or leadership roles.",
        "Saturn's aspect on the 10th house adds discipline and longevity to career gains."
      ],
      "evidence": [
        {
          "trigger": {
            "rule_id": "C001",
            "rule_name": "Sun in 10th House — Career Prominence",
            "scope": "career",
            "weight": 0.75,
            "explanation": "Sun placed in the 10th house ...",
            "source_refs": ["BPHS 24.5"],
            "evidence": {"planets.Sun.house": 10}
          },
          "passage": null,
          "source": null,
          "chart_facts": [
            "Sun: sign=Aries, house=10",
            "Moon: sign=Cancer, house=1",
            "..."
          ]
        },
        {
          "trigger": null,
          "passage": "When the Sun occupies the tenth house, the native is endowed ...",
          "source": "BPHS Ch.24",
          "chart_facts": ["Sun: sign=Aries, house=10", "..."]
        }
      ]
    }
  ]
}
```

**Key fields:**

| Field | What it tells you |
|---|---|
| `sections[].summary` | Main LLM-generated interpretation paragraph |
| `sections[].details` | List of supporting points from the LLM |
| `evidence[].trigger.rule_id` | Which YAML rule fired |
| `evidence[].trigger.evidence` | Exact feature value(s) that matched the rule condition |
| `evidence[].passage` | Verbatim corpus excerpt (when retrieval is enabled) |
| `evidence[].chart_facts` | Snapshot of natal planet positions for this trigger |
| `model_name` | Which LLM generated this report (`dry-run` if skipped) |
| `schema_version` | `1.0.0` — use this when deserialising stored reports |

**Export to Markdown:**

```python
from vedic_ai.api.routes_prediction import export_report
md = export_report(report, fmt="markdown")
print(md)
# → # Prediction Report — Arjuna
#   ## Career
#   Sun placed in the 10th house ...
#   - Saturn's aspect adds discipline ...
```

---

## 7. Timing and forecast reports

The timing engine produces a `ForecastReport` — a sequence of prediction windows over a date range, each annotated with the active Mahadasha and Antardasha.

```python
from datetime import datetime, timezone
from vedic_ai.orchestration.timing_service import generate_forecast_window

forecast = generate_forecast_window(
    birth=birth,
    start=datetime(2026, 1, 1, tzinfo=timezone.utc),
    end=datetime(2026, 12, 31, tzinfo=timezone.utc),
    scopes=["career", "relationships"],
    step_days=30,          # one window per 30 days
)

for window in forecast.windows:
    print(f"{window.start_date} → {window.end_date}")
    print(f"  Scope: {window.scope}")
    print(f"  Mahadasha: {window.mahadasha_lord} / Antardasha: {window.antardasha_lord}")
    print(f"  {window.summary}")
    print()
```

**ForecastWindow fields:**

| Field | Description |
|---|---|
| `start_date` / `end_date` | Date range this window covers |
| `mahadasha_lord` | Active Mahadasha lord at window start (e.g. `"Jupiter"`) |
| `antardasha_lord` | Active Antardasha lord (e.g. `"Saturn"`) |
| `scope` | `career`, `personality`, or `relationships` |
| `summary` | Best-matching timing rule explanation for this window |
| `details` | All matched timing rule explanations |
| `evidence` | `PredictionEvidence` list (same structure as PredictionReport) |

**Active dasha lookup (standalone):**

```python
from datetime import date, datetime, timezone
from vedic_ai.features.dasha_features import (
    get_active_mahadasha,
    get_active_antardasha,
    compute_timing_features,
)

# If you already have a ChartBundle with dashas populated:
at = datetime(2026, 4, 30, tzinfo=timezone.utc)
timing = compute_timing_features(bundle, at)
print(timing["timing"]["mahadasha"]["lord"])    # e.g. "Jupiter"
print(timing["timing"]["antardasha"]["lord"])   # e.g. "Saturn"
print(timing["timing"]["mahadasha"]["start"])   # "2015-01-01"
print(timing["timing"]["mahadasha"]["end"])     # "2031-01-01"
```

---

## 8. Debugging with artifacts

Every pipeline run automatically saves four files to `data/processed/artifacts/`:

| File | Contents |
|---|---|
| `features.json` | Full extracted feature dict (planets, houses, yogas, lagna, …) |
| `triggers.json` | All matched rules, their conditions, weights, and evidence values |
| `interpretation.json` | Raw LLM response (or dry-run fallback) |
| `report.json` | Final `PredictionReport` as JSON |

**Inspect triggered rules:**

```bash
python3 -c "
import json
triggers = json.loads(open('data/processed/artifacts/triggers.json').read())
for t in triggers:
    print(t['rule_id'], t['rule_name'], '→ weight', t['weight'])
    print('  evidence:', t['evidence'])
"
```

**Inspect raw LLM output:**

```bash
cat data/processed/artifacts/interpretation.json
```

**Use a custom artifact directory** (useful for per-run archiving):

```python
from pathlib import Path
report = run_prediction_pipeline(
    birth=birth,
    scope="career",
    llm_client=llm,
    artifacts_dir=Path(f"data/processed/runs/{birth.name}"),
)
```

**Enable debug logging** for step-by-step output:

```bash
VEDIC_AI__LOG__LEVEL=DEBUG vedic-ai predict "1990-04-05T10:30:00+05:30" 28.61 77.21
```

---

## 9. Caching and storage

### Chart cache (avoid recomputing the same chart)

```python
from vedic_ai.storage.cache import build_cache_key, cache_chart_bundle, load_cached_chart_bundle
from vedic_ai.engines.swisseph_adapter import SwissEphAdapter
from vedic_ai.engines.base import compute_core_chart

engine = SwissEphAdapter()
key = build_cache_key(birth)

bundle = load_cached_chart_bundle(key)
if bundle is None:
    bundle = compute_core_chart(birth, engine)
    cache_chart_bundle(key, bundle)
    print("Computed and cached.")
else:
    print("Loaded from cache.")
```

The cache is stored in `data/processed/chart_cache.db` (SQLite). The cache key is `SHA-256(birth_json + options_json)`.

### Report repository

```python
from vedic_ai.storage.repository import save_report, load_report, list_reports

# Save
report_id = save_report(report)
print("Saved:", report_id)

# List all saved reports
for entry in list_reports():
    print(entry["report_id"], entry["birth_name"], entry["scope"], entry["created_at"])

# Load by ID
loaded = load_report(report_id)
print(loaded.sections[0].summary)
```

---

## 10. Evaluation and reproducibility

### Reproduce any report

```python
from vedic_ai.utils.repro import build_reproducibility_manifest

manifest = build_reproducibility_manifest(report)
print(manifest)
# {
#   "schema_version": "1.0.0",
#   "model_name": "qwen2.5:14b",
#   "generated_at": "2026-04-30T10:30:00+00:00",
#   "packages": {"pydantic": "2.x.x", "vedic-ai": "0.1.0", ...},
#   "corpus_hash": "a3f1b2c4d5e6f789",
#   "sections": ["career"]
# }
```

### Benchmark against labeled cases

```python
from vedic_ai.evaluation.dataset import load_evaluation_set
from vedic_ai.evaluation.runner import run_regression_benchmark, save_benchmark_results

ev_set = load_evaluation_set("data/golden/eval_set_v1.json")

# Generate one report per case (same order as ev_set.cases)
reports = []
for case in ev_set.cases:
    r = run_prediction_pipeline(birth=..., scope=case.scope, llm_client=llm)
    reports.append(r)

summary = run_regression_benchmark(ev_set, "qwen2.5:14b", reports)
print(f"Passed: {summary.passed}/{summary.total_cases}")
print(f"Evidence coverage: {summary.mean_evidence_coverage:.0%}")
print(f"Keyword hit rate:  {summary.mean_keyword_hit_rate:.0%}")

save_benchmark_results(summary, "data/golden/benchmark_latest.json")
```

---

## 11. Common issues

### `birth_datetime must be timezone-aware`
Add an offset to the datetime string: `"1990-04-05T10:30:00+05:30"` (not `"1990-04-05T10:30:00"`).

### `LLM setup failed; falling back to dry-run`
Ollama is not running or the model is not pulled. Fix:
```bash
sudo systemctl start ollama
ollama pull qwen2.5:14b
curl http://localhost:11434/api/tags    # should return model list
```

### `RuleError: unknown feature namespace 'X'`
The YAML rule uses a feature path whose top-level namespace is not registered in `rule_loader.py`. Valid namespaces: `planets`, `houses`, `yogas`, `lagna`, `aspects`, `nakshatra_ascendant`, `metadata`, `timing`, `transit`.

### Report summary is `"Dry-run interpretation for scope 'career'."`
Either `dry_run=True` was passed or the LLM client was not initialised. Pass a `LocalLLMClient` and set `dry_run=False`.

### Very slow LLM response (CPU-only)
Expected: `qwen2.5:14b` runs at ~3–5 tokens/sec on CPU. A 500-token report takes ~2 minutes. `timeout_seconds` in `configs/models.yaml` defaults to 600 — increase if needed. To keep the model warm and avoid cold-start delays:
```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:14b","keep_alive":"1h","prompt":"","stream":false}'
```

### `Read timed out` calling Ollama
Increase `timeout_seconds` in `configs/models.yaml`:
```yaml
ollama:
  timeout_seconds: 1200   # 20 minutes for heavy CPU load
```

### Warning: "unauthenticated requests to the HF Hub"
This is suppressed automatically by the CLI (`HF_HUB_OFFLINE=1`). If you see it when calling the pipeline directly from Python, set the env var yourself:
```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

### Retrieval returns no passages
The FAISS index has not been built yet. Run the corpus ingestion pipeline once (see [Section 4b](#4b-python-api-direct), "With retrieval").

### `EngineError: pyswisseph is not installed`
```bash
pip install pyswisseph
```

### `ImportError: faiss-cpu ... not installed`
```bash
pip install faiss-cpu sentence-transformers
```

---

## Quick-reference cheat sheet

```bash
# ── FIRST-TIME SETUP ──────────────────────────────────────────────────────────
pip install -e ".[dev,engine,retrieval,llm,api]"
vedic-ai build-index                          # embed corpus (run once)

# ── WEB UI ───────────────────────────────────────────────────────────────────
vedic-ai serve                                # http://127.0.0.1:8000
vedic-ai serve --host 0.0.0.0 --port 8080    # LAN accessible

# ── CLI PREDICTIONS ───────────────────────────────────────────────────────────
# All three scopes — full LLM run
vedic-ai predict "1972-08-27T19:45:00+05:30" 21.15 79.08 --name "Rahul"

# Single scope
vedic-ai predict "1990-04-05T10:30:00+05:30" 28.61 77.21 --scope career

# Instant dry-run (no LLM, good for debugging rules)
vedic-ai predict "1990-04-05T10:30:00+05:30" 28.61 77.21 --dry-run

# Save to file
vedic-ai predict "1985-11-15T06:00:00+05:30" 19.07 72.87 \
    --scope personality -o report.json

# ── CORPUS MANAGEMENT ─────────────────────────────────────────────────────────
vedic-ai corpus-info                          # show manifest + index status
vedic-ai build-index --force                  # rebuild after adding new texts
vedic-ai search "Sun in 10th house career"    # semantic search
vedic-ai search "Atmakaraka Jaimini" --top-k 3

# ── REST API ──────────────────────────────────────────────────────────────────
curl http://localhost:8000/health
curl http://localhost:8000/predictions/scopes

curl -X POST http://localhost:8000/predictions \
  -H "Content-Type: application/json" \
  -d '{"birth_datetime":"1990-04-05T10:30:00+05:30","latitude":28.61,"longitude":77.21,"scope":"all","dry_run":true}'

curl -X POST http://localhost:8000/charts/compute \
  -H "Content-Type: application/json" \
  -d '{"birth_datetime":"1990-04-05T10:30:00+05:30","latitude":28.61,"longitude":77.21}'

# ── LLM ──────────────────────────────────────────────────────────────────────
sudo systemctl start ollama
ollama pull qwen2.5:14b
# Keep model warm (avoids cold-start delay):
curl http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:14b","keep_alive":"1h","prompt":"","stream":false}'

# ── TESTS AND DEBUG ───────────────────────────────────────────────────────────
pytest tests/unit -q
pytest tests/ -q
VEDIC_AI__LOG__LEVEL=DEBUG vedic-ai predict "1990-04-05T10:30:00+05:30" 28.61 77.21
```
