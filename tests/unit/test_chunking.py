"""Unit tests for corpus_loader.py, chunker.py, and domain corpus types."""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

import pytest

from vedic_ai.core.exceptions import ConfigError
from vedic_ai.domain.corpus import (
    CorpusChunk,
    CorpusManifest,
    EmbeddingBatch,
    SourceFile,
)
from vedic_ai.retrieval.chunker import _chunk_text, chunk_corpus_documents
from vedic_ai.retrieval.corpus_loader import _split_frontmatter, ingest_corpus, load_manifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BODY_TEXT = (
    "The Sun in the tenth house confers prominence and authority in career. "
    "Saturn builds discipline and endurance over a long professional life. "
    "Jupiter bestows wisdom and ethical conduct in advisory roles. "
    "Mars provides energy and leadership in competitive professional fields. "
    "The tenth house lord in a kendra gives a solid career foundation. "
    "An exalted tenth lord produces outstanding achievement and high status. "
    "The Lagna lord in the tenth house ties identity to career ambition. "
    "Planetary dignity strongly shapes the quality of career outcomes. "
    "Venus in the seventh house indicates a charming and refined partner. "
    "Moon in the Lagna gives emotional sensitivity and intuitive insight. "
)


def _make_corpus_file(tmp_path: Path, filename: str, source: str, chapter: int, body: str) -> Path:
    fp = tmp_path / filename
    fp.write_text(
        f"---\nsource: {source}\nchapter: {chapter}\nlanguage: en\n---\n\n{body}",
        encoding="utf-8",
    )
    return fp


# ---------------------------------------------------------------------------
# TestSplitFrontmatter
# ---------------------------------------------------------------------------

class TestSplitFrontmatter:
    def test_parses_metadata(self):
        content = "---\nsource: BPHS\nchapter: 24\n---\n\nBody text here."
        meta, body = _split_frontmatter(content)
        assert meta["source"] == "BPHS"
        assert meta["chapter"] == 24
        assert body == "Body text here."

    def test_no_frontmatter(self):
        content = "Plain text without frontmatter."
        meta, body = _split_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_missing_closing_delimiter(self):
        content = "---\nsource: BPHS\nBody goes on forever."
        meta, body = _split_frontmatter(content)
        assert meta == {}

    def test_empty_frontmatter(self):
        content = "---\n---\n\nBody only."
        meta, body = _split_frontmatter(content)
        assert meta == {}
        assert body == "Body only."


