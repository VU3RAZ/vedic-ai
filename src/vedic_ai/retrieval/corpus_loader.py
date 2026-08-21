"""Corpus ingestion: read source text files, parse frontmatter, build a manifest."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from vedic_ai.core.exceptions import ConfigError
from vedic_ai.domain.corpus import CorpusManifest, SourceFile

# Some corpus sources (e.g. the Santhanam BPHS scans) are OCR'd from
# Devanagari originals; failed transliteration leaves lines of Latin-script
# noise like "ft*T *TT*5m" interleaved with clean English commentary.
_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'\-]*$")
_OCR_NOISE_CHARS = set("*^~«»\\|„”¢£¥§¤¬¦¡¿")
_MID_TOKEN_CASE_FLIP_RE = re.compile(r"[a-z][A-Z]")


def _word_flag(word: str) -> str:
    """Classify a whitespace-split token as 'real' English, OCR 'noise'/'junk', or 'skip'."""
    core = word.strip(".,;:!?()[]{}\"'‘’“”-–—")
    if not core:
        return "skip"
    if any(c in _OCR_NOISE_CHARS for c in core):
        return "noise"
    if _MID_TOKEN_CASE_FLIP_RE.search(core[1:]):
        return "noise"
    alpha = sum(c.isalpha() for c in core)
    if alpha == 0:
        return "skip"
    vowel_ratio = sum(c in "aeiouAEIOU" for c in core) / alpha
    if _WORD_RE.match(core) and vowel_ratio > 0.15:
        return "real"
    return "junk"


def _is_garbled_line(line: str, min_len: int = 8) -> bool:
    """Detect an OCR-mangled line.

    Deliberately conservative — tuned to produce zero false positives across
    hand-authored corpus texts (headers, numeric lists, ISBN/citation lines),
    at the cost of missing some genuine OCR garbage. Only flags a line when
    it has no recognizable English word at all and is mostly noise/junk
    tokens.
    """
    stripped = line.strip()
    if len(stripped) < min_len:
        return False
    scored = [f for f in (_word_flag(w) for w in stripped.split()) if f != "skip"]
    if len(scored) < 2:
        return False
    bad = sum(1 for f in scored if f in ("noise", "junk"))
    real = sum(1 for f in scored if f == "real")
    return real == 0 and bad / len(scored) > 0.6


def filter_garbled_lines(text: str) -> str:
    """Drop OCR-garbled lines from text, preserving the rest as-is."""
    kept = [line for line in text.splitlines() if not _is_garbled_line(line)]
    return "\n".join(kept)


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
