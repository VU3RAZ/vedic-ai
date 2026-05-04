# Vedic AI — Complete Module Interconnection Flowchart

> Every arrow (→) is a real Python import dependency. Grouped by execution tier.  
> Read top-to-bottom: lower layers depend on upper layers, never the reverse.

---

## TIER 0 — FOUNDATION (no internal dependencies)

These modules import nothing from within vedic_ai. They are pure leaf nodes.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  FOUNDATION LAYER — zero internal dependencies                                      │
│                                                                                     │
│  domain/enums.py          domain/birth.py       domain/corpus.py                   │
│  ─────────────────         ───────────────       ────────────────                   │
│  Graha (9)                 BirthData             CorpusChunk                        │
│  Rasi (12)                 GeoLocation           CorpusManifest                     │
│  NakshatraName (27)                              EmbeddingBatch                     │
│  Dignity                                         RetrievedPassage                   │
│  NodeType                                        VectorIndexHandle                  │
│  Ayanamsa                                        SourceFile                         │
│  HouseSystem                                                                        │
│                                                                                     │
│  core/exceptions.py       core/rules.py          core/logging.py                   │
│  ──────────────────        ─────────────          ───────────────                   │
│  VedicAIError              RuleDefinition         setup_logging()                   │
│  ConfigError               RuleOperator                                             │
│  EngineError               RuleCondition                                            │
│  SchemaError               ConflictPolicy                                           │
│  LLMError                                                                           │
│  RetrievalError                                                                     │
│  RuleError                                                                          │
│                                                                                     │
│  llm/base.py              llm/output_parser.py                                     │
│  ──────────               ────────────────────                                      │
│  LLMClient (Protocol)     validate_llm_output()                                     │
│                           repair_llm_output()                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## TIER 1 — BASIC DOMAIN + CONFIG

```
domain/enums.py ──────────────┬──────────────────────────────────────────────┐
                              │                                              │
                              ▼                                              ▼
          ┌────────────────────────┐   ┌──────────────┐   ┌─────────────────────────┐
          │  domain/planet.py      │   │domain/house.py│   │  domain/nakshatra.py    │
          │  ─────────────────     │   │──────────────│   │  ──────────────────────  │
          │  RasiPlacement         │   │HousePlacement│   │  NakshatraDetail        │
          │  NakshatraPlacement    │   │              │   │  NAKSHATRA_DATA (27)    │
          │  PlanetPlacement       │   │              │   │                         │
          └────────────────────────┘   └──────────────┘   └─────────────────────────┘

domain/enums.py ──────────────┬────────────────────────────────────────────────
                              ▼
          ┌──────────────────────┐      core/exceptions.py ─────────────────────┐
          │  domain/dasha.py     │                                               │
          │  ────────────────    │                                               ▼
          │  DashaPeriod         │      ┌──────────────────────────────────────────┐
          └──────────────────────┘      │  core/config.py                          │
                                        │  ────────────────                        │
                                        │  LogConfig, StorageConfig                │
                                        │  AstrologyConfig, AppConfig              │
                                        │  load_app_config()                       │
                                        └──────────────────────────────────────────┘
```

---

## TIER 2 — COMPLEX DOMAIN + ENGINE PRIMITIVES

```
domain/birth.py ──┐
domain/dasha.py ──┤
domain/house.py ──┼──────────────────────────────────────────────────────────┐
domain/planet.py ─┤                                                          │
core/exceptions.py┘                                                          ▼
                                                             ┌──────────────────────────┐
                                                             │  domain/chart.py          │
                                                             │  ───────────────          │
                                                             │  ChartBundle              │
                                                             │  DivisionalChart          │
                                                             │  TransitSnapshot          │
                                                             │  serialize_chart_bundle() │
                                                             │  deserialize_chart_bundle │
                                                             └──────────────────────────┘
                                                                        │
                                                                        ▼
domain/chart.py ─────────────────────────────────────────► domain/prediction.py
                                                             ───────────────────
                                                             RuleTrigger
                                                             PredictionEvidence
                                                             PredictionSection
                                                             PredictionReport
                                                             ForecastWindow
                                                             ForecastReport

core/exceptions.py ─────────┐
core/rules.py ──────────────┼────────────────────────────► core/rule_loader.py
domain/enums.py ────────────┘                               ──────────────────
                                                             load_rule_set()

domain/enums.py ──► engines/varga.py      engines/dignity.py      engines/vimshottari.py
                    ────────────────       ──────────────────       ──────────────────────
                    compute_varga_rasi()   RASI_LORDS (dict)        VIMSHOTTARI_SEQUENCE
                                          compute_dignity()         compute_vimshottari_dashas()
                                                                    compute_antardasha_periods()
```

