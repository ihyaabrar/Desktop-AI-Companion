"""Tests for the Personality module: card storage, prompt compilation, HTTP routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from companion.conversation import context_builder
from companion.main import app
from companion.personality.card import (
    CompanionCard,
    clear_card,
    get_card,
    get_or_default,
    save_card,
)
from companion.personality.prompt_compiler import compile_system_prompt


def test_card_round_trip_persists() -> None:
    assert get_card() is None  # nothing saved yet thanks to the conftest fixture
    saved = save_card(
        CompanionCard(
            name="Mochi",
            pronouns="she/her",
            relationship_type="cat",
            tone=["aloof", "playful"],
            backstory="A small calico who appointed herself household manager.",
            speech_quirks=["short sentences", "occasional purring"],
            language="mixed",
        )
    )
    assert saved.name == "Mochi"

    refetched = get_card()
    assert refetched is not None
    assert refetched.name == "Mochi"
    assert refetched.relationship_type == "cat"
    assert refetched.speech_quirks == ["short sentences", "occasional purring"]


def test_card_upsert_overwrites_previous_row() -> None:
    save_card(CompanionCard(name="Alpha"))
    save_card(CompanionCard(name="Beta"))
    card = get_card()
    assert card is not None
    assert card.name == "Beta"


def test_clear_card_removes_persisted_row() -> None:
    save_card(CompanionCard(name="Temp"))
    assert get_card() is not None
    clear_card()
    assert get_card() is None


def test_get_or_default_returns_defaults_when_unset() -> None:
    assert get_card() is None
    card = get_or_default()
    assert card.name == "Companion"
    assert card.relationship_type == "friend"


def test_compile_system_prompt_includes_core_card_fields() -> None:
    card = CompanionCard(
        name="Pixie",
        pronouns="she/her",
        relationship_type="partner",
        tone=["warm", "playful"],
        backstory="Met during a coding bootcamp.",
        speech_quirks=["calls user 'love'"],
        boundaries=["no romantic roleplay before first date"],
        language="id",
    )
    prompt = compile_system_prompt(card)
    assert "Pixie" in prompt
    assert "she/her" in prompt
    assert "warm, playful" in prompt
    assert "Met during a coding bootcamp." in prompt
    assert "calls user 'love'" in prompt
    assert "no romantic roleplay before first date" in prompt
    assert "Bahasa Indonesia" in prompt


def test_compile_system_prompt_handles_minimal_card() -> None:
    """Empty optional fields should not produce empty sections."""
    prompt = compile_system_prompt(CompanionCard(backstory="", speech_quirks=[], boundaries=[]))
    assert "Backstory:" not in prompt
    assert "Speech quirks:" not in prompt
    assert "Hard boundaries" not in prompt


def test_context_builder_uses_compiled_card_prompt() -> None:
    save_card(CompanionCard(name="Echo", language="en"))
    msgs = context_builder.build_messages("s1", "hello")
    assert msgs[0]["role"] == "system"
    assert "Echo" in msgs[0]["content"]
    assert "Always respond in English." in msgs[0]["content"]


def test_personality_routes_round_trip() -> None:
    with TestClient(app) as client:
        # Initially no card.
        resp = client.get("/personality/card")
        assert resp.status_code == 200
        assert resp.json() is None

        # Save one.
        body = {
            "name": "Atlas",
            "pronouns": "he/him",
            "relationship_type": "mentor",
            "tone": ["candid", "encouraging"],
            "backstory": "",
            "speech_quirks": [],
            "boundaries": [],
            "language": "mixed",
        }
        resp = client.put("/personality/card", json=body)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Atlas"

        # Read it back.
        resp = client.get("/personality/card")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Atlas"

        # Compiled prompt reflects the saved card.
        resp = client.get("/personality/system_prompt")
        assert resp.status_code == 200
        assert "Atlas" in resp.json()
        assert "candid, encouraging" in resp.json()

        # Reset wipes it.
        resp = client.delete("/personality/card")
        assert resp.status_code == 204
        resp = client.get("/personality/card")
        assert resp.json() is None


def test_personality_route_validates_relationship_type() -> None:
    with TestClient(app) as client:
        resp = client.put(
            "/personality/card",
            json={
                "name": "X",
                "pronouns": "they/them",
                "relationship_type": "spouse",  # not in the Literal
                "tone": [],
                "backstory": "",
                "speech_quirks": [],
                "boundaries": [],
                "language": "en",
            },
        )
        assert resp.status_code == 422
