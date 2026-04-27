"""SQLite connection helper.

Single-user app: the whole companion lives in one SQLite file. Tables are created
lazily on first connection so we don't ship a separate migration tool yet.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock

from companion.settings import settings

_lock = Lock()
_initialized = False


def _db_path() -> Path:
    path = Path(settings.data_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path / "companion.sqlite"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables on first use. Idempotent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS personality_card (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            data TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def get_connection() -> sqlite3.Connection:
    """Return a thread-safe SQLite connection with the schema initialised."""
    global _initialized
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    if not _initialized:
        with _lock:
            if not _initialized:
                _ensure_schema(conn)
                _initialized = True
    return conn


def reset_for_tests() -> None:
    """Test helper — drops the schema flag so the next call recreates tables."""
    global _initialized
    with _lock:
        _initialized = False
