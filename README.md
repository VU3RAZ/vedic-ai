# Vedic AI

A local-first Vedic astrology analysis and prediction framework with a browser-based UI.

Accepts birth data, computes a canonical Jyotish horoscope using Swiss Ephemeris, evaluates a deterministic rule corpus, retrieves supporting passages from a 1.5 M-char knowledge base (BPHS Santhanam Vols 1 & 2, Jaimini Sutras, and more), and uses an LLM **only for synthesis** — weaving pre-computed engine findings into readable narrative. Every claim links to triggered rules and source passages; the LLM never re-derives positions, dashas, or remedies. Supports local inference (Ollama / LM Studio / llama.cpp) and cloud inference (Gemini free tier). Comes with a single-command web server.

## Status

**All 13 phases complete — 353 unit tests passing.**

## What's new (2026-05)

- **12-Bhava prediction analysis** — select "All 12 Bhavas" (or any individual bhava) as the prediction scope. Each bhava runs its own rule set (6 rules each, BPHS citations), injects a **BHAVA ACTIVATION** block into the LLM prompt (dasha activation score, aspects/drishti received, current transiting planets), and renders in a responsive card grid with activation badge (HIGH / MODERATE / LOW) and transit badges.
- **Bhava-aware prompt builder** — when scope is `bhava_N`, the prompt automatically: (a) focuses drishti on the target bhava + its trines and opposition, (b) injects the full dasha activation analysis (mahadasha/antardasha lord vs. bhava lord, occupants, drishti received), (c) maps to bhava-specific divisional charts (D2→H2, D10→H10, D9/D7→H7, etc.).
- **Gemini backend in web UI** — Gemini now appears as a selectable backend in the LLM Backend dropdown (alongside Ollama / LM Studio / llama.cpp). Selecting it swaps the Base URL field for an API Key field; results route to a dedicated **✨ Gemini** prediction tab. Key can also be supplied per-request without restarting the server.
- **Gochara / Transit engine** — full rule-based transit analysis: Gochara house effects (BPHS Ch.85–87, Phaladeepika Ch.26), Vedha obstruction table, Sadhe Sati / Ashtama Shani / Kantaka Shani detection, Guru Chandala and Mars–Saturn special alerts, dasha-transit synergy, remedies with classical citations (Mantra Mahodadhi, BPHS Ch.88, Agni Purana). `POST /transits/compute` — no LLM required.
- **Gochara tab in Web UI** — enter transit date → instant rule-based findings: planet matrix, Vedha cards, Sadhe Sati status, special alerts, per-planet remedies with Vedic mantra (RV/YV/AV verse) and beeja mantra source citations.
- **LLM synthesis-only refactor** — the LLM no longer receives raw chart longitudes or re-derives positions. It receives only pre-computed ENGINE FINDINGS (planet table, house table, yogas, dasha strength, varga analysis, triggered rules, and optional Gochara context) and is explicitly prohibited from re-deriving positions, inventing remedies, or contradicting engine tone.
- **Transit context in predictions** — pass `transit_datetime` to `POST /predictions` or `run_prediction_pipeline()` and the Gochara engine output is injected as a structured context block into the LLM synthesis prompt.
- **LLM Debug tab** — ⚙ tab alongside Standard / Raman predictions; shows the full prompt sent to the LLM and the raw response, collapsible per scope.
- **Graha Drishti** — classical aspect computation with strength fractions (full / 3/4 / 1/2) per graha
- **Rashi Drishti (Jaimini)** — sign-to-sign aspects; moveable→fixed, fixed→moveable, dual→dual
- **Full Drishti Matrix** — per-house view combining both drishti types with double-aspect detection
- **Bhava Sandhi / Madhya** — per-planet cusp-proximity and strength-zone classification
- **Scope-aware Varga Analysis** — D9/D10/D3/D7/D12: lagna lord placement, dignity stats, karaka positions, varga yogas

## Canonical pipeline