---

## TIER 3 — ENGINE CORE + RULE EVALUATOR

```
domain/birth.py ─────┐
domain/chart.py ─────┤
domain/enums.py ─────┤
domain/house.py ─────┤                          ┌──────────────────────────────────┐
domain/nakshatra.py ─┤──────────────────────────►  engines/normalizer.py            │
domain/planet.py ────┤                          │  ─────────────────────────────── │
core/exceptions.py ──┤                          │  normalize_engine_output()        │
engines/dignity.py ──┤                          │  build_varga_chart()              │
engines/varga.py ────┘                          │  _longitude_to_rasi()             │
                                                 │  _longitude_to_nakshatra()        │
                                                 │  _planet_house()                  │
                                                 │  _build_planet_placement()        │
                                                 └──────────────────────────────────┘

domain/chart.py ─────┐
domain/prediction.py ┤────────────────────────► core/rule_evaluator.py
core/rules.py ───────┘                          ─────────────────────
                                                 evaluate_rules()
                                                 score_rule_triggers()
                                                 resolve_rule_conflicts()

domain/chart.py ────────────────────────────────► features/base.py
                                                   ────────────────
                                                   KENDRA_HOUSES
                                                   TRIKONA_HOUSES
                                                   DUSTHANA_HOUSES
                                                   HOUSE_TYPES
                                                   FeatureExtractor (Protocol)

domain/chart.py ─────────────────────────────► engines/base.py
domain/birth.py ─────┐                         ──────────────
domain/dasha.py ─────┼──────────────────────►  AstrologyEngine (Protocol)
engines/normalizer.py┘                          compute_core_chart()
```

---

## TIER 4 — ENGINE ADAPTERS + INDIVIDUAL FEATURE MODULES

### Engine Adapters

```
domain/birth.py ─────┐
domain/chart.py ─────┤
domain/dasha.py ─────┤
domain/enums.py ─────┤─────────────────────────► engines/swisseph_adapter.py [PRIMARY]
core/exceptions.py ──┤                            ──────────────────────────────────────
engines/normalizer.py┤                            SwissEphAdapter
engines/vimshottari.py┘                           .compute_birth_chart()
                                                   .compute_divisional_chart()
                                                   .compute_dashas()
                                                   .compute_transits()

domain/birth.py ─────┐
domain/chart.py ─────┤─────────────────────────► engines/kerykeion_adapter.py [SECONDARY]
domain/dasha.py ─────┤                            ─────────────────────────────────────
core/exceptions.py ──┘                            KerykeionAdapter

core/config.py ──────┐
core/exceptions.py ──┤
engines/base.py ─────┤─────────────────────────► engines/registry.py
engines/kerykeion ───┤                            ──────────────────
engines/swisseph ────┘                            select_engine()  (singleton cache)
```

### Individual Feature Modules (all depend on domain/chart.py)

