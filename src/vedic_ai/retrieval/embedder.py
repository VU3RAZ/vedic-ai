"""Corpus embedder: generate L2-normalised sentence embeddings for corpus chunks."""

from __future__ import annotations

from vedic_ai.domain.corpus import CorpusChunk, EmbeddingBatch

_DEFAULT_MODEL = "all-MiniLM-L6-v2"


def embed_corpus_chunks(
    chunks: list[CorpusChunk],
    model_name: str = _DEFAULT_MODEL,
) -> EmbeddingBatch:
    """Embed each chunk's text using a SentenceTransformer model.

    Embeddings are L2-normalised so inner product equals cosine similarity,
    which is required for FAISS IndexFlatIP.

    Raises:
        ImportError: when sentence-transformers is not installed.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "sentence-transformers is required for embedding. "
            "Install it with: pip install sentence-transformers"
        ) from exc

    model = SentenceTransformer(model_name)
    texts = [c.text for c in chunks]
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    return EmbeddingBatch(
        chunk_ids=[c.chunk_id for c in chunks],
        embeddings=vectors.tolist(),
        model_name=model_name,
        dim=int(vectors.shape[1]),
    )
