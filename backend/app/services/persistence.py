"""SQLite-based persistence layer.

Replaces JSON file storage with a proper database for:
- Settings (AI providers, AWS credentials)
- Job history (discovery, generation, drift)
- Audit log (all operations)
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger("persistence")

DATA_DIR = Path(os.environ.get("TERRAMORPH_DATA_DIR", "/app/data"))
DB_PATH = DATA_DIR / "terramorph.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db() -> None:
    """Initialize database schema."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS job_history (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'gcp',
            status TEXT NOT NULL,
            resources_found INTEGER DEFAULT 0,
            config TEXT,
            result_summary TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            action TEXT NOT NULL,
            category TEXT NOT NULL,
            details TEXT,
            source TEXT DEFAULT 'web'
        );

        CREATE TABLE IF NOT EXISTS generation_history (
            id TEXT PRIMARY KEY,
            job_id TEXT,
            provider TEXT DEFAULT 'gcp',
            total_resources INTEGER DEFAULT 0,
            files_count INTEGER DEFAULT 0,
            style TEXT DEFAULT 'flat',
            ai_cleaned INTEGER DEFAULT 0,
            files TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_job_history_type ON job_history(type);
        CREATE INDEX IF NOT EXISTS idx_job_history_created ON job_history(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_log_category ON audit_log(category);
        CREATE INDEX IF NOT EXISTS idx_generation_history_created ON generation_history(created_at DESC);
    """)
    conn.commit()


# === Settings (replaces JSON load/save) ===

def load(filename: str, default: Any = None) -> Any:
    """Load a settings value by key (backward compatible with old persistence API)."""
    try:
        conn = _get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (filename,)).fetchone()
        if row:
            return json.loads(row["value"])
        return default
    except Exception as e:
        logger.warning(f"Failed to load setting '{filename}': {e}")
        return default


def save(filename: str, data: Any) -> None:
    """Save a settings value (backward compatible with old persistence API)."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (filename, json.dumps(data, default=str), datetime.now().isoformat()),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save setting '{filename}': {e}")


# === Job History ===

def record_job(
    job_id: str,
    job_type: str,
    provider: str = "gcp",
    status: str = "running",
    config: dict | None = None,
) -> None:
    """Record a new job in history."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO job_history (id, type, provider, status, config, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, job_type, provider, status, json.dumps(config or {}), datetime.now().isoformat()),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to record job: {e}")


def update_job(job_id: str, status: str, resources_found: int = 0, result_summary: str = "") -> None:
    """Update a job's status and results."""
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE job_history SET status = ?, resources_found = ?, result_summary = ?, completed_at = ? WHERE id = ?",
            (status, resources_found, result_summary, datetime.now().isoformat(), job_id),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update job: {e}")


def get_job_history(limit: int = 20, job_type: str | None = None) -> list[dict]:
    """Get recent job history."""
    try:
        conn = _get_conn()
        if job_type:
            rows = conn.execute(
                "SELECT * FROM job_history WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (job_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM job_history ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get job history: {e}")
        return []


# === Audit Log ===

def audit(action: str, category: str, details: dict | None = None, source: str = "web") -> None:
    """Record an audit log entry."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO audit_log (action, category, details, source, timestamp) VALUES (?, ?, ?, ?, ?)",
            (action, category, json.dumps(details or {}), source, datetime.now().isoformat()),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def get_audit_log(limit: int = 50, category: str | None = None) -> list[dict]:
    """Get recent audit log entries."""
    try:
        conn = _get_conn()
        if category:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE category = ? ORDER BY timestamp DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get audit log: {e}")
        return []


# === Generation History ===

def save_generation(
    generation_id: str,
    job_id: str,
    provider: str,
    total_resources: int,
    files: list[dict],
    style: str = "flat",
    ai_cleaned: bool = False,
) -> None:
    """Save a generation result for later retrieval."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO generation_history (id, job_id, provider, total_resources, files_count, style, ai_cleaned, files, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (generation_id, job_id, provider, total_resources, len(files), style, int(ai_cleaned), json.dumps(files), datetime.now().isoformat()),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save generation: {e}")


def get_generation_history(limit: int = 10) -> list[dict]:
    """Get recent generation history (without file content for listing)."""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, job_id, provider, total_resources, files_count, style, ai_cleaned, created_at FROM generation_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get generation history: {e}")
        return []


def get_generation_by_id(generation_id: str) -> dict | None:
    """Get a specific generation result including file contents."""
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM generation_history WHERE id = ?", (generation_id,)
        ).fetchone()
        if row:
            result = dict(row)
            result["files"] = json.loads(result["files"]) if result["files"] else []
            return result
        return None
    except Exception as e:
        logger.error(f"Failed to get generation: {e}")
        return None


# Initialize on import
init_db()
