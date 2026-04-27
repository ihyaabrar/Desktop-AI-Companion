"""Builds the message list sent to the LLM for a given chat turn.

In M0 this is intentionally minimal: a hard-coded system prompt + recent in-memory
history. In M1 it'll pull the personality card from SQLite, in M2 it'll inject
episodic memory recall + semantic profile, and in M5 it'll include the latest
screen-vision note.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

# Placeholder system prompt. Module 3 (Personality) replaces this with a compiled
# companion-card prompt.
DEFAULT_SYSTEM_PROMPT = (
    "You are a warm, attentive desktop companion. Keep replies short and conversational. "
    "Match the user's language (Indonesian or English). Avoid lists unless asked."
)

# Per-session sliding window of recent turns. Kept tiny in M0; persistent storage lands in M2.
_HISTORY_LIMIT = 20
_history: dict[str, deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=_HISTORY_LIMIT))


def append_turn(session_id: str, role: str, content: str) -> None:
    """Record a single message for the session."""
    _history[session_id].append({"role": role, "content": content})


def get_history(session_id: str) -> list[dict[str, str]]:
    """Return a copy of the recorded history for a session."""
    return list(_history[session_id])


def build_messages(session_id: str, user_message: str) -> list[dict[str, str]]:
    """Compose the message list for the next LLM call."""
    messages: list[dict[str, str]] = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    messages.extend(get_history(session_id))
    messages.append({"role": "user", "content": user_message})
    return messages


def reset(session_id: str | None = None) -> None:
    """Clear history for a session (or all sessions if None). Used by tests."""
    if session_id is None:
        _history.clear()
    else:
        _history.pop(session_id, None)


def all_sessions() -> Iterable[str]:
    """Diagnostic helper."""
    return list(_history.keys())