```
                                    domain/chart.py ──────────────────────────────────┐
                                    domain/enums.py ──────────────────────────────┐   │
                                    engines/dignity.py ────────────────────────┐  │   │
                                    features/base.py ───────────────────────┐  │  │   │
                                                                             │  │  │   │
                                                                             ▼  ▼  ▼  ▼
┌─────────────────────┐  ┌──────────────────────┐  ┌───────────────────────────────────┐
│ features/aspects.py │  │ features/strength.py │  │  features/lordships.py            │
│ ─────────────────── │  │ ──────────────────── │  │  ──────────────────────           │
│ GRAHA_ASPECTS       │  │ DIGNITY_SCORES        │  │  HOUSE_KARAKAS                    │
│ compute_relationship│  │ compute_combustion()  │  │  compute_house_lordships()        │
│ _graph()            │  │ compute_planet_       │  │  (also imports features/strength) │
└─────────────────────┘  │ strengths()           │  └───────────────────────────────────┘
                         │ full_dignity()         │
                         └──────────────────────┘

domain/chart.py + domain/enums.py ──────────────────────────────────────────────────────
                                    │               │               │
                                    ▼               ▼               ▼
                        ┌──────────────────┐ ┌──────────────┐ ┌───────────────────────┐
                        │features/drishti.py│ │features/     │ │features/nakshatra_    │
                        │─────────────────  │ │sandhi.py     │ │features.py            │
                        │compute_rashi_     │ │─────────────  │ │───────────────────    │
                        │drishti()          │ │compute_sandhi │ │extract_nakshatra_     │
                        │compute_full_      │ │_analysis()    │ │features()             │
                        │drishti_matrix()   │ └──────────────┘ │(+nakshatra.py,        │
                        └──────────────────┘                   │ normalizer._long→nk)  │
                                                                └───────────────────────┘

domain/chart.py + domain/dasha.py + engines/vimshottari.py ────────────────────────────
                                    ▼
                        ┌───────────────────────────────┐
                        │  features/dasha_features.py   │
                        │  ────────────────────────────  │
                        │  get_active_mahadasha()        │
                        │  get_active_antardasha()       │
                        │  compute_timing_features()     │
                        │  assess_dasha_lord()           │
                        └───────────────────────────────┘

domain/chart.py + domain/enums.py + engines/dignity.py + features/base.py ─────────────
                                    │                    │
                                    ▼                    ▼
                        ┌──────────────────────┐  ┌──────────────────────────────────┐
                        │features/functional_  │  │  features/varga_analysis.py      │
                        │nature.py             │  │  ────────────────────────────     │
                        │──────────────────────│  │  analyze_varga_chart()            │
                        │compute_functional_   │  │  extract_varga_analysis()         │
                        │nature()              │  │  (D3/D7/D9/D10/D12)               │
                        └──────────────────────┘  └──────────────────────────────────┘

domain/chart.py + domain/enums.py + engines/dignity.py + features/base.py ─────────────
                                    ▼
                        ┌───────────────────────────────────────────────────┐
                        │  features/yogas_extended.py                        │
                        │  ──────────────────────────────────────────────── │
                        │  detect_lunar_yogas()   detect_solar_yogas()      │
                        │  detect_conjunction_yogas()                        │
                        │  detect_wealth_yogas()  detect_special_yogas()    │
                        │  detect_nabhasa_yogas() detect_kartari_yogas()    │
                        └───────────────────────────────────────────────────┘

domain/chart.py + features/base.py ────────────────────────────────────────────────────
                                    │
                                    ▼
                        ┌────────────────────────────────┐  ┌──────────────────────────┐
                        │  features/raman_flowchart.py   │  │  features/house_         │
                        │  ────────────────────────────   │  │  influence.py            │
                        │  build_raman_flowchart()        │  │  ────────────────        │
                        └────────────────────────────────┘  │  HOUSE_TOPICS            │
                                                             │  compute_house_          │
domain/chart.py + domain/enums.py ──────────────────────────│  influence()             │
                                    ▼                        └──────────────────────────┘
                        ┌──────────────────────────────┐
                        │  features/transit_features.py │
                        │  ──────────────────────────── │
                        │  compute_transit_features()   │
                        └──────────────────────────────┘
```

---

## TIER 5 — FEATURE ORCHESTRATOR + RETRIEVAL PIPELINE

### Feature Orchestrator (imports ALL feature modules)

