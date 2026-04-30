# Vedic AI

A fully local, privacy-first Vedic astrology analysis and prediction framework with a browser-based UI.

Accepts birth data, computes a canonical Jyotish horoscope using Swiss Ephemeris, evaluates a rule corpus, retrieves supporting passages from a 1.5 M-char local knowledge base (BPHS Santhanam Vols 1 & 2, Jaimini Sutras, and more), and generates grounded natural-language predictions through a local LLM — with every claim linked to chart facts, triggered rules, and source passages. Comes with a single-command web server so you can use the full framework from any browser.

## Status

**All 13 phases complete — 538 tests passing.**

## Canonical pipeline

```
Birth Data
  → Calculation Engine       (SwissEphAdapter — pyswisseph + Moshier ephemeris, Lahiri ayanamsa)
  → Canonical ChartBundle    (Pydantic v2, schema-versioned JSON)
  → Feature Extractor        (strengths, lordships, aspects, yogas, nakshatras, dasha timing)
  → Rule Evaluator           (YAML micro-DSL, 4 rule scopes, conflict resolution)
  → Retrieval Layer          (FAISS + sentence-transformers, 3 054 chunks, all-MiniLM-L6-v2)
  → Prompt Builder           (structured, evidence-linked prompt contract)
  → Local LLM                (Ollama / LM Studio — qwen2.5:14b by default)
  → Structured Report        (PredictionReport with evidence refs — personality / career / relationships)
  → Timing Overlay           (Vimshottari dasha + transits, ForecastReport)
  → Evaluation & Hardening   (metrics, SQLite cache, reproducibility manifest)
  → Web UI                   (FastAPI + single-file HTML frontend, served at http://localhost:8000)
```

## Quick start

### Install

```bash
git clone https://github.com/VU3RAZ/vedic-ai.git
cd vedic-ai
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,engine,retrieval,llm,api]"
```

### Build the retrieval index (one-time)

```bash
vedic-ai build-index
# → 9 sources — 1 525 642 chars — 3 054 vectors embedded in data/processed/faiss.index
```

### Option A — Web UI

```bash
vedic-ai serve                # http://127.0.0.1:8000
vedic-ai serve --port 8080    # custom port
```

Open your browser at the printed URL. Fill in birth data, click **Compute Chart** for the natal chart + dashas, or **Generate Prediction** for the full LLM-powered reading.

### Option B — CLI

```bash
# All three scopes (personality + career + relationships) — full LLM run
vedic-ai predict "1972-08-27T19:45:00+05:30" 21.15 79.08 --name "Rahul"

# Single scope, dry-run (no LLM needed — instant)
vedic-ai predict "1972-08-27T19:45:00+05:30" 21.15 79.08 --scope career --dry-run

# Save report to file
vedic-ai predict "1972-08-27T19:45:00+05:30" 21.15 79.08 -o report.json
```

### Run tests

```bash
pytest tests/unit -q          # fast, no external deps
pytest tests/integration -q   # requires corpus index built
pytest tests/ -q              # full suite (538 tests)
```

## CLI reference

```
vedic-ai --help

Commands:
  predict       Generate a prediction report from birth data
  build-index   Ingest corpus, embed chunks, build FAISS index
  corpus-info   Show corpus manifest and index status
  search        Semantic search the corpus index
  serve         Launch the FastAPI + HTML web server
  info          Show resolved configuration
```

### `predict`

```
vedic-ai predict <DATETIME> <LAT> <LON> [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--scope` / `-s` | *(all three)* | `personality`, `career`, or `relationships`. Omit to run all. |
| `--name` / `-n` | — | Native's name |
| `--dry-run` | off | Skip LLM; return evidence-only report (instant) |
| `--no-rag` | off | Disable RAG retrieval |
| `--top-k` / `-k` | 5 | Number of passages to retrieve |
| `--output` / `-o` | stdout | Write JSON report to file |

### `build-index`

```bash
vedic-ai build-index                  # ingest data/corpus/texts/, write to data/processed/
vedic-ai build-index --force          # rebuild even if index exists
vedic-ai build-index --chunk-size 800 # custom chunk size
```

### `search`

```bash
vedic-ai search "Sun in 10th house career authority"
vedic-ai search "Atmakaraka Jaimini charakaraka" --top-k 3
vedic-ai search "marriage spouse seventh house Venus"
```

