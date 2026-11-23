"""SQLite connection and schema migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_V1 = """
CREATE TABLE analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    video_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL DEFAULT '',
    duration_sec INTEGER NOT NULL DEFAULT 0,
    thumbnail BLOB
);
CREATE TABLE shorts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    hook TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    hashtags TEXT NOT NULL DEFAULT '[]',
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    reason TEXT NOT NULL DEFAULT '',
    is_favorite INTEGER NOT NULL DEFAULT 0,
    is_edited INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_shorts_analysis ON shorts(analysis_id);
CREATE INDEX idx_analyses_created ON analyses(created_at DESC);
"""

MIGRATIONS = [SCHEMA_V1]


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the database, enable foreign keys and apply pending migrations."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for index in range(version, len(MIGRATIONS)):
        conn.executescript(MIGRATIONS[index])
        conn.execute(f"PRAGMA user_version = {index + 1}")
    conn.commit()