```
domain/chart.py ─────────────────────────────────────────────────────────┐
domain/enums.py ─────────────────────────────────────────────────────┐   │
engines/dignity.py ───────────────────────────────────────────────┐  │   │
engines/normalizer.py ────────────────────────────────────────┐   │  │   │
engines/vimshottari.py ───────────────────────────────────┐   │   │  │   │
features/aspects.py ─────────────────────────────────┐   │   │   │  │   │
features/base.py ────────────────────────────────┐   │   │   │   │  │   │
features/dasha_features.py ──────────────────┐   │   │   │   │   │  │   │
features/drishti.py ─────────────────────┐   │   │   │   │   │   │  │   │
features/functional_nature.py ───────┐   │   │   │   │   │   │   │  │   │
features/house_influence.py ─────┐   │   │   │   │   │   │   │   │  │   │
features/lordships.py ───────┐   │   │   │   │   │   │   │   │   │  │   │
features/nakshatra_features.py┐  │   │   │   │   │   │   │   │   │  │   │
features/raman_flowchart.py ─┐│  │   │   │   │   │   │   │   │   │  │   │
features/sandhi.py ─────────┐││  │   │   │   │   │   │   │   │   │  │   │
features/strength.py ──────┐│││  │   │   │   │   │   │   │   │   │  │   │
features/transit_features.py┐│││  │   │   │   │   │   │   │   │   │  │   │
features/varga_analysis.py ─┐│││  │   │   │   │   │   │   │   │   │  │   │
features/yogas_extended.py ─┐│││  │   │   │   │   │   │   │   │   │  │   │
                             ▼▼▼▼  ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼  ▼   ▼
                    ┌─────────────────────────────────────────────────────┐
                    │            features/core_features.py                │
                    │  ─────────────────────────────────────────────────  │
                    │  extract_core_features(bundle) → features_dict      │
                    │                                                      │
                    │  Output keys (50+):                                  │
                    │  planets.{graha}.{house,rasi,dignity,strength,...}   │
                    │  houses.{1-12}.{lord,occupants,type}                 │
                    │  yogas.{mahapurusha,kemdruma,dhana,raja,...}         │
                    │  drishti.matrix[9×12]                                │
                    │  sandhi.{in_sandhi,madhya}                           │
                    │  varga_analysis.{D9,D10,...}                         │
                    │  timing.{mahadasha_lord,antardasha_lord,...}         │
                    │  transit.{graha_over_natal,...}                      │
                    │  raman.{classification,...}                          │
                    └─────────────────────────────────────────────────────┘
```

### Retrieval Pipeline

```
core/exceptions.py ──┐
domain/corpus.py ────┤───────────────────────────────► retrieval/corpus_loader.py
                     │                                  ──────────────────────────
                     │                                  ingest_corpus()
                     │                                  load_manifest()
                     │                                  _split_frontmatter()
                     │
domain/corpus.py ────┼──► retrieval/corpus_loader.py ──► retrieval/chunker.py
                     │                                     ────────────────────
                     │                                     chunk_corpus_documents()
                     │                                     (size=600, overlap=100)
                     │
domain/corpus.py ────┼───────────────────────────────► retrieval/embedder.py
                     │                                  ──────────────────────
                     │                                  embed_corpus_chunks()
                     │                                  (all-MiniLM-L6-v2, 384-dim)
                     │
domain/corpus.py ────┼───────────────────────────────► retrieval/vector_store.py
                     │                                  ───────────────────────────
                     │                                  build_vector_index()
                     │                                  load_vector_index()
                     │                                  (FAISS IndexFlatIP, cosine)
                     │
domain/corpus.py ────┴───────────────────────────────► retrieval/retriever.py
                                                         ───────────────────────
                                                         Retriever.retrieve()
                                                         create_retriever()
                                                         retrieve_supporting_passages()

domain/prediction.py ───────────────────────────────► retrieval/query_expander.py
                                                         ───────────────────────────
                                                         expand_queries()
                                                         hyde_query()
```

---

## TIER 6 — LLM LAYER

```
core/exceptions.py ─────────────────────────────────► llm/local_client.py
                                                         ─────────────────
                                                         LocalLLMClient
                                                         .generate(prompt, temp)
                                                         Backends:
                                                         • Ollama :11434
                                                         • LM Studio :1234
                                                         • llama.cpp :8080

domain/chart.py ─────┐
domain/corpus.py ────┤─────────────────────────────► llm/prompt_builder.py
domain/prediction.py ┘                               ─────────────────────
                                                       build_interpretation_prompt()
                                                       → structured prompt string

evaluation/runner.py ───────────────────────────────► llm/fine_tune_prep.py
                                                         ──────────────────────
                                                         compare_rag_vs_tuned()
                                                         ModelComparison
                                                         (Phase 10: SFT prep)
```

---

## TIER 7 — ORCHESTRATION SERVICES

