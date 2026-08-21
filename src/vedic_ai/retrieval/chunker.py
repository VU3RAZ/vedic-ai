"""Corpus chunker: split ingested text into overlapping retrieval chunks."""

from __future__ import annotations

import bisect
import re
from pathlib import Path

from vedic_ai.domain.corpus import CorpusChunk, CorpusManifest
from vedic_ai.retrieval.corpus_loader import _split_frontmatter, filter_garbled_lines

# Sentence-ending punctuation (incl. Sanskrit daṇḍa/double-daṇḍa) followed by
# whitespace/end-of-text, or a paragraph break (blank line).
_BOUNDARY_RE = re.compile(r"[.!?।॥](?=\s|$)|\n\s*\n")


def _find_boundaries(text: str) -> list[int]:
    """Return sorted end-of-sentence/paragraph offsets within text."""
    return [m.end() for m in _BOUNDARY_RE.finditer(text)]


def _snap_to_boundary(boundaries: list[int], floor: int, hard_end: int) -> int | None:
    """Return the latest boundary in (floor, hard_end], or None if none qualifies."""
    idx = bisect.bisect_right(boundaries, hard_end)
    if idx == 0:
        return None
    candidate = boundaries[idx - 1]
    if candidate < floor:
        return None
    return candidate


def _chunk_text(
    text: str,
    source: str,
    chapter: int | None,
    chunk_size: int,
    overlap: int,
    min_chunk: int,
    seq_start: int = 0,
) -> list[CorpusChunk]:
    """Split text into overlapping, sentence-aware chunks.

    Each chunk grows up to chunk_size characters, but its end is snapped back
    to the nearest sentence or paragraph boundary (when one exists past the
    chunk's midpoint) so chunks don't split a sentence in half. Text with no
    recognizable sentence punctuation (e.g. a single long word/run) falls
    back to a hard character cut at chunk_size, identical to plain windowing.

    The final fragment is discarded only when it is shorter than min_chunk AND
    there are already other chunks (so a single short document still produces
    one chunk).
    """
    if not text.strip():
        return []

    source_lower = source.lower()
    chapter_str = f"{chapter:03d}" if chapter is not None else "000"
    boundaries = _find_boundaries(text)

    chunks: list[CorpusChunk] = []
    start = 0

    while start < len(text):
        hard_end = min(start + chunk_size, len(text))
        end = hard_end

        if hard_end < len(text):
            floor = start + max(min_chunk, chunk_size // 2)
            snapped = _snap_to_boundary(boundaries, floor, hard_end)
            if snapped is not None:
                end = snapped

        chunk_text = text[start:end]

        if len(chunk_text) < min_chunk and chunks:
            break

        seq = seq_start + len(chunks)
        chunk_id = f"{source_lower}_{chapter_str}_{seq:04d}"
        chunks.append(CorpusChunk(
            chunk_id=chunk_id,
            source=source,
            chapter=chapter,
            text=chunk_text,
            char_offset=start,
        ))

        if end == len(text):
            break

        next_start = end - overlap
        while next_start < len(text) and text[next_start] in " \t\n\r":
            next_start += 1
        if next_start <= start:
            next_start = start + 1
        start = next_start

    return chunks


def chunk_corpus_documents(
    manifest: CorpusManifest,
    chunk_size: int = 600,
    overlap: int = 100,
    min_chunk: int = 100,
) -> list[CorpusChunk]:
    """Split every source file in the manifest into overlapping text chunks.

    chunk_size: maximum characters per chunk
    overlap:    trailing characters shared with the next chunk
    min_chunk:  trailing fragments smaller than this are discarded
    """
    all_chunks: list[CorpusChunk] = []
    for sf in manifest.sources:
        raw = Path(sf.path).read_text(encoding="utf-8")
        _, body = _split_frontmatter(raw)
        body = filter_garbled_lines(body).strip()
        chunks = _chunk_text(
            body,
            sf.source,
            sf.chapter,
            chunk_size,
            overlap,
            min_chunk,
        )
        all_chunks.extend(chunks)
    return all_chunks