### `serve`

```bash
vedic-ai serve                        # http://127.0.0.1:8000
vedic-ai serve --host 0.0.0.0 --port 8080   # accessible on LAN
vedic-ai serve --reload               # auto-reload (development)
```

## REST API

Start the server with `vedic-ai serve`, then:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Web UI (HTML frontend) |
| GET | `/health` | Liveness check |
| GET | `/predictions/scopes` | Returns `["personality","career","relationships"]` |
| POST | `/predictions` | Full prediction pipeline |
| POST | `/charts/compute` | Compute chart only (no prediction) |
| GET | `/docs` | Interactive Swagger UI |

**`POST /predictions` body:**
```json
{
  "birth_datetime": "1972-08-27T19:45:00+05:30",
  "latitude": 21.15,
  "longitude": 79.08,
  "name": "Rahul",
  "scope": "all",
  "dry_run": false
}
```
`scope` accepts `"all"` (default), `"personality"`, `"career"`, or `"relationships"`.

**`POST /charts/compute` body:**
```json
{
  "birth_datetime": "1972-08-27T19:45:00+05:30",
  "latitude": 21.15,
  "longitude": 79.08,
  "ayanamsa": "lahiri",
  "house_system": "whole_sign"
}
```

## Corpus

9 knowledge sources — 1 525 642 chars — 3 054 retrieval chunks:

| Source | Content |
|---|---|
| BPHS Ch. 15 | Planets in the Lagna |
| BPHS Ch. 16 | Planets in houses 2–6 |
| **BPHS Ch. 17–22** | Planets in houses 7–12 (new) |
| BPHS Ch. 23 | Seventh house (marriage) |
| BPHS Ch. 24 | Tenth house (career) |
| BPHS Ch. 35 | Yogas |
| **BPHS Santhanam Vol 1** | Full BPHS translation Ch. 1–45 (new) |
| **BPHS Santhanam Vol 2** | Full BPHS translation Ch. 46+ — all dasa systems (new) |
| **Jaimini Sutras** | Chara Karakas, Karakamsha, Rasi Aspects, Argala, Chara Dasa, Upapada (new) |

To add your own texts:
1. Drop a `.txt` file in `data/corpus/texts/` with YAML frontmatter:
   ```
   ---
   source: MY_TEXT
   chapter: 1
   language: en
   ---
   Content here...
   ```
2. Run `vedic-ai build-index --force`.

## Implementation status

| Phase | Description | Status | Key modules |
|---|---|---|---|
| 0 | Project bootstrap | ✅ | `core/config`, `core/logging`, `cli/main` |
| 1 | Domain schemas | ✅ | `domain/` — BirthData, ChartBundle, PredictionReport |
| 2 | Calculation engine | ✅ | `engines/swisseph_adapter`, `engines/normalizer` |
| 3 | Feature extraction | ✅ | `features/` — strength, lordships, aspects, nakshatra, yogas |
| 4 | Rule engine | ✅ | `core/rule_evaluator`, `data/corpus/rules/*.yaml` |
| 5 | Corpus ingestion & retrieval | ✅ | `retrieval/` — FAISS, sentence-transformers, chunker |
| 6 | Prompt contracts & LLM wrapper | ✅ | `llm/local_client`, `llm/prompt_builder`, `llm/output_parser` |
| 7 | Prediction orchestrator | ✅ | `orchestration/pipeline`, `orchestration/prediction_service` |
| 8 | Timing engine | ✅ | `features/dasha_features`, `features/transit_features` |
| 9 | Evaluation framework | ✅ | `evaluation/dataset`, `evaluation/metrics`, `evaluation/runner` |
| 10 | Fine-tuning data prep | ✅ | `evaluation/training_data`, `llm/fine_tune_prep` |
| 11 | FastAPI + CLI + Web UI | ✅ | `api/`, `cli/`, `static/index.html` |
| 12 | Hardening (cache, repo, repro) | ✅ | `storage/cache`, `storage/repository`, `utils/repro` |

## Repository layout

