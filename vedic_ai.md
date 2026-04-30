# Local Vedic AI Framework Specification

## Purpose

This document defines a phased implementation plan for a local-first AI framework that analyzes Vedic horoscopes, computes chart features, retrieves interpretive rules, and generates grounded predictions.

The system should **not** be built as a single end-to-end model that “learns astrology” from raw birth data alone. Instead, it should combine:
- a deterministic astrology calculation engine,
- a structured domain model,
- a local retrieval layer for Jyotish knowledge,
- and a local LLM for natural-language explanation.

This approach is preferred because existing Vedic Python tooling already supports structured calculations such as planetary positions, houses, divisional charts, and dasha outputs, while current RAG guidance suggests retrieval should come before fine-tuning for knowledge-heavy tasks.

---

## Goals

Build a fully local system that can:

- Accept birth details and calculation settings.
- Compute a canonical horoscope representation.
- Represent 12 houses, 12 signs, 27 nakshatras, 9 grahas, and future support for multiple Vargas.
- Extract derived features such as lordships, aspects, strengths, yogas, and timing signals.
- Retrieve relevant Jyotish rules from a local corpus.
- Generate predictions in natural language through a local LLM.
- Attach evidence and reasoning traces to each prediction.
- Expand gradually from D1-only to multi-chart, dasha, transit, and forecasting workflows.

---

## Core principles

1. **Deterministic before generative**  
   All astronomy and astrology calculations must come from a calculation engine or rule layer, not from the LLM.

2. **Structured data everywhere**  
   Intermediate artifacts must be JSON or typed objects, not plain text blobs.

3. **Local-first privacy**  
   All chart data, embeddings, rule files, and prompts should remain local by default.

4. **RAG before fine-tuning**  
   Start with retrieval-augmented generation. Add fine-tuning only after a benchmark suite exists.

5. **Traceable predictions**  
   Every prediction must be linked to chart facts, triggered rules, and retrieved passages.

6. **Phase-gated development**  
   Later phases may only begin after earlier checkpoints and tests pass.

---

## Recommended repository layout

```text
vedic-ai/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── configs/
│   ├── app.yaml
│   ├── models.yaml
│   ├── astrology.yaml
│   └── retrieval.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── corpus/
│   ├── fixtures/
│   └── golden/
├── docs/
│   ├── architecture.md
│   ├── prompting.md
│   ├── evaluation.md
│   └── corpus_policy.md
├── src/
│   └── vedic_ai/
│       ├── __init__.py
│       ├── api/
│       ├── cli/
│       ├── core/
│       ├── domain/
│       ├── engines/
│       ├── features/
│       ├── retrieval/
│       ├── llm/
│       ├── orchestration/
│       ├── storage/
│       ├── evaluation/
│       └── utils/
└── tests/
    ├── unit/
    ├── integration/
    ├── regression/
    └── e2e/
```

---

## Suggested technology stack

- Python 3.11+
- FastAPI
- Pydantic
- SQLite first, PostgreSQL optional later
- FAISS or Chroma for vector retrieval
- sentence-transformers for embeddings
- local model served by Ollama or LM Studio
- astrology engine adapters over libraries such as VedAstro/Python-style tools or similar Jyotish JSON-producing backends

---

## Canonical system pipeline

```text
Birth Data
  -> Calculation Engine
  -> Canonical ChartBundle JSON
  -> Derived Feature Extractor
  -> Rule Evaluator
  -> Retrieval Query Builder
  -> Local Vector Search
  -> Prompt Builder
  -> Local LLM
  -> Structured Prediction Report
  -> Evidence / Trace Layer
```

---

## Phase 0: Project bootstrap

### Objective
Create the repository skeleton, configuration loader, logging, CLI, and test harness.

### Deliverables
- Python package structure
- dependency setup
- config loader
- logging framework
- CLI entrypoint
- formatter/linter/test setup

### Required modules
- `src/vedic_ai/core/config.py`
- `src/vedic_ai/core/logging.py`
- `src/vedic_ai/core/exceptions.py`
- `src/vedic_ai/cli/main.py`
- `tests/unit/test_config.py`
- `tests/unit/test_imports.py`

