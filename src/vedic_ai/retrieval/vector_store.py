"""Vector index: build and persist a FAISS IndexFlatIP from an EmbeddingBatch."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from vedic_ai.domain.corpus import EmbeddingBatch, VectorIndexHandle


def build_vector_index(
    embeddings: EmbeddingBatch,
    output_dir: str,
    backend: str = "faiss",
) -> VectorIndexHandle:
    """Build and persist a vector index from the embedding batch.

    Saves two files to output_dir:
    - faiss.index  — the FAISS binary index
    - handle.json  — VectorIndexHandle metadata (chunk_ids, model_name, dim, paths)

    Returns the VectorIndexHandle for use by the Retriever.

    Raises:
        ImportError: when faiss-cpu is not installed.
        ValueError: when the embeddings list is empty.
    """
    if not embeddings.chunk_ids:
        raise ValueError("Cannot build a vector index from an empty EmbeddingBatch")

    try:
        import faiss
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "faiss-cpu is required for vector indexing. "
            "Install it with: pip install faiss-cpu"
        ) from exc

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    vectors = np.array(embeddings.embeddings, dtype="float32")
    index = faiss.IndexFlatIP(embeddings.dim)
    index.add(vectors)

    index_path = str(output / "faiss.index")
    handle_path = str(output / "handle.json")

    faiss.write_index(index, index_path)

    handle = VectorIndexHandle(
        index_path=index_path,
        handle_path=handle_path,
        chunk_ids=list(embeddings.chunk_ids),
        model_name=embeddings.model_name,
        dim=embeddings.dim,
    )
    Path(handle_path).write_text(handle.model_dump_json(indent=2))
    return handle


def load_vector_index(handle_path: str) -> tuple[VectorIndexHandle, object]:
    """Load a persisted VectorIndexHandle and its FAISS index.

    Returns:
        (handle, faiss_index) — handle carries metadata; faiss_index is the live index.
    """
    try:
        import faiss
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "faiss-cpu is required. Install it with: pip install faiss-cpu"
        ) from exc

    handle = VectorIndexHandle.model_validate_json(Path(handle_path).read_text())
    faiss_index = faiss.read_index(handle.index_path)
    return handle, faiss_index
