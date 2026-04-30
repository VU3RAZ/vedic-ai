"""Corpus ingestion: read source text files, parse frontmatter, build a manifest."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import yaml

from vedic_ai.core.exceptions import ConfigError
from vedic_ai.domain.corpus import CorpusManifest, SourceFile


def _split_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter delimited by '---' and return (metadata, body)."""
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()

    try:
        metadata = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, body


def ingest_corpus(source_paths: list[str], output_dir: str) -> CorpusManifest:
    """Read text files from source_paths, extract frontmatter metadata, and build a manifest.

    Each entry in source_paths may be a file or a directory (all .txt files are ingested).
    The manifest is saved to {output_dir}/manifest.json.

    Raises:
        ConfigError: when a path in source_paths does not exist.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    for sp in source_paths:
        p = Path(sp)
        if p.is_dir():
            files.extend(sorted(p.glob("*.txt")))
        elif p.is_file():
            files.append(p)
        else:
            raise ConfigError(f"Corpus source path does not exist: {sp}")

    sources: list[SourceFile] = []
    for fp in files:
        raw = fp.read_text(encoding="utf-8")
        metadata, body = _split_frontmatter(raw)
        sha256 = hashlib.sha256(raw.encode()).hexdigest()
        sources.append(SourceFile(
            path=str(fp.absolute()),
            source=metadata.get("source", fp.stem.upper()),
            chapter=metadata.get("chapter"),
            language=metadata.get("language", "en"),
            sha256=sha256,
            char_count=len(body),
        ))

    manifest = CorpusManifest(
        sources=sources,
        created_at=datetime.now(timezone.utc).isoformat(),
        total_chars=sum(s.char_count for s in sources),
    )

    (output / "manifest.json").write_text(manifest.model_dump_json(indent=2))
    return manifest


def load_manifest(manifest_path: str) -> CorpusManifest:
    """Load a previously saved manifest from disk."""
    return CorpusManifest.model_validate_json(Path(manifest_path).read_text())