```
configs/
  app.yaml              Application settings (log level, engine, ayanamsa)
  models.yaml           LLM backend (ollama / lm_studio), model, timeout
  astrology.yaml        Engine defaults
  retrieval.yaml        Vector store backend, chunk size, top_k

data/
  corpus/
    rules/              YAML rule files: career, personality, relationships, timing
    texts/              Jyotish corpus (BPHS Vols 1+2, Jaimini, chapter extracts)
  fixtures/             Three sample chart JSON fixtures
  golden/               eval_set_v1.json — labeled evaluation cases
  processed/
    corpus/manifest.json  Ingestion manifest (sources, hashes, char counts)
    faiss.index           Binary FAISS index (built by build-index)
    handle.json           Vector index metadata (chunk_ids, model, dim)

src/vedic_ai/
  core/                 Config loader, logging, exceptions, rule engine
  domain/               Pydantic schemas — BirthData, ChartBundle, PredictionReport, …
  engines/              SwissEphAdapter (primary), vimshottari, normalizer
  features/             core_features, strength, lordships, nakshatra, dasha, transit
  retrieval/            corpus_loader, chunker, embedder, vector_store, retriever
  llm/                  LocalLLMClient (Ollama/LM Studio), prompt_builder, output_parser
  orchestration/        pipeline, prediction_service, evidence_builder, timing_service
  evaluation/           dataset, metrics, runner, training_data
  storage/              cache (SQLite), repository
  utils/                repro (reproducibility manifest)
  api/                  FastAPI app, routes_chart, routes_prediction
  cli/                  main, commands_predict, commands_corpus, commands_serve
  static/               index.html — self-contained browser UI

tests/
  unit/                 Fast isolated tests (no network, no DB)
  integration/          Pipeline, retrieval, LLM contract, timing, evaluation
  regression/           Golden snapshot comparisons
  e2e/                  CLI (Typer runner) and API (TestClient) end-to-end
```

## Technology stack

| Layer | Library |
|---|---|
| Language | Python 3.11+ |
| Schemas | Pydantic v2 |
| CLI | Typer |
| Logging | structlog |
| Astrology engine | pyswisseph (Moshier ephemeris, Lahiri ayanamsa) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (384-dim, CPU) |
| Vector store | FAISS `IndexFlatIP` (cosine similarity) |
| LLM serving | Ollama (`qwen2.5:14b`) or LM Studio (OpenAI-compatible) |
| API | FastAPI + uvicorn |
| Web UI | Vanilla HTML/CSS/JS (no npm, no CDN, fully offline) |
| Cache / storage | SQLite |
| Test runner | pytest |

## LLM configuration (`configs/models.yaml`)

```yaml
llm:
  backend: ollama         # or lm_studio
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
    timeout_seconds: 600  # CPU inference can be slow
  temperature: 0.2
  max_tokens: 2048
```

Start Ollama and pull the model once:

```bash
sudo systemctl start ollama
ollama pull qwen2.5:14b
```

Expected throughput (CPU-only): ~3–5 tokens/sec. A 500-token report takes ~2 minutes.

## Design principles

1. **Deterministic before generative** — all astrology calculations come from the engine, never the LLM.
2. **Local-first, offline-capable** — chart data, embeddings, rules, and prompts stay on-device. No HuggingFace Hub calls at runtime.
3. **Structured data everywhere** — all intermediate artifacts are typed Pydantic objects or JSON.
4. **RAG before fine-tuning** — retrieval-augmented generation first; fine-tuning only after benchmarks stabilise.
5. **Traceable predictions** — every claim links to chart facts, triggered rules, and retrieved passages.

## Rule file format

```yaml
- rule_id: C001
  name: Sun in 10th House — Career Prominence
  scope: career
  weight: 0.75
  conditions:
    - feature: planets.Sun.house
      op: eq
      value: 10
  explanation_template: >-
    Sun in the 10th house confers prominence and authority in professional life.
  source_refs:
    - "BPHS 24.5"
  conflict_policy: merge
```

Valid feature namespaces: `planets`, `houses`, `yogas`, `lagna`, `aspects`, `nakshatra_ascendant`, `timing`, `transit`.

## License

MIT — open-source for personal and research use.

---

See [`docs/usage_guide.md`](docs/usage_guide.md) for the complete walkthrough.
See [`vedic_ai.md`](vedic_ai.md) for the full 13-phase specification.