### Function specifications

#### `load_app_config(config_path: str | None = None) -> AppConfig`
Load application settings, merge environment variables, validate required fields, and return a typed config object.

#### `setup_logging(level: str, json_logs: bool = False) -> logging.Logger`
Initialize structured logging and return the root logger.

#### `register_cli() -> object`
Create the CLI entrypoint and register phase-specific commands.

### Checkpoints
- Repository installs cleanly.
- `--help` works.
- Invalid config fails with a typed error.
- Unit tests run in a clean environment.

### Tests
#### Unit
- Config parsing
- Env override precedence
- Missing required keys
- Logger initialization

#### Integration
- CLI boot with sample config

#### Regression
- Snapshot normalized config output

---

## Phase 1: Domain schemas and JSON contract

### Objective
Create the canonical typed schema for birth data, chart output, derived features, and prediction evidence.

### Deliverables
- Pydantic schemas
- versioned JSON contract
- fixture files
- serializer/deserializer layer

### Required modules
- `src/vedic_ai/domain/birth.py`
- `src/vedic_ai/domain/chart.py`
- `src/vedic_ai/domain/planet.py`
- `src/vedic_ai/domain/house.py`
- `src/vedic_ai/domain/nakshatra.py`
- `src/vedic_ai/domain/dasha.py`
- `src/vedic_ai/domain/prediction.py`
- `tests/unit/test_schema_roundtrip.py`

### Core entities
- `BirthData`
- `GeoLocation`
- `PlanetPlacement`
- `HousePlacement`
- `RasiPlacement`
- `NakshatraPlacement`
- `DivisionalChart`
- `DashaPeriod`
- `TransitSnapshot`
- `RuleTrigger`
- `PredictionEvidence`
- `ChartBundle`

### Minimum ChartBundle contract
- birth metadata
- ayanamsa and engine settings
- D1 chart
- 9 grahas
- 12 houses
- 12 signs
- 27 nakshatras
- optional Vargas
- dashas
- derived features
- provenance metadata

### Function specifications

#### `build_chart_schema_version() -> str`
Return active schema version.

#### `serialize_chart_bundle(bundle: ChartBundle) -> dict`
Convert typed objects to canonical JSON-safe form.

#### `deserialize_chart_bundle(payload: dict) -> ChartBundle`
Validate JSON and parse into typed objects.

#### `validate_chart_bundle(payload: dict) -> list[str]`
Return schema validation errors; return empty list when valid.

### Checkpoints
- Fixture JSON loads successfully.
- Round-trip serialization preserves structure.
- Invalid house or graha indices are rejected.
- Schema versioning exists from day one.

### Tests
#### Unit
- enum validation
- missing mandatory fields
- round-trip serialization

#### Integration
- validate 3 sample chart fixtures

#### Regression
- golden JSON snapshots

---

## Phase 2: Calculation engine adapter layer

### Objective
Abstract the horoscope computation backend behind a stable interface.

### Deliverables
- engine protocol
- primary adapter
- optional secondary adapter
- normalization layer

### Required modules
- `src/vedic_ai/engines/base.py`
- `src/vedic_ai/engines/vedastro_adapter.py`
- `src/vedic_ai/engines/secondary_adapter.py`
- `src/vedic_ai/engines/normalizer.py`
- `tests/unit/test_engine_normalizer.py`
- `tests/integration/test_engine_adapter_real.py`

### Interface

```python
class AstrologyEngine(Protocol):
    def compute_birth_chart(self, birth: BirthData, options: dict | None = None) -> ChartBundle:
        ...

    def compute_divisional_chart(self, birth: BirthData, division: str, options: dict | None = None) -> DivisionalChart:
        ...

    def compute_dashas(self, birth: BirthData, options: dict | None = None) -> list[DashaPeriod]:
        ...

    def compute_transits(self, birth: BirthData, at_time: datetime, options: dict | None = None) -> TransitSnapshot:
        ...
```

### Function specifications

#### `select_engine(engine_name: str, config: AppConfig) -> AstrologyEngine`
Instantiate the configured backend adapter.