```
domain/chart.py ──────┐
domain/corpus.py ─────┤────────────────────────────► orchestration/evidence_builder.py
domain/prediction.py ─┘                              ────────────────────────────────
                                                       build_prediction_evidence()
                                                       generate_scope_report()
                                                       → PredictionSection (with refs)

core/rule_evaluator.py ──┐
core/rule_loader.py ─────┤
core/rules.py ───────────┤
domain/chart.py ─────────┤───────────────────────► orchestration/prediction_service.py
domain/corpus.py ────────┤                          ─────────────────────────────────
domain/prediction.py ────┤                          load_rules_for_scope()
llm/output_parser.py ────┤                          evaluate_scope_rules()
llm/prompt_builder.py ───┘                          call_llm_for_interpretation()

core/rule_evaluator.py ──┐
core/rule_loader.py ─────┤
core/rules.py ───────────┤
domain/birth.py ─────────┤
domain/chart.py ─────────┤───────────────────────► orchestration/timing_service.py
domain/prediction.py ────┤                          ─────────────────────────────
engines/base.py ─────────┤                          evaluate_timing_rules()
features/core_features.py┤                          generate_forecast_window()
features/dasha_features.py┤                         → ForecastReport
features/transit_features.py┘
```

---

## TIER 8 — EVALUATION + STORAGE + UTILS

```
core/exceptions.py ──┐
domain/prediction.py ┤────────────────────────────► evaluation/dataset.py
                      │                              ──────────────────────
                      │                              EvaluationCase
                      │                              EvaluationSet
                      │                              load_evaluation_set()

domain/prediction.py ─┐
evaluation/dataset.py ┤────────────────────────────► evaluation/metrics.py
                       │                              ──────────────────────
                       │                              EvaluationResult
                       │                              score_prediction_report()
                       │                              {grounding, coverage, consistency}

domain/prediction.py ─┐
evaluation/dataset.py ─┤───────────────────────────► evaluation/runner.py
evaluation/metrics.py ─┘                              ──────────────────────
                                                        BenchmarkSummary
                                                        run_regression_benchmark()

domain/prediction.py ─┐
evaluation/dataset.py ─┘───────────────────────────► evaluation/training_data.py
                                                        ──────────────────────────
                                                        build_sft_examples()
                                                        (Phase 10 SFT dataset)

domain/birth.py ──────┐
domain/chart.py ───────┤───────────────────────────► storage/cache.py
                        │                              ──────────────
                        │                              build_cache_key()
                        │                              cache_chart_bundle()
                        │                              load_cached_chart_bundle()
                        │                              (SQLite: chart_cache.db)

domain/prediction.py ──────────────────────────────► storage/repository.py
                                                        ──────────────────────
                                                        save_report()
                                                        load_report()
                                                        list_reports()

domain/prediction.py ──────────────────────────────► utils/repro.py
                                                        ─────────────
                                                        build_reproducibility_manifest()
```

---

## TIER 9 — PIPELINE (main orchestrator)

```
domain/birth.py ─────────────────┐
domain/prediction.py ────────────┤
engines/base.py ─────────────────┤
engines/swisseph_adapter.py ─────┤───────────────────► orchestration/pipeline.py
features/core_features.py ───────┤                      ──────────────────────────
orchestration/evidence_builder.py┤                      run_prediction_pipeline(
orchestration/prediction_service.py┘                      birth, scope, engine,
                                                           retriever, llm_client,
                                                           at_time, dry_run
                                                         ) → PredictionReport
                                                        ┌────────────────────────┐
                                                        │  9-stage execution:    │
                                                        │  1. compute_chart()    │
                                                        │  2. extract_features() │
                                                        │  3. evaluate_rules()   │
                                                        │  4. retrieve_passages()│
                                                        │  5. build_prompt()     │
                                                        │  6. call_llm()         │
                                                        │  7. parse_output()     │
                                                        │  8. build_evidence()   │
                                                        │  9. persist_artifacts()│
                                                        └────────────────────────┘
```

---

## TIER 10 — ENTRY POINTS (API · CLI · Web UI)

### FastAPI Entry Points

```
core/config.py ──────────────────────────────────────► api/app.py
api/routes_chart.py ────────────────────────────────┘  ──────────
api/routes_prediction.py ───────────────────────────┘  create_api_app()
                                                         mounts all routes
                                                         serves static/index.html

core/exceptions.py ──┐
domain/birth.py ─────┤
domain/chart.py ─────┤
engines/base.py ─────┤──────────────────────────────► api/routes_chart.py
engines/swisseph ────┤                                 ───────────────────
features/core_features┘                                POST /charts/compute
                                                         GET  /charts/{id}
                                                         → ChartBundle + features

domain/birth.py ──────────┐
domain/prediction.py ─────┤
orchestration/pipeline.py ─┤──────────────────────► api/routes_prediction.py
retrieval/chunker.py ──────┤                          ──────────────────────────
retrieval/corpus_loader.py ─┤                          POST /predictions
retrieval/retriever.py ─────┤                          GET  /predictions/scopes
retrieval/vector_store.py ──┘                          → PredictionReport (JSON)
```

