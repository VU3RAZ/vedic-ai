# Vedic AI

A fully local, privacy-first Vedic astrology analysis and prediction framework.

Accepts birth data, computes a canonical Jyotish horoscope, evaluates a rule corpus against the chart's derived features, retrieves supporting textual evidence from a local knowledge base, and generates grounded natural-language predictions through a local LLM — with every claim linked to chart facts, triggered rules, and source passages.

## Status

**All 13 phases complete — 538 tests passing.**

## Canonical pipeline

```
Birth Data
  → Calculation Engine       (swisseph + kerykeion adapters)
  → Canonical ChartBundle    (Pydantic v2, schema-versioned JSON)
  → Feature Extractor        (strengths, lordships, aspects, yogas, nakshatras)
  → Rule Evaluator           (YAML micro-DSL, 4 rule scopes, conflict resolution)
  → Retrieval Layer          (FAISS + sentence-transformers, all-MiniLM-L6-v2)
  → Prompt Builder           (structured, evidence-linked prompt contract)
  → Local LLM                (Ollama / LM Studio — qwen2.5:14b by default)
  → Structured Report        (PredictionReport with evidence refs)
  → Timing Overlay           (Vimshottari dasha + transits, ForecastReport)
  → Evaluation & Hardening   (metrics, SQLite cache, reproducibility manifest)
```

## Implementation status

| Phase | Description                          | Status   | Key modules |
|-------|--------------------------------------|----------|-------------|
| 0     | Project bootstrap                    | ✅ Done  | `core/config`, `core/logging`, `cli/main` |
| 1     | Domain schemas and JSON contract     | ✅ Done  | `domain/` — BirthData, ChartBundle, RuleTrigger, PredictionReport |
| 2     | Calculation engine adapter layer     | ✅ Done  | `engines/swisseph_adapter`, `engines/normalizer` |
| 3     | Derived feature extraction           | ✅ Done  | `features/` — strength, lordships, aspects, nakshatra, yogas |
| 4     | Rule engine and interpretation triggers | ✅ Done | `core/rule_evaluator`, `data/corpus/rules/*.yaml` |
| 5     | Corpus ingestion and retrieval       | ✅ Done  | `retrieval/` — FAISS, sentence-transformers, chunker |
| 6     | Prompt contracts and LLM wrapper     | ✅ Done  | `llm/local_client`, `llm/prompt_builder`, `llm/output_parser` |
| 7     | Prediction orchestrator (MVP gate)   | ✅ Done  | `orchestration/pipeline`, `orchestration/prediction_service` |
| 8     | Timing engine (dasha + transits)     | ✅ Done  | `features/dasha_features`, `features/transit_features`, `orchestration/timing_service` |
| 9     | Evaluation framework                 | ✅ Done  | `evaluation/dataset`, `evaluation/metrics`, `evaluation/runner` |
| 10    | Fine-tuning data prep                | ✅ Done  | `evaluation/training_data`, `llm/fine_tune_prep`, `scripts/train_lora.py` |
| 11    | FastAPI surface + CLI                | ✅ Done  | `api/app`, `api/routes_chart`, `api/routes_prediction` |
| 12    | Hardening (cache, repo, repro)       | ✅ Done  | `storage/cache`, `storage/repository`, `utils/repro` |

## Quick start

### Install

```bash
git clone https://github.com/VU3RAZ/vedic-ai.git
cd vedic-ai
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,engine,retrieval,llm,api]"
```

### Run tests

```bash
pytest tests/unit -q          # fast, no external deps
pytest tests/integration -q   # requires corpus index built
pytest tests/ -q              # full suite (538 tests)
```

### CLI — generate a prediction report

```bash
# Dry run (no LLM call)
vedic-ai predict "1990-04-05T10:00:00+05:30" 28.6 77.2 \
    --name "Test Native" --scope career --dry-run

# With local LLM (Ollama must be running)
vedic-ai predict "1990-04-05T10:00:00+05:30" 28.6 77.2 \
    --name "Test Native" --scope career

# Save report to file
vedic-ai predict "1990-04-05T10:00:00+05:30" 28.6 77.2 \
    --scope personality --output report.json
```

### API server

```bash
uvicorn vedic_ai.api.app:create_api_app --factory --reload
# → http://localhost:8000/health
# → POST http://localhost:8000/predictions
# → POST http://localhost:8000/charts/compute
```

## Repository layout