#### `normalize_engine_output(raw_output: dict, birth: BirthData, options: dict | None = None) -> ChartBundle`
Transform backend-specific output into canonical schema.

#### `compute_core_chart(birth: BirthData, engine: AstrologyEngine, include_dashas: bool = True, include_vargas: list[str] | None = None) -> ChartBundle`
Compute the minimum interpretation-ready chart package.

### Checkpoints
- One backend returns valid `ChartBundle`.
- Output includes 9 grahas and 12 houses.
- D1 plus basic dasha output works.
- Backend exceptions map to typed application errors.

### Tests
#### Unit
- engine selection
- normalization mapping
- error translation

#### Integration
- real adapter call for one known chart

#### Regression
- golden normalized chart output

---

## Phase 3: Derived feature extraction

### Objective
Transform raw placements into interpretation-ready features.

### Deliverables
- feature extraction pipeline
- deterministic derived facts
- reusable feature registry

### Required modules
- `src/vedic_ai/features/base.py`
- `src/vedic_ai/features/core_features.py`
- `src/vedic_ai/features/strength.py`
- `src/vedic_ai/features/aspects.py`
- `src/vedic_ai/features/lordships.py`
- `src/vedic_ai/features/nakshatra_features.py`
- `tests/unit/test_features_core.py`

### Function specifications

#### `extract_core_features(bundle: ChartBundle) -> dict`
Generate normalized feature objects for planets, houses, signs, lords, nakshatras, yogas, and status conditions.

#### `compute_planet_strengths(bundle: ChartBundle) -> dict[str, dict]`
Compute dignity and strength indicators for each graha.

#### `compute_house_lordships(bundle: ChartBundle) -> dict[int, dict]`
Map each house to its lord and the lord’s placement.

#### `compute_relationship_graph(bundle: ChartBundle) -> dict`
Build conjunction, aspect, exchange, and influence relationships.

### Checkpoints
- Every graha has a feature record.
- House lordship is traceable.
- Derived features are deterministic.
- Nakshatra metadata is accessible for prompting.

### Tests
#### Unit
- lordship logic
- aspect graph
- sign-house relation extraction

#### Integration
- extract features from golden chart

#### Regression
- snapshot feature dictionaries

---

## Phase 4: Rule engine and interpretation triggers

### Objective
Convert chart features into auditable interpretive signals before LLM generation.

### Deliverables
- rule definition format
- rule evaluator
- conflict resolution
- scoring model

### Required modules
- `src/vedic_ai/core/rules.py`
- `src/vedic_ai/core/rule_loader.py`
- `src/vedic_ai/core/rule_evaluator.py`
- `data/corpus/rules/*.yaml`
- `tests/unit/test_rule_evaluator.py`

### Rule fields
- `rule_id`
- `name`
- `scope`
- `conditions`
- `explanation_template`
- `weight`
- `source_refs`
- `conflict_policy`

### Function specifications

#### `load_rule_set(path: str) -> list[RuleDefinition]`
Load and validate local YAML/JSON rules.

#### `evaluate_rules(bundle: ChartBundle, features: dict, rule_set: list[RuleDefinition]) -> list[RuleTrigger]`
Return all matched rule triggers with evidence payloads.

#### `score_rule_triggers(triggers: list[RuleTrigger]) -> dict[str, float]`
Aggregate triggers into domain-level scores.

#### `resolve_rule_conflicts(triggers: list[RuleTrigger]) -> list[RuleTrigger]`
Apply precedence and conflict-resolution policy.

### Checkpoints
- Rule file loads successfully.
- Minimum 20 core rules exist.
- Each trigger includes chart evidence.
- Conflict behavior is deterministic.

### Tests
#### Unit
- single-rule match/no-match
- invalid rule rejection
- conflict resolution order

#### Integration
- evaluate full ruleset on fixture chart

#### Regression
- golden trigger snapshots

---

## Phase 5: Corpus ingestion and retrieval

### Objective
Build the local knowledge base and retrieval layer.

### Deliverables
- corpus ingestion pipeline
- chunking
- embeddings
- vector index
- retrieval interface

