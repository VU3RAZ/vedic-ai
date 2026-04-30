"""CLI commands for corpus ingestion and index building."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer

from vedic_ai.cli.main import app

logger = logging.getLogger(__name__)

_DEFAULT_TEXTS_DIR = "data/corpus/texts"
_DEFAULT_PROCESSED_DIR = "data/processed/corpus"
_DEFAULT_INDEX_DIR = "data/processed"


@app.command("build-index")
def build_index(
    texts_dir: Path = typer.Option(
        _DEFAULT_TEXTS_DIR,
        "--texts-dir",
        "-t",
        help="Directory containing .txt corpus files.",
    ),
    output_dir: Path = typer.Option(
        _DEFAULT_INDEX_DIR,
        "--output-dir",
        "-o",
        help="Directory where faiss.index and handle.json are written.",
    ),
    corpus_dir: Path = typer.Option(
        _DEFAULT_PROCESSED_DIR,
        "--corpus-dir",
        help="Directory where manifest.json is written.",
    ),
    chunk_size: int = typer.Option(600, "--chunk-size", help="Max characters per chunk."),
    overlap: int = typer.Option(100, "--overlap", help="Overlap characters between chunks."),
    embedding_model: str = typer.Option(
        "all-MiniLM-L6-v2",
        "--model",
        "-m",
        help="SentenceTransformer model name.",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Rebuild even if index already exists."
    ),
) -> None:
    """Ingest text corpus, embed chunks, and build the FAISS retrieval index."""
    index_path = output_dir / "faiss.index"
    handle_path = output_dir / "handle.json"

    if index_path.exists() and handle_path.exists() and not force:
        typer.echo(
            f"Index already exists at {index_path}. Use --force to rebuild.",
            err=False,
        )
        raise typer.Exit(code=0)

    if not texts_dir.exists():
        typer.echo(f"Texts directory not found: {texts_dir}", err=True)
        raise typer.Exit(code=1)

    try:
        from vedic_ai.retrieval.corpus_loader import ingest_corpus
        from vedic_ai.retrieval.chunker import chunk_corpus_documents
        from vedic_ai.retrieval.embedder import embed_corpus_chunks
        from vedic_ai.retrieval.vector_store import build_vector_index
    except ImportError as exc:
        typer.echo(f"Missing dependency: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[1/4] Ingesting corpus from {texts_dir} ...")
    try:
        manifest = ingest_corpus(
            source_paths=[str(texts_dir)],
            output_dir=str(corpus_dir),
        )
    except Exception as exc:
        typer.echo(f"Ingestion failed: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(
        f"       {len(manifest.sources)} sources — "
        f"{manifest.total_chars:,} total chars"
    )

    typer.echo("[2/4] Chunking ...")
    chunks = chunk_corpus_documents(manifest, chunk_size=chunk_size, overlap=overlap)
    typer.echo(f"       {len(chunks):,} chunks produced")

    typer.echo(f"[3/4] Embedding with {embedding_model!r} (this may take a few minutes) ...")
    try:
        batch = embed_corpus_chunks(chunks, model_name=embedding_model)
    except ImportError as exc:
        typer.echo(f"Embedding dependency missing: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"       {len(batch.chunk_ids):,} vectors — dim={batch.dim}")

    typer.echo(f"[4/4] Building FAISS index in {output_dir} ...")
    try:
        handle = build_vector_index(batch, output_dir=str(output_dir))
    except ImportError as exc:
        typer.echo(f"FAISS dependency missing: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"\nIndex ready:")
    typer.echo(f"  FAISS index : {handle.index_path}")
    typer.echo(f"  Handle      : {handle.handle_path}")
    typer.echo(f"  Vectors     : {len(handle.chunk_ids):,}")
    typer.echo(f"  Model       : {handle.model_name}")


@app.command("corpus-info")
def corpus_info(
    corpus_dir: Path = typer.Option(
        _DEFAULT_PROCESSED_DIR,
        "--corpus-dir",
        help="Directory containing manifest.json.",
    ),
    index_dir: Path = typer.Option(
        _DEFAULT_INDEX_DIR,
        "--index-dir",
        help="Directory containing handle.json.",
    ),
) -> None:
    """Show corpus manifest and index status."""
    manifest_path = corpus_dir / "manifest.json"
    handle_path = index_dir / "handle.json"

    if manifest_path.exists():
        data = json.loads(manifest_path.read_text())
        typer.echo(f"Corpus manifest: {manifest_path}")
        typer.echo(f"  Sources     : {len(data.get('sources', []))}")
        typer.echo(f"  Total chars : {data.get('total_chars', 0):,}")
        typer.echo(f"  Created     : {data.get('created_at', 'unknown')}")
        for src in data.get("sources", []):
            ch = src.get("chapter")
            ch_str = f" ch.{ch}" if ch else ""
            typer.echo(f"    {src['source']}{ch_str}  ({src['char_count']:,} chars)")
    else:
        typer.echo(f"No manifest found at {manifest_path}. Run build-index first.")

    typer.echo("")

    if handle_path.exists():
        handle = json.loads(handle_path.read_text())
        index_path = Path(handle.get("index_path", ""))
        typer.echo(f"FAISS index: {handle_path}")
        typer.echo(f"  Vectors    : {len(handle.get('chunk_ids', [])):,}")
        typer.echo(f"  Model      : {handle.get('model_name', 'unknown')}")
        typer.echo(f"  Dim        : {handle.get('dim', 'unknown')}")
        typer.echo(f"  Index file : {'EXISTS' if index_path.exists() else 'MISSING'}")
    else:
        typer.echo(f"No index handle found at {handle_path}. Run build-index first.")


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Query string to search for relevant passages."),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of passages to return."),
    index_dir: Path = typer.Option(
        _DEFAULT_INDEX_DIR,
        "--index-dir",
        help="Directory containing handle.json and faiss.index.",
    ),
    texts_dir: Path = typer.Option(
        _DEFAULT_TEXTS_DIR,
        "--texts-dir",
        help="Directory of source .txt files (to load chunk text).",
    ),
    corpus_dir: Path = typer.Option(
        _DEFAULT_PROCESSED_DIR,
        "--corpus-dir",
        help="Directory containing manifest.json.",
    ),
) -> None:
    """Search the FAISS index for passages relevant to a query."""
    handle_path = index_dir / "handle.json"
    if not handle_path.exists():
        typer.echo("Index not found. Run build-index first.", err=True)
        raise typer.Exit(code=1)

    try:
        from vedic_ai.retrieval.corpus_loader import ingest_corpus, load_manifest
        from vedic_ai.retrieval.chunker import chunk_corpus_documents
        from vedic_ai.retrieval.vector_store import load_vector_index
        from vedic_ai.retrieval.retriever import create_retriever
    except ImportError as exc:
        typer.echo(f"Missing dependency: {exc}", err=True)
        raise typer.Exit(code=1)

    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.exists():
        typer.echo("Manifest not found. Run build-index first.", err=True)
        raise typer.Exit(code=1)

    manifest = load_manifest(str(manifest_path))
    chunks = chunk_corpus_documents(manifest)
    handle, _ = load_vector_index(str(handle_path))
    retriever = create_retriever(chunks, handle)

    passages = retriever.retrieve(query, top_k=top_k)

    if not passages:
        typer.echo("No passages found.")
        raise typer.Exit(code=0)

    for i, p in enumerate(passages, 1):
        ch = p.metadata.get("chapter")
        source_label = f"{p.source}" + (f" ch.{ch}" if ch else "")
        typer.echo(f"\n--- [{i}] {source_label}  score={p.score:.4f} ---")
        typer.echo(p.text[:500] + ("..." if len(p.text) > 500 else ""))