```
configs/
  app.yaml              Application settings
  models.yaml           LLM backend (ollama / lm_studio) and model config
  astrology.yaml        Engine, ayanamsa, house system defaults
  retrieval.yaml        Vector store backend (faiss / chroma) and chunk size

data/
  corpus/
    rules/              YAML rule files: career, personality, relationships, timing
    texts/              Seed Jyotish corpus (BPHS, Phaladeepika, nakshatra notes)
  fixtures/             Three sample chart JSON fixtures (A, B, C)
  golden/               eval_set_v1.json — labeled evaluation cases

scripts/
  train_lora.py         SFT training data export entrypoint

src/vedic_ai/
  core/                 Config loader, logging, exceptions, rule engine
  domain/               Pydantic schemas — BirthData, ChartBundle, RuleTrigger,
                        PredictionReport, ForecastReport, DashaPeriod, …
  engines/              SwissEphAdapter (primary), KerykeionAdapter (stub),
                        vimshottari (Mahadasha + Antardasha), normalizer
  features/             core_features, strength, lordships, aspects,
                        nakshatra_features, dasha_features, transit_features
  retrieval/            corpus_loader, chunker, embedder (all-MiniLM-L6-v2),
                        vector_store (FAISS), retriever
  llm/                  LLMClient protocol, LocalLLMClient (Ollama / LM Studio),
                        prompt_builder, output_parser, fine_tune_prep
  orchestration/        pipeline (end-to-end), prediction_service,
                        evidence_builder, timing_service (forecast)
  evaluation/           dataset, metrics, runner (benchmark), training_data
  storage/              cache (SQLite ChartBundle), repository (PredictionReport)
  utils/                repro (reproducibility manifest)
  api/                  FastAPI app, routes_chart, routes_prediction
  cli/                  main (Typer), commands_predict

tests/
  unit/                 Fast isolated tests (no network, no DB)
  integration/          Pipeline, retrieval, LLM contract, timing, evaluation
  regression/           Golden snapshot comparisons
  e2e/                  CLI (Typer runner) and API (TestClient) end-to-end tests
```

## Technology stack

| Layer | Library |
|---|---|
| Language | Python 3.11+ |
| Schemas | Pydantic v2 |
| CLI | Typer |
| Logging | structlog (JSON mode optional) |
| Astrology engine | pyswisseph (Moshier built-in ephemeris, Lahiri ayanamsa) |
| Secondary adapter | kerykeion (stub, in-progress) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (384-dim, CPU) |
| Vector store | FAISS `IndexFlatIP` (cosine similarity) |
| LLM serving | Ollama (`qwen2.5:14b`, CPU-only) or LM Studio (OpenAI-compatible) |
| LLM output repair | json5 → regex extract → minimal fallback |
| API | FastAPI + uvicorn |
| Cache / storage | SQLite (standard library) |
| Test runner | pytest |

## LLM configuration

The active model is configured in `configs/models.yaml`:

```yaml
llm:
  backend: ollama         # or lm_studio
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
    timeout_seconds: 120
  temperature: 0.2
  max_tokens: 2048
```

Ollama must be running (`sudo systemctl start ollama`). The model is pulled once:

```bash
ollama pull qwen2.5:14b
```

Expected throughput on CPU-only hardware: ~3–5 tokens/sec. A 500-token report takes roughly 2 minutes.

## Core design principles

1. **Deterministic before generative** — all astrology calculations come from the engine layer, never the LLM.
2. **Structured data everywhere** — all intermediate artifacts are typed Pydantic objects or JSON.
3. **Local-first privacy** — chart data, embeddings, rule files, and prompts stay on-device.
4. **RAG before fine-tuning** — retrieval-augmented generation first; fine-tuning only after benchmarks are stable.
5. **Traceable predictions** — every claim links to chart facts, triggered rules, and retrieved passages.
6. **Phase-gated development** — each phase has typed tests and checkpoints before the next begins.

## Rule file format

Rules live in `data/corpus/rules/*.yaml`. Each rule is a small typed object:

```yaml
- rule_id: C001
  name: Sun in 10th House — Career Prominence
  scope: career          # career | personality | relationships | timing
  weight: 0.75           # 0.0–1.0
  conditions:
    - feature: planets.Sun.house
      op: eq             # eq | ne | gt | lt | in | not_in | contains
      value: 10
  explanation_template: >-
    Sun placed in the 10th house confers prominence and authority in
    professional life, often in government or leadership roles.
  source_refs:
    - "BPHS 24.5"
  conflict_policy: merge  # merge | override | defer
```

Feature paths use dot notation into the extracted feature dict:
`planets.<Graha>.house`, `houses.<1-12>.lord_in_kendra`, `yogas.gajakesari`,
`timing.mahadasha.lord`, `transit.<Graha>.house`, etc.

## Evaluation

Run the benchmark against a labeled evaluation set:

```python
from vedic_ai.evaluation.dataset import load_evaluation_set
from vedic_ai.evaluation.runner import run_regression_benchmark

ev_set = load_evaluation_set("data/golden/eval_set_v1.json")
# generate reports for each case, then:
summary = run_regression_benchmark(ev_set, "qwen2.5:14b", reports)
print(summary.mean_evidence_coverage, summary.mean_keyword_hit_rate)
```

## Reproducibility

Every report can be accompanied by a manifest capturing the exact versions and content hashes used:

```python
from vedic_ai.utils.repro import build_reproducibility_manifest
manifest = build_reproducibility_manifest(report)
# → schema_version, model_name, package versions, corpus_hash, section list
```

## License

MIT — see [LICENSE](LICENSE) if present, otherwise consider this open-source for personal and research use.

---

See `vedic_ai.md` for the full 13-phase specification and `FIXES_AND_CONFIG.md` for environment and bug-fix notes.
