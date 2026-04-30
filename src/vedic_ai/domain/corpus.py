"""Domain types for corpus ingestion, chunking, embeddings, and retrieval."""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


class SourceFile(BaseModel):
    path: str
    source: str
    chapter: int | None = None
    language: str = "en"
    sha256: str
    char_count: int


class CorpusManifest(BaseModel):
    manifest_id: str = Field(default_factory=lambda: str(uuid4()))
    sources: list[SourceFile] = Field(default_factory=list)
    created_at: str
    total_chars: int = 0


class CorpusChunk(BaseModel):
    chunk_id: str
    source: str
    chapter: int | None = None
    text: str
    char_offset: int
    language: str = "en"
    metadata: dict = Field(default_factory=dict)


class EmbeddingBatch(BaseModel):
    chunk_ids: list[str]
    embeddings: list[list[float]]
    model_name: str
    dim: int


class VectorIndexHandle(BaseModel):
    index_path: str
    handle_path: str
    chunk_ids: list[str]
    model_name: str
    dim: int


class RetrievedPassage(BaseModel):
    chunk_id: str
    text: str
    source: str
    score: float
    metadata: dict = Field(default_factory=dict)
