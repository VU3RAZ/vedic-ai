"""LoRA fine-tuning script stub.

This script prepares and exports training data for LoRA fine-tuning.
Actual LoRA training requires a compatible trainer (e.g. unsloth, axolotl,
or HuggingFace TRL) and a GPU. This script is a data-preparation entrypoint
only — it does not invoke a GPU training loop.

Usage:
  python scripts/train_lora.py --eval-set data/golden/eval_set_v1.json \
      --reports-dir data/processed/reports/ \
      --output data/processed/training_data.jsonl

Prerequisites (install manually before running):
  pip install unsloth trl peft
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export LoRA SFT training data")
    parser.add_argument("--eval-set", required=True, help="Path to evaluation set JSON")
    parser.add_argument(
        "--reports-dir", required=True, help="Directory with PredictionReport JSON files"
    )
    parser.add_argument(
        "--output", default="data/processed/training_data.jsonl", help="Output JSONL path"
    )
    args = parser.parse_args()

    from vedic_ai.domain.prediction import PredictionReport
    from vedic_ai.evaluation.dataset import load_evaluation_set
    from vedic_ai.evaluation.training_data import build_sft_examples, export_training_dataset

    ev_set = load_evaluation_set(args.eval_set)

    reports_dir = Path(args.reports_dir)
    reports: list[PredictionReport] = []
    for case in ev_set.cases:
        rpath = reports_dir / f"{case.case_id}.json"
        if not rpath.exists():
            print(f"WARNING: Report not found for {case.case_id}, skipping")
            reports.append(
                PredictionReport(
                    generated_at=__import__("datetime").datetime.now(
                        __import__("datetime").timezone.utc
                    ),
                    sections=[],
                    model_name="missing",
                )
            )
        else:
            reports.append(PredictionReport.model_validate(json.loads(rpath.read_text())))

    examples = build_sft_examples(ev_set, reports)
    out = export_training_dataset(examples, args.output)
    print(f"Exported {len(examples)} training examples to {out}")


if __name__ == "__main__":
    main()