```
Birth Data
  → Calculation Engine       (SwissEphAdapter — pyswisseph + Moshier ephemeris, Lahiri ayanamsa)
  → Canonical ChartBundle    (Pydantic v2, schema-versioned JSON)
  → Feature Extractor        (strengths, lordships, graha+rashi drishti, yogas, sandhi, nakshatras,
                               varga analysis D3/D7/D9/D10/D12, dasha timing)
  → Rule Evaluator           (YAML micro-DSL, 16 rule scopes: 4 traditional + 12 bhava, conflict resolution)
  → Gochara Engine           (transit analysis — BPHS/Phaladeepika/SC rules, Vedha, Sadhe Sati,
                               special alerts, remedies with classical citations — no LLM)
  → Bhava Activation         (per-bhava dasha activation score + transit pressure from Gochara engine)
  → Retrieval Layer          (FAISS + sentence-transformers, 3 054 chunks, all-MiniLM-L6-v2)
  → Prompt Builder           (synthesis-only: ENGINE FINDINGS + BHAVA ACTIVATION + optional Gochara
                               context; LLM prohibited from re-deriving positions or remedies)
  → LLM — Local or Cloud     (Ollama / LM Studio / llama.cpp  OR  Gemini free tier)
  → Structured Report        (PredictionReport — sections + llm_debug for inspection)
  → Timing Overlay           (Vimshottari dasha + transits, ForecastReport)
  → Evaluation & Hardening   (metrics, SQLite cache, reproducibility manifest)
  → Web UI                   (FastAPI + single-file HTML — Chart / Drishti / Vargas / Raman-Analysis /
                               Gochara / Standard / Raman / 12 Bhavas / ✨ Gemini / ⚙ Debug tabs)
```

## Quick start

**Prerequisites:** Python 3.11+, internet access for first run (downloads ~90 MB embedding model once).

### Option A — Make (recommended)

```bash
git clone https://github.com/VU3RAZ/vedic-ai.git
cd vedic-ai
make install        # creates .venv and installs all dependencies
make build-index    # downloads embedding model + builds FAISS index (one-time, needs internet)
make serve          # http://127.0.0.1:8000
```

All subsequent runs work fully offline — the embedding model is cached locally after the first `build-index`.

### Option B — Manual

```bash
git clone https://github.com/VU3RAZ/vedic-ai.git
cd vedic-ai
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
# or equivalently:
pip install -e ".[dev,engine,retrieval,llm,api]"

# Build the retrieval index (one-time — downloads all-MiniLM-L6-v2 ~90 MB on first run)
vedic-ai build-index
# → 9 sources — 1 525 642 chars — 3 054 vectors written to data/processed/faiss.index

# Start the web server
vedic-ai serve                # http://127.0.0.1:8000
vedic-ai serve --port 8080    # custom port
```

Open your browser at the printed URL. Fill in birth data, click **Compute Chart** for the natal chart + dashas, or **Generate Prediction** for the full LLM-powered reading.

### Option C — CLI predict

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

