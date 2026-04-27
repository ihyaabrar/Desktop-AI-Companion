"""Semantic memory: structured key/value facts about the user, in SQLite.

Single-user app, so a flat table is plenty. Values are JSON so we can store
strings, numbers, lists, or nested dicts without schema churn.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from companion.db import get_connection


class SemanticFact(BaseModel):
    key: str
    value: Any
    evidence: str | None = None
    updated_at: str


def _row_to_fact(row: Any) -> SemanticFact:
    return SemanticFact(
        key=row["key"],
        value=json.loads(row["value"]),
        evidence=row["evidence"],
        updated_at=row["updated_at"],
    )


def upsert(key: str, value: Any, evidence: str | None = None) -> SemanticFact:
    """Create or overwrite a fact. Last write wins (we don't keep history yet)."""
    if not key or not key.replace("_", "").isalnum():
        raise ValueError(f"semantic.upsert: key must be snake_case-alphanumeric, got {key!r}")
    conn = get_connection()
    payload = json.dumps(value, ensure_ascii=False)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO semantic_memory (key, value, evidence, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            evidence = excluded.evidence,
            updated_at = excluded.updated_at
        """,
        (key, payload, evidence, now),
    )
    conn.commit()
    return SemanticFact(key=key, value=value, evidence=evidence, updated_at=now)


def get(key: str) -> SemanticFact | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT key, value, evidence, updated_at FROM semantic_memory WHERE key = ?",
        (key,),
    ).fetchone()
    return _row_to_fact(row) if row else None


def all_facts() -> list[SemanticFact]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, value, evidence, updated_at FROM semantic_memory ORDER BY key"
    ).fetchall()
    return [_row_to_fact(r) for r in rows]


def delete(key: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM semantic_memory WHERE key = ?", (key,))
    conn.commit()


def clear() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM semantic_memory")
    conn.commit()


def count() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS n FROM semantic_memory").fetchone()
    return int(row["n"])