# ---------------------------------------------------------------------------
# TestChunkText
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_basic_chunks_produced(self):
        text = "A" * 1800
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        assert len(chunks) >= 3

    def test_chunk_size_respected(self):
        text = "B" * 1800
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        for c in chunks:
            assert len(c.text) <= 600

    def test_overlap_between_adjacent_chunks(self):
        text = "X" * 1200
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        assert len(chunks) >= 2
        # End of chunk 0 overlaps start of chunk 1
        end_of_first = chunks[0].text[-100:]
        start_of_second = chunks[1].text[:100]
        assert end_of_first == start_of_second

    def test_source_field_set(self):
        chunks = _chunk_text("Some text " * 100, "BPHS", 24, 600, 100, 100)
        assert all(c.source == "BPHS" for c in chunks)

    def test_chapter_field_set(self):
        chunks = _chunk_text("Some text " * 100, "BPHS", 24, 600, 100, 100)
        assert all(c.chapter == 24 for c in chunks)

    def test_chunk_id_format(self):
        chunks = _chunk_text("Some text " * 100, "BPHS", 24, 600, 100, 100)
        for i, c in enumerate(chunks):
            assert c.chunk_id == f"bphs_024_{i:04d}"

    def test_chunk_id_no_chapter(self):
        chunks = _chunk_text("Some text " * 100, "BPHS", None, 600, 100, 100)
        assert chunks[0].chunk_id == "bphs_000_0000"

    def test_char_offset_monotonic(self):
        text = "W" * 1800
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        offsets = [c.char_offset for c in chunks]
        assert offsets == sorted(offsets)
        assert offsets[0] == 0

    def test_char_offset_first_chunk(self):
        text = "Y" * 1200
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        assert chunks[0].char_offset == 0

    def test_char_offset_second_chunk(self):
        text = "Z" * 1200
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        # step = chunk_size - overlap = 500
        assert chunks[1].char_offset == 500

    def test_short_text_single_chunk(self):
        text = "Short text."
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_empty_text_no_chunks(self):
        chunks = _chunk_text("", "BPHS", 24, 600, 100, 100)
        assert chunks == []

    def test_whitespace_only_no_chunks(self):
        chunks = _chunk_text("   \n\n  ", "BPHS", 24, 600, 100, 100)
        assert chunks == []

    def test_min_chunk_trailing_fragment_discarded(self):
        # 1250 chars: first chunk [0:600], second [500:1100], third [1000:1250] = 250 chars
        # 250 > min_chunk=100 so third chunk is NOT discarded
        text = "M" * 1250
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100)
        # Last chunk text is text[1000:1250] = 250 chars, kept
        assert len(chunks[2].text) == 250

    def test_min_chunk_tiny_fragment_discarded(self):
        # Produce a trailing fragment of exactly 50 chars (< min_chunk=100)
        # 1050 chars: chunk 0 [0:600], chunk 1 [500:1050]=550 chars, no third
        # Actually 1050: step=500, chunk0=[0:600], chunk1=[500:1050]=550, end reached, done
        # To get a tiny trailing fragment we need: first chunk fills 600, second = 500+50
        # Let's use 1050 chars with step=500: chunks are [0:600], [500:1050], that's end.
        # For a tiny fragment: 1600 chars with step=500:
        #   chunk0=[0:600], chunk1=[500:1100], chunk2=[1000:1600]
        #   chunk2 is 600 chars, no fragment
        # Use 1560: chunk0=[0:600], chunk1=[500:1100], chunk2=[1000:1560]=560 chars > 100
        # To force fragment < 100: 1540: chunk2=[1000:1540]=540 > 100
        # Simplest: set chunk_size=600, overlap=100, min_chunk=200
        # text=1050: chunk0=[0:600], chunk1=[500:1050]=550, done (end reached)
        # For a fragment: text=1060: chunk0=[0:600], chunk1=[500:1100]? no, end at 1060
        #   chunk1=[500:1060]=560, end reached. No fragment.
        # OK let me do: chunk_size=200, overlap=50, min_chunk=100
        # step=150, text=380:
        #   chunk0=[0:200], chunk1=[150:350], chunk2=[300:380]=80 < 100 → discarded
        text = "N" * 380
        chunks = _chunk_text(text, "BPHS", 24, 200, 50, 100)
        assert len(chunks) == 2
        assert all(len(c.text) >= 100 for c in chunks)

    def test_seq_start_offset(self):
        text = "P" * 700
        chunks = _chunk_text(text, "BPHS", 24, 600, 100, 100, seq_start=5)
        assert chunks[0].chunk_id == "bphs_024_0005"


# ---------------------------------------------------------------------------
# TestCorpusLoader
# ---------------------------------------------------------------------------

