"""Integration tests for the full corpus ingestion → retrieval pipeline.

Requires:  pip install sentence-transformers faiss-cpu
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")
sentence_transformers = pytest.importorskip("sentence_transformers")

from vedic_ai.retrieval import (
    build_vector_index,
    chunk_corpus_documents,
    create_retriever,
    embed_corpus_chunks,
    ingest_corpus,
    load_vector_index,
)

# ---------------------------------------------------------------------------
# Shared paths
# ---------------------------------------------------------------------------

CORPUS_DIR = Path(__file__).parents[2] / "data" / "corpus" / "texts"
MODEL_NAME = "all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Session-scoped fixtures — build index once for all tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def corpus_dir():
    assert CORPUS_DIR.exists(), f"Seed corpus not found at {CORPUS_DIR}"
    return CORPUS_DIR


@pytest.fixture(scope="session")
def manifest(tmp_path_factory, corpus_dir):
    out = tmp_path_factory.mktemp("retrieval") / "out"
    return ingest_corpus([str(corpus_dir)], str(out))


@pytest.fixture(scope="session")
def chunks(manifest):
    return chunk_corpus_documents(manifest, chunk_size=600, overlap=100)


@pytest.fixture(scope="session")
def embedding_batch(chunks):
    return embed_corpus_chunks(chunks, model_name=MODEL_NAME)


@pytest.fixture(scope="session")
def index_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("index")


@pytest.fixture(scope="session")
def handle(embedding_batch, index_dir):
    return build_vector_index(embedding_batch, str(index_dir))


@pytest.fixture(scope="session")
def retriever(chunks, handle):
    return create_retriever(chunks, handle, MODEL_NAME)


# ---------------------------------------------------------------------------
# Ingestion tests
# ---------------------------------------------------------------------------

class TestIngestion:
    def test_manifest_has_four_sources(self, manifest):
        assert len(manifest.sources) == 4

    def test_all_sources_are_bphs(self, manifest):
        assert all(s.source == "BPHS" for s in manifest.sources)

    def test_chapters_covered(self, manifest):
        chapters = {s.chapter for s in manifest.sources}
        assert {15, 23, 24, 35}.issubset(chapters)

    def test_all_sha256_set(self, manifest):
        for sf in manifest.sources:
            assert len(sf.sha256) == 64

    def test_total_chars_positive(self, manifest):
        assert manifest.total_chars > 0

    def test_manifest_json_saved(self, manifest, tmp_path):
        out = tmp_path / "out2"
        m2 = ingest_corpus(
            [str(Path(sf.path).parent) for sf in manifest.sources[:1]],
            str(out),
        )
        assert (out / "manifest.json").exists()


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

class TestChunking:
    def test_chunk_count_sufficient(self, chunks):
        assert len(chunks) >= 10

    def test_all_chunks_have_source(self, chunks):
        assert all(c.source != "" for c in chunks)

    def test_all_chunks_have_chapter(self, chunks):
        assert all(c.chapter is not None for c in chunks)

    def test_chunk_ids_unique(self, chunks):
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_ids_follow_format(self, chunks):
        for c in chunks:
            parts = c.chunk_id.split("_")
            assert len(parts) == 3
            assert parts[1].isdigit()
            assert parts[2].isdigit()

    def test_all_chapters_represented(self, chunks):
        chapters = {c.chapter for c in chunks}
        assert {15, 23, 24, 35}.issubset(chapters)

    def test_chunk_text_nonempty(self, chunks):
        assert all(len(c.text) > 0 for c in chunks)


# ---------------------------------------------------------------------------
# Embedding tests
# ---------------------------------------------------------------------------

class TestEmbedding:
    def test_chunk_ids_match_chunks(self, embedding_batch, chunks):
        assert len(embedding_batch.chunk_ids) == len(chunks)

    def test_embedding_dim(self, embedding_batch):
        assert embedding_batch.dim == 384  # all-MiniLM-L6-v2 output dim

    def test_embedding_shape(self, embedding_batch):
        assert len(embedding_batch.embeddings) == len(embedding_batch.chunk_ids)
        assert all(len(e) == embedding_batch.dim for e in embedding_batch.embeddings)

    def test_embeddings_l2_normalized(self, embedding_batch):
        vecs = np.array(embedding_batch.embeddings, dtype="float32")
        norms = np.linalg.norm(vecs, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_model_name_recorded(self, embedding_batch):
        assert embedding_batch.model_name == MODEL_NAME


# ---------------------------------------------------------------------------
# Vector index tests
# ---------------------------------------------------------------------------

class TestVectorIndex:
    def test_handle_chunk_ids_match(self, handle, chunks):
        assert len(handle.chunk_ids) == len(chunks)

    def test_handle_files_exist(self, handle):
        assert Path(handle.index_path).exists()
        assert Path(handle.handle_path).exists()

    def test_handle_dim(self, handle):
        assert handle.dim == 384

    def test_load_index_roundtrip(self, handle):
        loaded_handle, loaded_index = load_vector_index(handle.handle_path)
        assert loaded_handle.chunk_ids == handle.chunk_ids
        assert loaded_handle.dim == handle.dim
        assert loaded_index.ntotal == len(handle.chunk_ids)

    def test_empty_batch_raises(self, tmp_path):
        from vedic_ai.domain.corpus import EmbeddingBatch
        empty = EmbeddingBatch(chunk_ids=[], embeddings=[], model_name=MODEL_NAME, dim=384)
        with pytest.raises(ValueError):
            build_vector_index(empty, str(tmp_path / "empty_idx"))


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------

class TestRetrieval:
    def test_career_query_returns_results(self, retriever):
        passages = retriever.retrieve("Sun in tenth house career prominence authority", top_k=5)
        assert len(passages) > 0

    def test_career_query_includes_chapter_24(self, retriever):
        passages = retriever.retrieve("Sun in tenth house career prominence authority", top_k=5)
        chapters = [p.metadata.get("chapter") for p in passages]
        assert 24 in chapters

    def test_relationships_query_includes_chapter_23(self, retriever):
        passages = retriever.retrieve("marriage partner seventh house Venus Jupiter", top_k=5)
        chapters = [p.metadata.get("chapter") for p in passages]
        assert 23 in chapters

    def test_yoga_query_includes_chapter_35(self, retriever):
        passages = retriever.retrieve("Gajakesari yoga Jupiter Moon kendra intelligence", top_k=5)
        chapters = [p.metadata.get("chapter") for p in passages]
        assert 35 in chapters

    def test_personality_query_includes_chapter_15(self, retriever):
        passages = retriever.retrieve("Sun Moon Jupiter Lagna personality temperament", top_k=5)
        chapters = [p.metadata.get("chapter") for p in passages]
        assert 15 in chapters

    def test_top_k_respected(self, retriever):
        passages = retriever.retrieve("career", top_k=3)
        assert len(passages) <= 3

    def test_scores_descending(self, retriever):
        passages = retriever.retrieve("Saturn discipline career patience", top_k=5)
        scores = [p.score for p in passages]
        assert scores == sorted(scores, reverse=True)

    def test_passage_fields_populated(self, retriever):
        passages = retriever.retrieve("career", top_k=1)
        assert len(passages) == 1
        p = passages[0]
        assert p.chunk_id
        assert p.text
        assert p.source == "BPHS"
        assert isinstance(p.score, float)

    def test_filter_by_source(self, retriever):
        passages = retriever.retrieve("planets and houses", top_k=5, filters={"source": "BPHS"})
        assert all(p.source == "BPHS" for p in passages)

    def test_scores_in_valid_range(self, retriever):
        passages = retriever.retrieve("Vedic astrology", top_k=5)
        for p in passages:
            assert -1.0 <= p.score <= 1.0

    def test_retrieve_supporting_passages_wrapper(self, retriever):
        from vedic_ai.retrieval import retrieve_supporting_passages
        passages = retrieve_supporting_passages(retriever, "Jupiter wisdom career", top_k=3)
        assert len(passages) <= 3