### Required modules
- `src/vedic_ai/retrieval/corpus_loader.py`
- `src/vedic_ai/retrieval/chunker.py`
- `src/vedic_ai/retrieval/embedder.py`
- `src/vedic_ai/retrieval/vector_store.py`
- `src/vedic_ai/retrieval/retriever.py`
- `tests/unit/test_chunking.py`
- `tests/integration/test_retrieval_pipeline.py`

### Function specifications

#### `ingest_corpus(source_paths: list[str], output_dir: str) -> CorpusManifest`
Read local documents, clean text, extract metadata, and build a manifest.

#### `chunk_corpus_documents(manifest: CorpusManifest, chunk_size: int = 600, overlap: int = 100) -> list[CorpusChunk]`
Split source documents into retrieval chunks with traceability.

#### `embed_corpus_chunks(chunks: list[CorpusChunk], model_name: str) -> EmbeddingBatch`
Generate embeddings for all chunks.

#### `build_vector_index(embeddings: EmbeddingBatch, backend: str = "faiss") -> VectorIndexHandle`
Persist the vector index locally.

#### `retrieve_supporting_passages(query: str, top_k: int = 5, filters: dict | None = None) -> list[RetrievedPassage]`
Return relevant passages for interpretation prompts.

### Checkpoints
- Corpus ingests from local text sources.
- Every chunk preserves source metadata.
- Retrieval works on seeded test queries.
- Fixed corpus yields stable index contents.

### Tests
#### Unit
- chunk boundaries
- metadata retention
- embedding batch structure

#### Integration
- ingestion to retrieval end-to-end

#### Regression
- fixed query returns expected top passages

---

## Phase 6: Prompt contracts and local LLM wrapper

### Objective
Standardize prompt construction and structured output generation.

### Deliverables
- LLM client abstraction
- prompt builder
- JSON output contract
- repair parser

### Required modules
- `src/vedic_ai/llm/base.py`
- `src/vedic_ai/llm/local_client.py`
- `src/vedic_ai/llm/prompt_builder.py`
- `src/vedic_ai/llm/output_parser.py`
- `tests/unit/test_prompt_builder.py`
- `tests/integration/test_local_llm_contract.py`

### Prompt inputs
- chart facts
- derived features
- triggered rules
- retrieved passages
- requested scope
- output schema
- instruction to avoid unsupported claims

### Function specifications

#### `build_interpretation_prompt(bundle: ChartBundle, features: dict, triggers: list[RuleTrigger], passages: list[RetrievedPassage], scope: str, output_schema: dict) -> str`
Construct the final prompt sent to the local model.

#### `generate_structured_interpretation(prompt: str, model_name: str, temperature: float = 0.2) -> dict`
Call the local LLM and return structured JSON.

#### `validate_llm_output(payload: dict, schema: dict) -> list[str]`
Validate output against schema.

#### `repair_llm_output(raw_text: str, schema: dict) -> dict`
Repair malformed JSON if possible.

### Checkpoints
- One wrapper supports LM Studio or Ollama.
- Prompt is deterministic for fixed input.
- JSON output is parsed and validated.
- Unsupported keys or malformed objects are rejected.

### Tests
#### Unit
- prompt section ordering
- valid/invalid JSON parsing
- schema validation

#### Integration
- one real local model call

#### Regression
- prompt snapshot tests

---

## Phase 7: Prediction orchestrator

### Objective
Wire the full chart-to-report workflow.

### Deliverables
- end-to-end orchestration service
- domain-specific prediction flow
- debugging artifacts

### Required modules
- `src/vedic_ai/orchestration/pipeline.py`
- `src/vedic_ai/orchestration/prediction_service.py`
- `src/vedic_ai/orchestration/evidence_builder.py`
- `tests/integration/test_prediction_pipeline.py`
- `tests/e2e/test_cli_prediction.py`

### Function specifications

#### `run_prediction_pipeline(birth: BirthData, scope: str, at_time: datetime | None = None) -> PredictionReport`
Execute chart computation, feature extraction, rule evaluation, retrieval, prompting, generation, validation, and assembly.

