"""Conversation engine: orchestrates a single chat turn end-to-end."""

from __future__ import annotations

from collections.abc import AsyncIterator

from companion.conversation import context_builder
from companion.llm.router import LLMRouter

_router: LLMRouter | None = None


def _get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


async def stream_reply(session_id: str, user_message: str) -> AsyncIterator[str]:
    """Stream assistant tokens for `user_message`, recording history as we go."""
    context_builder.append_turn(session_id, "user", user_message)
    messages = context_builder.build_messages(session_id, user_message)
    # `messages` already includes the user turn we just appended via context_builder,
    # so trim the trailing duplicate before calling the LLM.
    messages = messages[:-1] if messages and messages[-1]["role"] == "user" else messages
    messages.append({"role": "user", "content": user_message})

    collected: list[str] = []
    async for token in _get_router().stream(messages):
        collected.append(token)
        yield token

    context_builder.append_turn(session_id, "assistant", "".join(collected))
