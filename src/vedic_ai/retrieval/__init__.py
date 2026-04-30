"""Retrieval layer: corpus ingestion, chunking, embedding, and vector search."""

from vedic_ai.retrieval.chunker import chunk_corpus_documents
from vedic_ai.retrieval.corpus_loader import ingest_corpus, load_manifest
from vedic_ai.retrieval.embedder import embed_corpus_chunks
from vedic_ai.retrieval.retriever import Retriever, create_retriever, retrieve_supporting_passages
from vedic_ai.retrieval.vector_store import build_vector_index, load_vector_index

__all__ = [
    "ingest_corpus",
    "load_manifest",
    "chunk_corpus_documents",
    "embed_corpus_chunks",
    "build_vector_index",
    "load_vector_index",
    "Retriever",
    "create_retriever",
    "retrieve_supporting_passages",
]
