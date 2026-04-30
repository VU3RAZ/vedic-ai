#!/usr/bin/env python
"""Generate data/fixtures/*.json from the canonical fixture factories.

Run from the project root:
    python scripts/gen_fixtures.py
"""

import json
import sys
from pathlib import Path

# Allow imports from src without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from conftest import build_chart_a, build_chart_b, build_chart_c
from vedic_ai.domain.chart import serialize_chart_bundle

FIXTURES_DIR = Path(__file__).parent.parent / "data" / "fixtures"


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    charts = {
        "sample_chart_a.json": build_chart_a(),
        "sample_chart_b.json": build_chart_b(),
        "sample_chart_c.json": build_chart_c(),
    }
    for filename, bundle in charts.items():
        path = FIXTURES_DIR / filename
        payload = serialize_chart_bundle(bundle)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
