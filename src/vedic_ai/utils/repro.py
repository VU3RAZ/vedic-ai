"""Reproducibility manifest builder."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

from vedic_ai.domain.prediction import PredictionReport


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _hash_directory(path: Path, pattern: str = "**/*.txt") -> str:
    """Return a SHA-256 digest over sorted contents of matching files."""
    h = hashlib.sha256()
    for fpath in sorted(path.glob(pattern)):
        h.update(fpath.read_bytes())
    return h.hexdigest()[:16]


def build_reproducibility_manifest(
    report: PredictionReport,
    corpus_dir: Path | None = None,
) -> dict:
    """Capture all version and content hashes needed to reproduce a report.

    Includes:
    - schema_version from the report
    - model_name from the report
    - key package versions (vedic-ai, pydantic, sentence-transformers, faiss-cpu)
    - corpus_hash (first 16 hex chars of SHA-256 over corpus text files)
    - prompt_hash placeholder (populated by pipeline if prompt is passed separately)

    Returns a JSON-safe dict.
    """
    corpus_path = corpus_dir or Path("data/corpus/texts")
    corpus_hash: str
    if corpus_path.exists():
        corpus_hash = _hash_directory(corpus_path, "**/*.txt")
    else:
        corpus_hash = "no-corpus"

    return {
        "schema_version": report.schema_version,
        "model_name": report.model_name,
        "generated_at": report.generated_at.isoformat(),
        "packages": {
            "vedic-ai": _package_version("vedic-ai"),
            "pydantic": _package_version("pydantic"),
            "sentence-transformers": _package_version("sentence-transformers"),
            "faiss-cpu": _package_version("faiss-cpu"),
            "fastapi": _package_version("fastapi"),
        },
        "corpus_hash": corpus_hash,
        "sections": [s.scope for s in report.sections],
    }
