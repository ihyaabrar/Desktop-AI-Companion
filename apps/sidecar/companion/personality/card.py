"""Companion card schema + SQLite-backed storage (single-user app, single row)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from companion.db import get_connection

Language = Literal["id", "en", "mixed"]
RelationshipType = Literal["friend", "sibling", "partner", "mentor", "cat", "other"]


class CompanionCard(BaseModel):
    """The user-authored "character creator" definition of the companion."""

    name: str = Field(default="Companion", min_length=1, max_length=60)
    pronouns: str = Field(default="they/them", max_length=40)
    relationship_type: RelationshipType = "friend"
    tone: list[str] = Field(default_factory=lambda: ["warm", "playful", "concise"])
    backstory: str = Field(default="", max_length=1000)
    speech_quirks: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    language: Language = "mixed"


def get_card() -> CompanionCard | None:
    """Return the saved card, or None if the user hasn't completed onboarding."""
    conn = get_connection()
    row = conn.execute("SELECT data FROM personality_card WHERE id = 1").fetchone()
    if row is None:
        return None
    return CompanionCard.model_validate_json(row["data"])


def save_card(card: CompanionCard) -> CompanionCard:
    """Upsert the single-row card. Returns the saved value."""
    conn = get_connection()
    payload = card.model_dump_json()
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO personality_card (id, data, updated_at)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
        """,
        (payload, now),
    )
    conn.commit()
    return card


def clear_card() -> None:
    """Delete the saved card. Used by tests and the 'reset onboarding' debug action."""
    conn = get_connection()
    conn.execute("DELETE FROM personality_card WHERE id = 1")
    conn.commit()


def get_or_default() -> CompanionCard:
    """Return the saved card, or the default (used by the prompt compiler before onboarding)."""
    return get_card() or CompanionCard()


# Helper for tests to assert what's persisted.
def _raw_row() -> dict[str, str] | None:
    conn = get_connection()
    row = conn.execute("SELECT data, updated_at FROM personality_card WHERE id = 1").fetchone()
    return dict(row) if row else None


__all__ = [
    "CompanionCard",
    "Language",
    "RelationshipType",
    "clear_card",
    "get_card",
    "get_or_default",
    "save_card",
]