### CLI Entry Points

```
core/config.py ──────┐
core/exceptions.py ──┤──────────────────────────────► cli/main.py
core/logging.py ─────┘                                ───────────
                                                         vedic-ai --help
                                                         vedic-ai info
                                                         vedic-ai --version

core/config.py ───────────┐
core/exceptions.py ────────┤
domain/birth.py ───────────┤
orchestration/pipeline.py ──┤
retrieval/chunker.py ────────┤──────────────────────► cli/commands_predict.py
retrieval/corpus_loader.py ──┤                          ──────────────────────
retrieval/retriever.py ──────┤                          vedic-ai predict <DT> <LAT> <LON>
retrieval/vector_store.py ───┤                            [--scope] [--dry-run] [--no-rag]
storage/cache.py ────────────┤                            [-k N] [-o FILE]
storage/repository.py ───────┘

retrieval/chunker.py ───────┐
retrieval/corpus_loader.py ──┤──────────────────────► cli/commands_corpus.py
retrieval/embedder.py ───────┤                          ──────────────────────
retrieval/vector_store.py ───┘                          vedic-ai build-index [--force]
                                                         vedic-ai corpus-info
                                                         vedic-ai search <QUERY>

(no internal imports) ──────────────────────────────► cli/commands_serve.py
                                                         ─────────────────────
                                                         vedic-ai serve [--port 8000]
```

---

## COMPLETE DEPENDENCY SUMMARY TABLE

