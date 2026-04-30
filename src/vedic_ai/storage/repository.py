"""SQLite repository for persisting and loading PredictionReport objects."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from vedic_ai.domain.prediction import PredictionReport

_DEFAULT_DB_PATH = Path("data/processed/reports.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS prediction_reports (
    report_id TEXT PRIMARY KEY,
    birth_name TEXT,
    scope TEXT,
    model_name TEXT,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def _get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def _report_id(report: PredictionReport) -> str:
    """Derive a stable ID from chart_bundle_id + generated_at timestamp."""
    ts = report.generated_at.strftime("%Y%m%dT%H%M%S")
    base = (report.chart_bundle_id or "unknown")[:16]
    return f"{base}_{ts}"


def save_report(report: PredictionReport, db_path: Path | None = None) -> str:
    """Persist a PredictionReport and return its report_id.

    Replaces any existing entry with the same ID.
    """
    db = db_path or _DEFAULT_DB_PATH
    conn = _get_connection(db)
    rid = _report_id(report)
    scopes = ",".join(s.scope for s in report.sections)
    conn.execute(
        """INSERT OR REPLACE INTO prediction_reports
           (report_id, birth_name, scope, model_name, report_json)
           VALUES (?, ?, ?, ?, ?)""",
        (rid, report.birth_name, scopes, report.model_name,
         report.model_dump_json()),
    )
    conn.commit()
    conn.close()
    return rid


def load_report(report_id: str, db_path: Path | None = None) -> PredictionReport | None:
    """Load a PredictionReport by ID, or None if not found."""
    db = db_path or _DEFAULT_DB_PATH
    if not db.exists():
        return None
    conn = _get_connection(db)
    row = conn.execute(
        "SELECT report_json FROM prediction_reports WHERE report_id = ?", (report_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    try:
        return PredictionReport.model_validate(json.loads(row[0]))
    except Exception:
        return None


def list_reports(db_path: Path | None = None) -> list[dict]:
    """Return a list of report metadata dicts (id, birth_name, scope, created_at)."""
    db = db_path or _DEFAULT_DB_PATH
    if not db.exists():
        return []
    conn = _get_connection(db)
    rows = conn.execute(
        "SELECT report_id, birth_name, scope, model_name, created_at "
        "FROM prediction_reports ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"report_id": r[0], "birth_name": r[1], "scope": r[2],
         "model_name": r[3], "created_at": r[4]}
        for r in rows
    ]
