"""Retriever: embed a query and search the FAISS index for supporting passages."""

from __future__ import annotations

from typing import Any

import numpy as np

from vedic_ai.domain.corpus import CorpusChunk, RetrievedPassage, VectorIndexHandle


class Retriever:
    """Holds a loaded FAISS index and chunk lookup for repeated retrieval calls."""

    def __init__(
        self,
        chunks: list[CorpusChunk],
        index: Any,
        handle: VectorIndexHandle,
        model: Any,
    ) -> None:
        self._chunks: dict[str, CorpusChunk] = {c.chunk_id: c for c in chunks}
        self._index = index
        self._handle = handle
        self._model = model

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievedPassage]:
        """Embed query and return the top-k most relevant passages.

        filters: optional dict with key 'source' to restrict results to one source.
        Scores are cosine similarities (via inner product on L2-normalised vectors).
        """
        query_vec = self._model.encode(
            [query], normalize_embeddings=True, convert_to_numpy=True
        ).astype("float32")

        k = min(top_k, len(self._handle.chunk_ids))
        scores, indices = self._index.search(query_vec, k)

        passages: list[RetrievedPassage] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk_id = self._handle.chunk_ids[idx]
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                continue
            if filters and "source" in filters:
                if chunk.source != filters["source"]:
                    continue
            passages.append(RetrievedPassage(
                chunk_id=chunk_id,
                text=chunk.text,
                source=chunk.source,
                score=float(score),
                metadata={"chapter": chunk.chapter, **chunk.metadata},
            ))

        return passages[:top_k]


def create_retriever(
    chunks: list[CorpusChunk],
    handle: VectorIndexHandle,
    model_name: str | None = None,
) -> Retriever:
    """Instantiate a Retriever by loading the FAISS index and embedding model.

    Raises:
        ImportError: when faiss-cpu or sentence-transformers is not installed.
    """
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "faiss-cpu and sentence-transformers are required for retrieval."
        ) from exc

    faiss_index = faiss.read_index(handle.index_path)
    model = SentenceTransformer(model_name or handle.model_name)
    return Retriever(chunks, faiss_index, handle, model)


def retrieve_supporting_passages(
    retriever: Retriever,
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> list[RetrievedPassage]:
    """Module-level convenience wrapper around Retriever.retrieve."""
    return retriever.retrieve(query, top_k=top_k, filters=filters)