| Module | Imports From | Imported By |
|--------|-------------|-------------|
| `domain/enums` | — | planet, house, nakshatra, dasha, chart, rule_loader, dignity, varga, vimshottari, aspects, strength, drishti, sandhi, functional_nature, varga_analysis, yogas, transit, core_features |
| `domain/birth` | — | chart, engines/base, swisseph, kerykeion, normalizer, timing_service, pipeline, routes_chart, routes_prediction, cli/predict, cache |
| `domain/corpus` | — | corpus_loader, chunker, embedder, vector_store, retriever, prompt_builder, evidence_builder |
| `domain/chart` | birth, dasha, house, planet, exceptions | prediction, normalizer, rule_evaluator, features/base, all feature modules, core_features, prompt_builder, evidence_builder, prediction_service, timing_service, pipeline, routes_chart, cache |
| `domain/prediction` | chart | rule_evaluator, query_expander, prompt_builder, evidence_builder, prediction_service, timing_service, pipeline, evaluation/*, storage/repository, utils/repro, routes_prediction |
| `core/exceptions` | — | config, rule_loader, normalizer, swisseph, kerykeion, registry, corpus_loader, local_client, dataset, routes_chart, cli/main, cli/predict |
| `core/config` | exceptions | registry, api/app, cli/main, cli/predict |
| `core/rules` | — | rule_loader, rule_evaluator, prediction_service, timing_service |
| `core/rule_loader` | exceptions, rules, enums | prediction_service, timing_service |
| `core/rule_evaluator` | chart, prediction, rules | prediction_service, timing_service |
| `engines/dignity` | enums | normalizer, aspects, strength, functional_nature, varga_analysis, yogas, core_features |
| `engines/varga` | enums | normalizer |
| `engines/vimshottari` | dasha, enums | swisseph, dasha_features, core_features |
| `engines/normalizer` | birth, chart, enums, house, nakshatra, planet, exceptions, dignity, varga | swisseph, nakshatra_features, core_features |
| `engines/swisseph` | birth, chart, dasha, enums, exceptions, normalizer, vimshottari | engines/base, pipeline, routes_chart |
| `engines/registry` | config, exceptions, base, kerykeion, swisseph | (used by app startup) |
| `features/base` | chart | strength, lordships, functional_nature, varga_analysis, yogas, raman, core_features |
| `features/strength` | chart, enums, dignity, base | lordships, core_features |
| `features/lordships` | chart, enums, base, strength | core_features |
| `features/aspects` | chart, enums, dignity | core_features |
| `features/drishti` | chart, enums | core_features |
| `features/sandhi` | chart, enums | core_features |
| `features/nakshatra_features` | chart, enums, nakshatra, normalizer | core_features |
| `features/dasha_features` | chart, dasha, vimshottari | core_features, timing_service |
| `features/transit_features` | chart, enums | core_features, timing_service |
| `features/functional_nature` | chart, enums, dignity, base | core_features |
| `features/varga_analysis` | chart, enums, dignity, base | core_features |
| `features/yogas_extended` | chart, enums, dignity, base | core_features |
| `features/raman_flowchart` | chart, base | core_features |
| `features/house_influence` | chart | core_features |
| `features/core_features` | chart, enums, dignity, normalizer, vimshottari + ALL feature modules | pipeline, timing_service, routes_chart |
| `retrieval/corpus_loader` | exceptions, corpus | chunker, cli/corpus |
| `retrieval/chunker` | corpus, corpus_loader | cli/corpus, routes_prediction, cli/predict |
| `retrieval/embedder` | corpus | cli/corpus |
| `retrieval/vector_store` | corpus | cli/corpus, routes_prediction, cli/predict |
| `retrieval/retriever` | corpus | routes_prediction, cli/predict |
| `retrieval/query_expander` | prediction | (optional, query expansion) |
| `llm/local_client` | exceptions | prediction_service |
| `llm/prompt_builder` | chart, corpus, prediction | prediction_service |
| `llm/output_parser` | — | prediction_service |
| `llm/fine_tune_prep` | evaluation/runner | (Phase 10 standalone) |
| `orchestration/evidence_builder` | chart, corpus, prediction | pipeline |
| `orchestration/prediction_service` | rule_evaluator, rule_loader, rules, chart, corpus, prediction, output_parser, prompt_builder | pipeline |
| `orchestration/timing_service` | rule_evaluator, rule_loader, rules, birth, chart, prediction, engines/base, core_features, dasha_features, transit_features | (standalone forecast) |
| `orchestration/pipeline` | birth, prediction, engines/base, swisseph, core_features, evidence_builder, prediction_service | routes_prediction, cli/predict |
| `evaluation/dataset` | exceptions, prediction | metrics, runner, training_data |
| `evaluation/metrics` | prediction, dataset | runner |
| `evaluation/runner` | prediction, dataset, metrics | fine_tune_prep |
| `evaluation/training_data` | prediction, dataset | (standalone SFT) |
| `storage/cache` | birth, chart | cli/predict |
| `storage/repository` | prediction | cli/predict |
| `utils/repro` | prediction | (standalone repro check) |
| `api/app` | config, routes_chart, routes_prediction | (uvicorn entrypoint) |
| `api/routes_chart` | exceptions, birth, chart, engines/base, swisseph, core_features | api/app |
| `api/routes_prediction` | birth, prediction, pipeline, chunker, corpus_loader, retriever, vector_store | api/app |
| `cli/main` | config, exceptions, logging | (typer entrypoint) |
| `cli/commands_predict` | config, exceptions, birth, pipeline, chunker, corpus_loader, retriever, vector_store, cache, repository | cli/main |
| `cli/commands_corpus` | chunker, corpus_loader, embedder, vector_store | cli/main |
| `cli/commands_serve` | — | cli/main |

---

## KEY ARCHITECTURAL INVARIANTS

1. **domain/** has no internal deps — it is the universal data contract layer.
2. **core/exceptions** is imported by almost every other layer (cross-cutting concern).
3. **engines/dignity** leaks into features — this is intentional (dignity is a computed primitive needed everywhere).
4. **features/core_features** is the single aggregation point — it imports every feature sub-module.
5. **orchestration/pipeline** is the only module that wires everything together end-to-end.
6. **retrieval/** and **llm/** are independent pipelines — they share only domain types.
7. **api/routes_prediction** and **cli/commands_predict** are symmetric entry points — both call `run_prediction_pipeline()`.
8. **evaluation/** has no runtime dependency on features or engines — it operates only on `PredictionReport` objects.
9. **storage/** is strictly downstream — it only persists, never computes.
10. No circular imports anywhere in the graph.
