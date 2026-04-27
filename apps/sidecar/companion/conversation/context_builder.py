"""Builds the message list sent to the LLM for a given chat turn.

The system prompt is compiled from the Personality module's CompanionCard. In M2
this builder will also inject episodic memory recall + semantic profile, and in
M5 it'll include the latest screen-vision note.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import Iterable

from companion.memory.recall import recall
from companion.personality.card import get_or_default
from companion.personality.prompt_compiler import compile_system_prompt

# Per-session sliding window of recent turns. Kept tiny in M0; persistent storage lands in M2.
_HISTORY_LIMIT = 20
_history: dict[str, deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=_HISTORY_LIMIT))


def append_turn(session_id: str, role: str, content: str) -> None:
    """Record a single message for the session."""
    _history[session_id].append({"role": role, "content": content})


def get_history(session_id: str) -> list[dict[str, str]]:
    """Return a copy of the recorded history for a session."""
    return list(_history[session_id])


async def build_messages(session_id: str, user_message: str) -> list[dict[str, str]]:
    """Compose the message list for the next LLM call."""
    system_prompt = compile_system_prompt(get_or_default())
    recalled = await asyncio.to_thread(recall, user_message)
    suffix = recalled.to_prompt_suffix()
    if suffix:
        system_prompt = f"{system_prompt}\n\n{suffix}"
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
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
