"""Thin wrapper around LiteLLM so the rest of the codebase doesn't import it directly.

This keeps the contract narrow: callers pass messages + a model name, get an async
iterator of token strings. Swapping the underlying router later (e.g. directly hitting
Ollama / OpenAI) only touches this file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any

import litellm

from companion.settings import settings


class LLMRouter:
    """Async streaming LLM client backed by LiteLLM."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.llm_model
        # LiteLLM reads provider keys from env vars; we only need to point Ollama
        # at a custom base URL when configured.
        if self.model.startswith("ollama/"):
            litellm.api_base = settings.ollama_api_base

    async def stream(
        self,
        messages: Iterable[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield assistant tokens as they arrive.

        Args:
            messages: OpenAI-style chat messages.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "stream": True,
            "temperature": temperature if temperature is not None else settings.temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.max_tokens,
        }
        if self.model.startswith("ollama/"):
            kwargs["api_base"] = settings.ollama_api_base

        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            # LiteLLM yields OpenAI-shaped chunks; pull the delta safely.
            choices = getattr(chunk, "choices", None) or chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta") if isinstance(choices[0], dict) else choices[0].delta
            if not delta:
                continue
            content = (
                delta.get("content") if isinstance(delta, dict) else getattr(delta, "content", None)
            )
            if content:
                yield content
