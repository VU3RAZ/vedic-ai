"""Corpus chunker: split ingested text into overlapping retrieval chunks."""

from __future__ import annotations

from pathlib import Path

from vedic_ai.domain.corpus import CorpusChunk, CorpusManifest
from vedic_ai.retrieval.corpus_loader import _split_frontmatter


def _chunk_text(
    text: str,
    source: str,
    chapter: int | None,
    chunk_size: int,
    overlap: int,
    min_chunk: int,
    seq_start: int = 0,
) -> list[CorpusChunk]:
    """Split text into overlapping character-based chunks.

    The final fragment is discarded only when it is shorter than min_chunk AND
    there are already other chunks (so a single short document still produces
    one chunk).
    """
    if not text.strip():
        return []

    step = chunk_size - overlap
    source_lower = source.lower()
    chapter_str = f"{chapter:03d}" if chapter is not None else "000"

    chunks: list[CorpusChunk] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
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
        start += step

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
        body = body.strip()
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
