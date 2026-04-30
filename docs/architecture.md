# Architecture

## Layers

```
┌────────────────────────────────────────────────────────┐
│  CLI / API surface                                     │
│  src/vedic_ai/cli/   src/vedic_ai/api/                 │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│  Orchestration layer      src/vedic_ai/orchestration/  │
│  run_prediction_pipeline()                             │
└────┬──────────┬───────────┬────────────┬───────────────┘
     │          │           │            │
 ┌───▼──┐  ┌───▼───┐  ┌────▼────┐  ┌───▼──────┐
 │Engine│  │Feature│  │  Rule   │  │Retrieval │
 │layer │  │extract│  │ engine  │  │  layer   │
 └───┬──┘  └───┬───┘  └────┬────┘  └───┬──────┘
     │          │           │            │
 ┌───▼──────────▼───────────▼────────────▼──────┐
 │  Domain schemas   src/vedic_ai/domain/        │
 │  ChartBundle  RuleTrigger  PredictionReport   │
 └───────────────────────────────────────────────┘
```

## Module map

### `src/vedic_ai/domain/` — Canonical typed schemas (Phase 1)

| Module           | Key types |
|------------------|-----------|
| `birth.py`       | `BirthData`, `GeoLocation` |
| `chart.py`       | `ChartBundle`, `D1Chart`, `PlanetPlacement`, `HousePlacement` |
| `planet.py`      | `PlanetPlacement` |
| `house.py`       | `HousePlacement` |
| `nakshatra.py`   | `NakshatraPlacement` |
| `dasha.py`       | `DashaPeriod` |
| `prediction.py`  | `RuleTrigger`, `PredictionEvidence`, `PredictionReport` |
| `enums.py`       | `Graha`, `Rasi`, `Dignity`, `HouseType` |

`ChartBundle` is the central artifact. Every downstream module receives it as input and must not mutate it.

### `src/vedic_ai/engines/` — Calculation engine adapters (Phase 2)

| Module                  | Role |
|-------------------------|------|
| `base.py`               | `AstrologyEngine` Protocol |
| `swisseph_adapter.py`   | Primary adapter (flatlib/swisseph) |
| `kerykeion_adapter.py`  | Secondary adapter |
| `normalizer.py`         | Converts raw engine output to `ChartBundle` |
| `dignity.py`            | Dignity classification helpers |
| `vimshottari.py`        | Vimshottari dasha calculation |
| `registry.py`           | Engine selection by config name |

The `normalizer` is the boundary: all engine-specific representations end there.

### `src/vedic_ai/features/` — Derived feature extraction (Phase 3)

| Module                  | Produces |
|-------------------------|----------|
| `core_features.py`      | Top-level `extract_core_features(bundle) → dict` orchestrator |
| `strength.py`           | `planets.<Graha>.is_exalted`, `.dignity`, `.shadbala` |
| `lordships.py`          | `houses.<n>.lord`, `.lord_dignity`, `.lord_in_kendra`, etc. |
| `aspects.py`            | `planets.<Graha>.aspects_to_houses`, `houses.<n>.aspected_by` |
| `nakshatra_features.py` | `nakshatra_ascendant.*`, per-planet nakshatra metadata |
| `base.py`               | House-type constants (`KENDRA_HOUSES`, `TRIKONA_HOUSES`, `DUSTHANA_HOUSES`) |

The feature dict uses **capitalized graha names** (`"Sun"`, not `"sun"`) matching `Graha.value`, and **integer keys** for the `houses` sub-dict. Rule paths like `planets.Sun.house` and `houses.7.lord_dignity` navigate this structure.

### `src/vedic_ai/core/` — Rule engine (Phase 4)

| Module             | Role |
|--------------------|------|
| `rules.py`         | `RuleDefinition`, `RuleCondition`, `RuleOperator`, `ConflictPolicy` |
| `rule_loader.py`   | `load_rule_set(path)` — loads YAML, validates feature paths at load time |
| `rule_evaluator.py`| `evaluate_rules()`, `score_rule_triggers()`, `resolve_rule_conflicts()` |
| `config.py`        | `load_app_config()`, `AppConfig` |
| `logging.py`       | `setup_logging()` — structured logging via structlog |
| `exceptions.py`    | Typed exception hierarchy rooted at `VedicAIError` |

#### Rule YAML micro-DSL

```yaml
- rule_id: C001
  name: Sun in 10th House — Career Prominence
  scope: career
  weight: 0.75
  conditions:
    - feature: planets.Sun.house   # dot-notation path into feature dict
      op: eq                       # eq | ne | gt | lt | in | not_in | contains
      value: 10
  explanation_template: >-
    Sun placed in the 10th house …
  source_refs:
    - "BPHS 24.5"
  conflict_policy: merge           # merge | override | defer
```

#### Conflict resolution

Within a scope:
- `merge` — always kept.
- `override` — always kept; suppresses all `defer` triggers in the same scope.
- `defer` — dropped when any `override` trigger fires in the same scope.

#### Scoring

`score_rule_triggers()` returns the mean weight of triggered rules per scope (naturally bounded in [0, 1]).

### `data/corpus/rules/` — Seed rule corpus

| File                | Rules | Scopes |
|---------------------|-------|--------|
| `personality.yaml`  | 11    | personality |
| `career.yaml`       | 10    | career |
| `relationships.yaml`| 7     | relationships |

**Total: 28 rules** covering the MVP gate minimum of 20.

## Data flow detail (Phases 0–4)

```
BirthData
  → select_engine() + compute_birth_chart()
  → normalize_engine_output()
  → ChartBundle

ChartBundle
  → extract_core_features()
  → features: dict
      planets: { Sun: {house, sign, is_exalted, dignity, …}, … }
      houses:  { 1: {lord, lord_house, lord_dignity, is_occupied, …}, … }
      yogas:   { gajakesari: bool, kemadruma: bool, … }
      lagna:   { sign, lord, lord_house, lord_dignity, … }

(ChartBundle, features, rule_set)
  → evaluate_rules()
  → list[RuleTrigger]           # matched rules with evidence payload
  → resolve_rule_conflicts()
  → list[RuleTrigger]           # after conflict policy applied
  → score_rule_triggers()
  → dict[scope, float]          # per-scope mean weight
```

## Exception hierarchy

```
VedicAIError
├── ConfigError     — bad config, missing YAML, malformed rule file
├── RuleError       — invalid rule schema, bad feature path, duplicate rule_id
├── EngineError     — calculation backend failure
└── SchemaError     — ChartBundle validation failure
```

## Invariants

- `ChartBundle` is immutable across the pipeline; no module mutates it.
- Feature dict keys for grahas are `Graha.value` strings (capitalized).
- Feature dict keys for house numbers are Python `int`, not strings.
- Every `RuleTrigger` carries the feature values that satisfied its conditions in `evidence`.
- `resolve_rule_conflicts` is self-contained: conflict policy travels with the trigger, not the rule definition.