class TestCorpusLoader:
    def test_ingest_single_file(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        assert len(manifest.sources) == 1

    def test_ingest_metadata_source(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        assert manifest.sources[0].source == "BPHS"

    def test_ingest_metadata_chapter(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        assert manifest.sources[0].chapter == 24

    def test_ingest_sha256_set(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        sha = manifest.sources[0].sha256
        assert len(sha) == 64
        assert sha.isalnum()

    def test_ingest_sha256_value(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        raw = fp.read_text(encoding="utf-8")
        expected_sha = hashlib.sha256(raw.encode()).hexdigest()
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        assert manifest.sources[0].sha256 == expected_sha

    def test_ingest_char_count(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        # _split_frontmatter strips the body, so char_count reflects stripped length
        assert manifest.sources[0].char_count == len(BODY_TEXT.strip())

    def test_ingest_total_chars(self, tmp_path):
        fp1 = _make_corpus_file(tmp_path, "a.txt", "BPHS", 23, BODY_TEXT)
        fp2 = _make_corpus_file(tmp_path, "b.txt", "BPHS", 24, BODY_TEXT)
        manifest = ingest_corpus([str(fp1), str(fp2)], str(tmp_path / "out"))
        assert manifest.total_chars == len(BODY_TEXT.strip()) * 2

    def test_ingest_directory(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        for i in range(3):
            _make_corpus_file(src_dir, f"file{i}.txt", "BPHS", i + 1, BODY_TEXT)
        manifest = ingest_corpus([str(src_dir)], str(tmp_path / "out"))
        assert len(manifest.sources) == 3

    def test_ingest_saves_manifest_json(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        out_dir = tmp_path / "out"
        ingest_corpus([str(fp)], str(out_dir))
        assert (out_dir / "manifest.json").exists()

    def test_ingest_missing_path_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            ingest_corpus([str(tmp_path / "nonexistent.txt")], str(tmp_path / "out"))

    def test_ingest_fallback_source_from_filename(self, tmp_path):
        # No frontmatter: source name derived from filename
        fp = tmp_path / "mytext.txt"
        fp.write_text("Plain body text without frontmatter.", encoding="utf-8")
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        assert manifest.sources[0].source == "MYTEXT"

    def test_load_manifest_roundtrip(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT)
        out_dir = tmp_path / "out"
        original = ingest_corpus([str(fp)], str(out_dir))
        loaded = load_manifest(str(out_dir / "manifest.json"))
        assert loaded.manifest_id == original.manifest_id
        assert loaded.total_chars == original.total_chars


# ---------------------------------------------------------------------------
# TestChunkCorpusDocuments
# ---------------------------------------------------------------------------

class TestChunkCorpusDocuments:
    def test_produces_chunks(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT * 5)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        chunks = chunk_corpus_documents(manifest, chunk_size=300, overlap=50)
        assert len(chunks) > 0

    def test_all_chunks_have_source(self, tmp_path):
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 24, BODY_TEXT * 5)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        chunks = chunk_corpus_documents(manifest)
        assert all(c.source == "BPHS" for c in chunks)

    def test_multi_file_chunks_distinct_ids(self, tmp_path):
        fp1 = _make_corpus_file(tmp_path, "a.txt", "BPHS", 23, BODY_TEXT * 5)
        fp2 = _make_corpus_file(tmp_path, "b.txt", "BPHS", 24, BODY_TEXT * 5)
        manifest = ingest_corpus([str(fp1), str(fp2)], str(tmp_path / "out"))
        chunks = chunk_corpus_documents(manifest)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids)), "chunk IDs must be unique across files"

    def test_chunk_text_content(self, tmp_path):
        body = "Hello world. " * 200
        fp = _make_corpus_file(tmp_path, "test.txt", "BPHS", 1, body)
        manifest = ingest_corpus([str(fp)], str(tmp_path / "out"))
        chunks = chunk_corpus_documents(manifest)
        # Reconstruct original from chunks via offsets
        full_body = body.strip()
        for c in chunks:
            expected = full_body[c.char_offset: c.char_offset + len(c.text)]
            assert c.text == expected


# ---------------------------------------------------------------------------
# TestEmbeddingBatchModel
# ---------------------------------------------------------------------------

class TestEmbeddingBatchModel:
    def test_batch_structure(self):
        batch = EmbeddingBatch(
            chunk_ids=["a", "b", "c"],
            embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
            model_name="test",
            dim=2,
        )
        assert len(batch.chunk_ids) == len(batch.embeddings)

    def test_batch_dim_field(self):
        batch = EmbeddingBatch(
            chunk_ids=["a"],
            embeddings=[[0.1, 0.2, 0.3]],
            model_name="test",
            dim=3,
        )
        assert batch.dim == 3

    def test_batch_roundtrip(self):
        batch = EmbeddingBatch(
            chunk_ids=["x"],
            embeddings=[[1.0, 0.0]],
            model_name="mock",
            dim=2,
        )
        restored = EmbeddingBatch.model_validate(batch.model_dump())
        assert restored.chunk_ids == batch.chunk_ids
        assert restored.dim == batch.dim