#### `build_prediction_evidence(bundle: ChartBundle, features: dict, triggers: list[RuleTrigger], passages: list[RetrievedPassage]) -> list[PredictionEvidence]`
Assemble evidence references for the final report.

#### `generate_scope_report(scope: str, interpretation: dict, evidence: list[PredictionEvidence]) -> PredictionSection`
Create a domain-specific section such as career or relationship analysis.

### Checkpoints
- One command generates a full report.
- Intermediate artifacts are persisted for debugging.
- Each prediction contains evidence references.
- Failures surface cleanly with typed errors.

### Tests
#### Unit
- evidence assembly
- report section formatting

#### Integration
- full prediction flow on fixture chart

#### End-to-end
- CLI prediction command

---

## Phase 8: Timing engine for dasha and transits

### Objective
Add time-aware prediction support.

### Deliverables
- dasha feature module
- transit feature module
- timing fusion logic

### Required modules
- `src/vedic_ai/features/dasha_features.py`
- `src/vedic_ai/features/transit_features.py`
- `src/vedic_ai/orchestration/timing_service.py`
- `tests/unit/test_timing_features.py`
- `tests/integration/test_timing_pipeline.py`

### Function specifications

#### `compute_timing_features(bundle: ChartBundle, at_time: datetime) -> dict`
Return active Mahadasha, Antardasha, and relevant transit facts.

#### `evaluate_timing_rules(bundle: ChartBundle, features: dict, timing_features: dict, rule_set: list[RuleDefinition]) -> list[RuleTrigger]`
Evaluate time-dependent rules.

#### `generate_forecast_window(birth: BirthData, start: datetime, end: datetime, scopes: list[str]) -> ForecastReport`
Generate forecast outputs for a selected interval.

### Checkpoints
- Active dasha for any date can be computed.
- Timing rules are separated from natal rules.
- A 3- or 6-month forecast is supported.

### Tests
#### Unit
- dasha lookup
- transit normalization

#### Integration
- forecast generation on fixture ranges

#### Regression
- golden active-dasha snapshots

---

## Phase 9: Evaluation framework

### Objective
Measure grounding, consistency, and usefulness before any tuning.

### Deliverables
- labeled evaluation case format
- metrics
- benchmark runner
- regression baseline

### Required modules
- `src/vedic_ai/evaluation/dataset.py`
- `src/vedic_ai/evaluation/metrics.py`
- `src/vedic_ai/evaluation/runner.py`
- `tests/unit/test_metrics.py`

### Evaluation dimensions
- schema validity
- evidence coverage
- unsupported claim rate
- retrieval relevance
- rule-trigger agreement
- cross-run consistency
- human review score

### Function specifications

#### `load_evaluation_set(path: str) -> EvaluationSet`
Load labeled chart cases and expected outputs.

#### `score_prediction_report(report: PredictionReport, reference: EvaluationCase) -> EvaluationResult`
Compute metrics for one report.

#### `run_regression_benchmark(cases: EvaluationSet, model_name: str) -> BenchmarkSummary`
Run the benchmark and persist results.

### Checkpoints
- At least 20 reviewed cases exist.
- Unsupported claim detection exists.
- Baseline metrics are stored before major changes.

### Tests
#### Unit
- metric calculations
- dataset parsing

#### Integration
- mini benchmark run

#### Regression
- compare new metrics to baseline

---

## Phase 10: Optional fine-tuning track

### Objective
Add fine-tuning only after RAG baseline is stable.

### Deliverables
- SFT dataset builder
- training export
- comparison report

### Required modules
- `src/vedic_ai/evaluation/training_data.py`
- `src/vedic_ai/llm/fine_tune_prep.py`
- `scripts/train_lora.py`
- `tests/integration/test_training_data_export.py`

### Function specifications

#### `build_sft_examples(cases: EvaluationSet) -> list[dict]`
Generate supervised examples from chart facts, retrieved evidence, and approved interpretations.

#### `export_training_dataset(examples: list[dict], output_path: str) -> str`
Write JSONL training data.

#### `compare_rag_vs_tuned(baseline_results: BenchmarkSummary, tuned_results: BenchmarkSummary) -> ModelComparison`
Compare tuned model quality against baseline.