> **Note:** Predictions also require a local LLM server — see [LLM configuration](#llm-configuration-configsmodelsyaml) below. Chart computation (`vedic-ai serve` + **Compute Chart** button) works without an LLM.

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
| GET | `/predictions/scopes` | Returns supported scope names |
| POST | `/predictions` | Full prediction pipeline (LLM synthesis) |
| POST | `/charts/compute` | Compute chart only (no prediction) |
| POST | `/transits/compute` | Gochara transit analysis (no LLM — instant) |
| GET | `/docs` | Interactive Swagger UI |

**`POST /predictions` body:**
```json
{
  "birth_datetime": "1972-08-27T19:45:00+05:30",
  "latitude": 21.15,
  "longitude": 79.08,
  "name": "Rahul",
  "scope": "bhava_all",
  "dry_run": false,
  "transit_datetime": "2026-05-04T12:00:00+05:30",
  "llm_backend": "gemini",
  "llm_api_key": "AIza..."
}
```

**`scope` values:**

| Value | Runs |
|---|---|
| `"all"` | All 4 traditional scopes (personality, career, relationships, health) |
| `"personality"` / `"career"` / `"relationships"` / `"health"` | Single traditional scope |
| `"bhava_all"` | All 12 bhava scopes |
| `"bhava_1"` … `"bhava_12"` | Single bhava (H1 Lagna through H12 Vyaya) |

`transit_datetime` (optional): triggers the Gochara engine; its findings are injected into every scope's prompt. The LLM synthesizes natal + transit without re-deriving positions.  
`llm_api_key` (optional): Gemini API key — overrides `GEMINI_API_KEY` env var and `configs/models.yaml`.

**`POST /transits/compute` body:**
```json
{
  "birth_datetime": "1972-08-27T19:45:00+05:30",
  "birth_latitude": 21.15,
  "birth_longitude": 79.08,
  "transit_datetime": "2026-05-04T12:00:00+05:30"
}
```
Returns planet-by-planet Gochara results, Vedha status, Sadhe Sati phase, special alerts, remedies with classical citations — all rule-based, no LLM.

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
| 2 | Calculation engine | ✅ | `engines/swisseph_adapter`, `engines/normalizer`, `engines/varga` |
| 3 | Feature extraction | ✅ | `features/` — strength, lordships, aspects, nakshatra, yogas |
| 3a | Drishti (graha + rashi) | ✅ | `features/drishti` — full drishti matrix with double-aspect detection |
| 3b | Bhava sandhi / madhya | ✅ | `features/sandhi` — cusp proximity, bhava madhya zone |
| 3c | Varga analysis | ✅ | `features/varga_analysis` — D3/D7/D9/D10/D12 scope-aware analysis |
| 4 | Rule engine | ✅ | `core/rule_evaluator`, `data/corpus/rules/*.yaml` |
| 5 | Corpus ingestion & retrieval | ✅ | `retrieval/` — FAISS, sentence-transformers, chunker |
| 6 | Prompt contracts & LLM wrapper | ✅ | `llm/local_client`, `llm/cloud_client` (Gemini), `llm/prompt_builder` (synthesis-only), `llm/output_parser` |
| 6a | Gochara transit engine | ✅ | `engines/gochara` — BPHS/Phaladeepika/SC rules, Vedha, Sadhe Sati, remedies with citations |
| 7 | Prediction orchestrator | ✅ | `orchestration/pipeline` (Gochara context injection), `orchestration/prediction_service` |
| 8 | Timing engine | ✅ | `features/dasha_features`, `features/transit_features` |
| 9 | Evaluation framework | ✅ | `evaluation/dataset`, `evaluation/metrics`, `evaluation/runner` |
| 10 | Fine-tuning data prep | ✅ | `evaluation/training_data`, `llm/fine_tune_prep` |
| 11 | FastAPI + CLI + Web UI | ✅ | `api/`, `cli/`, `static/index.html` (Chart/Drishti/Vargas/Raman/Gochara/Standard/Raman/12 Bhavas/Gemini/Debug) |
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
    rules/              YAML rule files: career, personality, relationships, health,
                        timing, bhava_01 … bhava_12 (16 scope files, 100+ rules)
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
  engines/              SwissEphAdapter (primary), vimshottari, normalizer, varga
  features/             core_features, strength, lordships, nakshatra, dasha, transit,
                        aspects (graha drishti), drishti (rashi drishti + matrix),
                        sandhi (bhava sandhi/madhya), varga_analysis (D3/D7/D9/D10/D12),
                        bhava_analysis (dasha activation + transit pressure per bhava),
                        jaimini_features (chara karakas, arudha padas, upapada)
  retrieval/            corpus_loader, chunker, embedder, vector_store, retriever
  llm/                  LocalLLMClient (Ollama/LM Studio/llama.cpp), GeminiClient (cloud),
                        prompt_builder (synthesis-only, Gochara context block), output_parser
  orchestration/        pipeline, prediction_service, evidence_builder, timing_service
  evaluation/           dataset, metrics, runner, training_data
  storage/              cache (SQLite), repository
  utils/                repro (reproducibility manifest)
  api/                  FastAPI app, routes_chart, routes_prediction, routes_transit
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
| LLM — local | Ollama / LM Studio / llama.cpp — selectable in UI or `configs/models.yaml` |
| LLM — cloud | Google Gemini via `google-genai` SDK (free tier 1,500 req/day) |
| API | FastAPI + uvicorn |
| Web UI | Vanilla HTML/CSS/JS (no npm, no CDN, fully offline) |
| Cache / storage | SQLite |
| Test runner | pytest |

## LLM configuration (`configs/models.yaml`)

Four backends supported. Set `backend` to whichever you are using:

```yaml
llm:
  backend: gemini         # ollama | lm_studio | llamacpp | gemini
  gemini:
    model: "gemini-flash-lite-latest"   # free tier: 1,500 req/day, ~2 s/request
    max_tokens: 4096
    timeout_seconds: 60
    api_key: ""           # or set GEMINI_API_KEY env var
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:14b"
    timeout_seconds: 600
  lm_studio:
    base_url: "http://localhost:1234"
    model: "local-model"
    timeout_seconds: 600
  llamacpp:
    base_url: "http://localhost:8080"
    model: "default"
    timeout_seconds: 600
  temperature: 0.2
  max_tokens: 4096
```

> `configs/models.yaml` is gitignored — safe to put the API key there.

**Gemini (recommended — free tier):**
1. Get a free key at https://aistudio.google.com/apikey
2. Paste it into `configs/models.yaml` under `gemini.api_key`, or `export GEMINI_API_KEY=…`
3. `pip install google-genai`
4. Set `backend: gemini`

**Ollama** — start server and pull model once:
```bash
sudo systemctl start ollama
ollama pull qwen2.5:14b
```

**LM Studio** — load a GGUF model in the LM Studio app, enable the local server on port 1234.

**llama.cpp** — build `llama-server` and point it at a GGUF file:
```bash
llama-server --model /path/to/model.gguf --host 0.0.0.0 --port 8080 --ctx-size 4096
```

The backend can also be switched **per-request** from the web UI without restarting the server.

Expected throughput: Gemini ~2 s/scope · Local CPU ~2–8 min/scope.

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

Valid feature namespaces: `planets`, `houses`, `yogas`, `lagna`, `aspects`, `drishti`, `sandhi`, `vargas`, `varga_analysis`, `nakshatra_ascendant`, `timing`, `transit`.

## 12-Bhava rule scopes

Each of the 12 houses has its own rule file (`data/corpus/rules/bhava_01.yaml` … `bhava_12.yaml`). Use scope names `bhava_1` through `bhava_12`. Rules follow the same format as traditional scopes.

| Bhava | Scope name | Domain |
|---|---|---|
| 1 | `bhava_1` | Lagna — self, constitution, appearance |
| 2 | `bhava_2` | Dhana — wealth, speech, family |
| 3 | `bhava_3` | Sahaja — siblings, courage, communication |
| 4 | `bhava_4` | Sukha — mother, home, property, happiness |
| 5 | `bhava_5` | Putra — children, intelligence, creativity |
| 6 | `bhava_6` | Ari — enemies, disease, debt, service |
| 7 | `bhava_7` | Kalatra — spouse, partnerships, business |
| 8 | `bhava_8` | Ayu — longevity, transformation, occult |
| 9 | `bhava_9` | Dharma — father, guru, fortune, religion |
| 10 | `bhava_10` | Karma — career, status, authority |
| 11 | `bhava_11` | Labha — gains, income, elder siblings |
| 12 | `bhava_12` | Vyaya — losses, liberation, foreign lands |

When a bhava scope runs, the prompt builder automatically:
- Injects a **BHAVA ACTIVATION** block with dasha lord activation score and current transits through that house
- Focuses the drishti section on the target bhava + its trines and opposition
- Routes to bhava-specific divisional charts (D10 for bhava_10, D9/D7 for bhava_7, etc.)

## License

MIT — open-source for personal and research use.

---

See [`docs/usage_guide.md`](docs/usage_guide.md) for the complete walkthrough.
See [`vedic_ai.md`](vedic_ai.md) for the full 13-phase specification.
