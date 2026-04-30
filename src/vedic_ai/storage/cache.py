"""SQLite-backed cache for ChartBundle objects."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from vedic_ai.domain.birth import BirthData
from vedic_ai.domain.chart import ChartBundle, deserialize_chart_bundle, serialize_chart_bundle

_DEFAULT_DB_PATH = Path("data/processed/chart_cache.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS chart_cache (
    cache_key TEXT PRIMARY KEY,
    bundle_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def _get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def build_cache_key(birth: BirthData, options: dict | None = None) -> str:
    """Return a deterministic SHA-256 cache key for a birth + options pair."""
    birth_json = birth.model_dump_json()
    options_json = json.dumps(options or {}, sort_keys=True)
    raw = birth_json + options_json
    return hashlib.sha256(raw.encode()).hexdigest()


def cache_chart_bundle(
    cache_key: str,
    bundle: ChartBundle,
    db_path: Path | None = None,
) -> None:
    """Persist a ChartBundle keyed by cache_key in SQLite.

    Silently replaces any existing entry with the same key.
    """
    db = db_path or _DEFAULT_DB_PATH
    conn = _get_connection(db)
    payload = json.dumps(serialize_chart_bundle(bundle))
    conn.execute(
        "INSERT OR REPLACE INTO chart_cache (cache_key, bundle_json) VALUES (?, ?)",
        (cache_key, payload),
    )
    conn.commit()
    conn.close()


def load_cached_chart_bundle(
    cache_key: str,
    db_path: Path | None = None,
) -> ChartBundle | None:
    """Return the cached ChartBundle for cache_key, or None if not found.

    The returned bundle is validated against the current schema; stale entries
    that fail validation are treated as cache misses.
    """
    db = db_path or _DEFAULT_DB_PATH
    if not db.exists():
        return None
    conn = _get_connection(db)
    row = conn.execute(
        "SELECT bundle_json FROM chart_cache WHERE cache_key = ?", (cache_key,)
    ).fetchone()
    conn.close()

    if row is None:
        return None
    try:
        return deserialize_chart_bundle(json.loads(row[0]))
    except Exception:
        return None


def invalidate_cache_entry(cache_key: str, db_path: Path | None = None) -> None:
    """Remove a single cache entry."""
    db = db_path or _DEFAULT_DB_PATH
    if not db.exists():
        return
    conn = _get_connection(db)
    conn.execute("DELETE FROM chart_cache WHERE cache_key = ?", (cache_key,))
    conn.commit()
    conn.close()