### Checkpoints
- Training examples are human-reviewed.
- Tuned model improves benchmark results without increasing unsupported claims.

### Tests
#### Unit
- export format

#### Integration
- training-data generation flow

#### Regression
- model-comparison report

---

## Phase 11: API and CLI surface

### Objective
Expose the framework for apps and local workflows.

### Deliverables
- FastAPI app
- request validation
- report export
- CLI commands

### Required modules
- `src/vedic_ai/api/app.py`
- `src/vedic_ai/api/routes_chart.py`
- `src/vedic_ai/api/routes_prediction.py`
- `src/vedic_ai/cli/commands_predict.py`
- `tests/e2e/test_api_prediction.py`

### Function specifications

#### `create_api_app(config: AppConfig) -> FastAPI`
Build and configure the API app.

#### `predict_from_birth_payload(payload: dict) -> dict`
Validate input and execute the prediction pipeline.

#### `export_report(report: PredictionReport, format: str = "json") -> str | dict`
Export report as JSON or Markdown.

### Checkpoints
- CLI and API use the same orchestration layer.
- Invalid requests return actionable errors.
- Export preserves evidence references.

### Tests
#### Unit
- request validation
- export formatting

#### Integration
- API lifecycle test

#### End-to-end
- CLI/API equivalence test

---

## Phase 12: Hardening and reproducibility

### Objective
Make the framework stable for long-term local use.

### Deliverables
- cache layer
- reproducibility manifest
- storage repository layer
- troubleshooting docs

### Required modules
- `src/vedic_ai/storage/cache.py`
- `src/vedic_ai/storage/repository.py`
- `src/vedic_ai/utils/repro.py`
- `docs/troubleshooting.md`
- `tests/integration/test_reproducibility.py`

### Function specifications

#### `cache_chart_bundle(cache_key: str, bundle: ChartBundle) -> None`
Persist chart bundle for reuse.

#### `load_cached_chart_bundle(cache_key: str) -> ChartBundle | None`
Return cached bundle if available.

#### `build_reproducibility_manifest(report: PredictionReport) -> dict`
Capture engine version, model version, corpus hash, prompt hash, and schema version.

### Checkpoints
- Same input and config produce the same deterministic artifacts.
- Reproducibility manifest is generated for each report.
- Cached objects still pass schema validation.

### Tests
#### Unit
- cache behavior
- manifest completeness

#### Integration
- repeat-run reproducibility checks

#### Regression
- report metadata snapshots

---

## Cross-phase acceptance gates

Before moving to the next phase:

- all new modules must have unit tests
- at least one integration test must exist
- regression snapshots must pass or be intentionally updated
- public functions must have type hints and docstrings
- no placeholders or TODO stubs may remain
- all artifacts must serialize cleanly
- logging must exist at orchestration boundaries
- failure modes must be typed and documented

---

## MVP scope

The first usable MVP should stop after Phase 7 and include:

- D1 chart only
- 9 grahas
- 12 houses
- 12 signs
- 27 nakshatras
- basic lordships and aspects
- 20 to 50 core rules
- small curated corpus
- local report generation for personality, career, and relationships
- evidence-linked outputs

Do **not** attempt all 30 chart types in the first build.

---

## Claude Code execution protocol

Claude Code should execute phases in this order:

1. Bootstrap repository.
2. Implement schemas and fixtures.
3. Add one engine adapter.
4. Add feature extraction.
5. Add rule engine.
6. Add corpus ingestion and retrieval.
7. Add local LLM wrapper.
8. Wire full orchestrator.
9. Add timing features.
10. Add evaluation framework.
11. Explore fine-tuning only after benchmarks are stable.

At the end of each phase, run:

```bash
pytest tests/unit -q
pytest tests/integration -q
```

At regression phases, also run:

```bash
pytest tests/regression -q
```

If any checkpoint fails, Claude Code must stop, summarize the failure, fix the issue, and rerun tests before continuing.

---

## Definition of done

Version 1 is complete when the system can accept birth data, compute a canonical chart bundle, derive traceable features, evaluate interpretation rules, retrieve supporting passages, generate a structured local prediction report, and attach evidence for every major claim.
