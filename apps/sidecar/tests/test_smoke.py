"""Smoke tests that don't need a live LLM."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from companion import conversation
from companion.conversation import context_builder, engine
from companion.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "model" in body


def test_context_builder_appends_and_returns_history() -> None:
    context_builder.append_turn("s1", "user", "hi")
    context_builder.append_turn("s1", "assistant", "hello")
    history = context_builder.get_history("s1")
    assert history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_context_builder_isolates_sessions() -> None:
    context_builder.append_turn("a", "user", "hi from a")
    context_builder.append_turn("b", "user", "hi from b")
    assert context_builder.get_history("a") == [{"role": "user", "content": "hi from a"}]
    assert context_builder.get_history("b") == [{"role": "user", "content": "hi from b"}]


async def test_build_messages_includes_system_and_user(monkeypatch: pytest.MonkeyPatch) -> None:
    msgs = await context_builder.build_messages("s1", "what's up?")
    assert msgs[0]["role"] == "system"
    assert msgs[-1] == {"role": "user", "content": "what's up?"}


@pytest.mark.asyncio
async def test_chat_endpoint_streams_with_fake_router(monkeypatch: pytest.MonkeyPatch) -> None:
    """`POST /chat` should emit token events then a done event, using a stubbed router."""

    async def fake_stream(self, messages, **_kwargs):  # type: ignore[no-untyped-def]
        for tok in ["he", "llo", " there"]:
            yield tok

    monkeypatch.setattr("companion.llm.router.LLMRouter.stream", fake_stream)
    # Force engine to rebuild the router so it picks up the patched stream method.
    monkeypatch.setattr(engine, "_router", None)

    with (
        TestClient(app) as client,
        client.stream(
            "POST",
            "/chat",
            json={"user_message": "hi", "session_id": "test"},
        ) as resp,
    ):
        assert resp.status_code == 200
        events: list[dict[str, str]] = []
        for line in resp.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = json.loads(line.removeprefix("data:").strip())
            events.append(payload)

    types = [e["type"] for e in events]
    assert "token" in types
    assert types[-1] == "done"
    full_text = "".join(e["text"] for e in events if e["type"] == "token")
    assert full_text == "hello there"

    # History should now have user + assistant message.
    history = context_builder.get_history("test")
    assert history[0] == {"role": "user", "content": "hi"}
    assert history[1] == {"role": "assistant", "content": "hello there"}


def test_conversation_module_exports() -> None:
    """Sanity check that `from companion import conversation` works."""
    assert hasattr(conversation, "context_builder")
