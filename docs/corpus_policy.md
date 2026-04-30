# Corpus Policy

Guidelines for the Vedic AI knowledge corpus — what sources qualify, how they are licensed, how text is prepared, and how chunks are attributed.

## Source categories

### Tier 1 — Classical Jyotish texts (preferred)

Public-domain Sanskrit texts and their published English translations. These are the authoritative sources for rule `source_refs`.

| Text                          | Abbreviation | Notes |
|-------------------------------|--------------|-------|
| Brihat Parashara Hora Shastra | BPHS         | Primary classical authority |
| Phaladeepika                  | Phal         | Chapter/verse citations preferred |
| Saravali                      | Sara         | |
| Jataka Parijata               | JP           | |
| Hora Sara                     | HS           | |

Citations in `source_refs` fields use the format `"BPHS 24.5"` (text abbreviation, chapter, verse).

### Tier 2 — Contemporary Jyotish commentary

Scholarly commentary that explains classical rules with modern language. Include only works where redistribution rights are verified. Metadata must record the edition, publisher, and year.

### Tier 3 — Structured reference tables

Machine-generated tables derived from classical rules (planet dignities, house lordships, nakshatra padas, dasha years). These are deterministic and need no citation beyond the rule source.

## What is excluded

- Astrological interpretation blogs or social media posts.
- Astrology software output or generated commentary.
- Non-Jyotish traditions (tropical astrology, Chinese astrology, tarot).
- Any source where redistribution rights have not been confirmed.
- Personal chart readings or case studies without the subject's consent.

## Text preparation

1. **Normalize unicode** — convert Devanagari transliterations to IAST or a consistent ASCII scheme before indexing.
2. **Strip footnotes and TOC** — footnotes and page headers are noisy; remove before chunking.
3. **Preserve chapter/verse provenance** — each chunk must retain the source text abbreviation, chapter, and verse (or page range for prose) as metadata.
4. **Clean OCR artifacts** — manual review required for scanned texts with OCR errors before ingestion.

## Chunking parameters (Phase 5)

```python
chunk_size    = 600   # characters (not tokens)
overlap       = 100   # characters of trailing context carried into next chunk
min_chunk     = 100   # discard fragments smaller than this
```

Chunks that cross a verse boundary must include the full verse. Splitting in the middle of a verse is forbidden.

## Chunk metadata schema

Every `CorpusChunk` must carry:

```json
{
  "chunk_id":    "bphs_24_005_0",
  "source":      "BPHS",
  "chapter":     24,
  "verse_start": 5,
  "verse_end":   5,
  "text":        "…chunk text…",
  "char_offset": 1240,
  "language":    "en"
}
```

`chunk_id` format: `{source_abbrev}_{chapter:03d}_{verse:03d}_{seq}`.

## Vector index policy

- Index backend: FAISS `IndexFlatIP` (inner product on L2-normalised embeddings = cosine similarity).
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (Phase 5 default).
- Index is rebuilt from scratch when any source document changes. Incremental updates are not supported in the Phase 5 implementation.
- The corpus manifest (`CorpusManifest`) records the SHA-256 of each source file and the embedding model name so the index can be reproduced deterministically.

## Attribution in predictions

Every `RetrievedPassage` surfaced by the retriever must carry its `chunk_id`. The prompt builder must render source references in the generated output so human reviewers can verify claims against the original texts.

## Corpus growth process

1. Propose the new source in a PR with: title, edition, license confirmation, and sample 50-line extract.
2. Obtain at least one maintainer approval before ingesting.
3. Add the source to the manifest in `data/corpus/` with a `source_meta.yaml` entry.
4. Run `ingest_corpus()` and `build_vector_index()`, then commit the updated manifest (not the index binary itself).
