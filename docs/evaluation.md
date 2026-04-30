# Evaluation

Framework for measuring grounding, consistency, and usefulness before any LLM fine-tuning. Phase 9 implements this; it must not be started until the Phase 7 MVP is complete and a RAG baseline exists.

## Evaluation dimensions

| Dimension                 | What it measures |
|---------------------------|------------------|
| Schema validity           | Output conforms to `PredictionReport` JSON schema |
| Evidence coverage         | Fraction of claims that have at least one `rule_ref` or `passage_ref` |
| Unsupported claim rate    | Fraction of claims with no traceable evidence |
| Retrieval relevance       | Mean reciprocal rank of expected passages for seed queries |
| Rule-trigger agreement    | Fraction of triggered rules that are referenced in the output |
| Cross-run consistency     | Variance of outputs for identical inputs across N runs |
| Human review score        | 1–5 scale on accuracy, usefulness, and tone |

## Evaluation case format

```json
{
  "case_id": "eva_001",
  "birth": { ... },
  "scope": "career",
  "expected_rule_ids": ["C001", "C003", "C009"],
  "expected_passage_sources": ["BPHS 24.5", "BPHS 24.3"],
  "human_label": {
    "accuracy": 4,
    "usefulness": 5,
    "tone": 4,
    "reviewer": "reviewer_initials",
    "reviewed_at": "2026-05-10"
  }
}
```

Cases are stored in `data/golden/evaluation_cases.jsonl`. A minimum of 20 reviewed cases is required before the first benchmark run.

## Metrics

### `score_prediction_report(report, reference) → EvaluationResult`

Computes per-report metrics:

```python
@dataclass
class EvaluationResult:
    case_id: str
    schema_valid: bool
    evidence_coverage: float   # [0, 1]
    unsupported_rate: float    # [0, 1]; lower is better
    rule_trigger_agreement: float
    human_score: float | None  # None if not labeled
```

### `run_regression_benchmark(cases, model_name) → BenchmarkSummary`

Aggregates across all cases:

```python
@dataclass
class BenchmarkSummary:
    model_name: str
    run_at: str          # ISO datetime
    n_cases: int
    mean_evidence_coverage: float
    mean_unsupported_rate: float
    mean_trigger_agreement: float
    mean_human_score: float | None
    schema_pass_rate: float
```

Results are persisted to `data/golden/benchmarks/{model_name}_{timestamp}.json`. The file for the current baseline is symlinked at `data/golden/benchmarks/baseline.json`.

## Regression gate

Before any LLM upgrade or prompt change, run:

```bash
pytest tests/regression -q
```

The regression suite:
1. Loads `data/golden/benchmarks/baseline.json`.
2. Runs the full pipeline on the 20+ evaluation cases.
3. Asserts each metric does not regress by more than the allowed delta.

| Metric                     | Max regression |
|----------------------------|---------------|
| `mean_evidence_coverage`   | −0.05         |
| `mean_unsupported_rate`    | +0.05         |
| `mean_trigger_agreement`   | −0.05         |
| `schema_pass_rate`         | −0.0 (strict) |

## Fine-tuning gate (Phase 10)

Fine-tuning is only permitted when:
- Baseline benchmark exists with ≥ 20 reviewed cases.
- `mean_unsupported_rate < 0.10` in the RAG baseline.
- `compare_rag_vs_tuned()` shows improvement in at least 2 of 4 automated metrics without regression in `unsupported_rate`.

## Human review process

Reviewers score outputs on three axes:
- **Accuracy (1–5)** — do the claims reflect the chart correctly?
- **Usefulness (1–5)** — is the analysis actionable and informative?
- **Tone (1–5)** — is the language appropriate for a Jyotish consultation?

Scores below 3 on accuracy must be investigated for rule engine or retrieval failures before merging changes.
