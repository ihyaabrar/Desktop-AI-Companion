"""Tests for the Memory module: episodic store, semantic store, extractor, recall."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from companion.conversation import context_builder
from companion.main import app
from companion.memory import episodic, extractor, recall, semantic
from companion.personality.card import CompanionCard, save_card
from companion.settings import settings

# ----------------------------- Episodic --------------------------------------


def test_episodic_add_and_query_returns_nearest() -> None:
    episodic.add("user adopted a calico cat named Mochi")
    episodic.add("user finished a marathon last weekend")
    episodic.add("user's favorite ramen shop closed down")

    results = episodic.query("tell me about the cat", top_k=2)
    assert len(results) == 2
    # The deterministic FakeHashEmbedder gives stable distances; we just want
    # the result list to be non-empty and well-shaped.
    for r in results:
        assert "text" in r
        assert "metadata" in r
        assert "distance" in r


def test_episodic_query_empty_collection_returns_empty_list() -> None:
    assert episodic.query("anything", top_k=3) == []


def test_episodic_clear_removes_everything() -> None:
    episodic.add("memory one")
    episodic.add("memory two")
    assert episodic.count() == 2
    episodic.clear()
    assert episodic.count() == 0


# ----------------------------- Semantic --------------------------------------


def test_semantic_upsert_round_trip() -> None:
    fact = semantic.upsert("user_name", "Ihya", evidence="user said: 'I'm Ihya'")
    assert fact.key == "user_name"
    assert fact.value == "Ihya"

    fetched = semantic.get("user_name")
    assert fetched is not None
    assert fetched.value == "Ihya"
    assert fetched.evidence == "user said: 'I'm Ihya'"


def test_semantic_upsert_overwrites_existing_key() -> None:
    semantic.upsert("user_pet", "cat")
    semantic.upsert("user_pet", "dog")
    fact = semantic.get("user_pet")
    assert fact is not None
    assert fact.value == "dog"


def test_semantic_upsert_rejects_invalid_key() -> None:
    with pytest.raises(ValueError):
        semantic.upsert("not a snake_case key!", "value")


def test_semantic_all_facts_returns_sorted_by_key() -> None:
    semantic.upsert("z_last", 1)
    semantic.upsert("a_first", 2)
    keys = [f.key for f in semantic.all_facts()]
    assert keys == ["a_first", "z_last"]


# ----------------------------- Extractor parsing -----------------------------


def test_extractor_parses_clean_json() -> None:
    raw = json.dumps(
        {
            "episodic": ["user adopted a calico cat named Mochi"],
            "semantic": [{"key": "user_pet", "value": "calico cat"}],
        }
    )
    parsed = extractor.parse_extraction(raw)
    assert parsed["episodic"] == ["user adopted a calico cat named Mochi"]
    assert parsed["semantic"][0]["key"] == "user_pet"


def test_extractor_parses_json_with_code_fence() -> None:
    raw = '```json\n{"episodic": [], "semantic": [{"key": "k", "value": 1}]}\n```'
    parsed = extractor.parse_extraction(raw)
    assert parsed["semantic"][0]["key"] == "k"


def test_extractor_parses_json_embedded_in_prose() -> None:
    raw = 'Here you go:\n{"episodic":["a thing"], "semantic":[]}\nHope that helps.'
    parsed = extractor.parse_extraction(raw)
    assert parsed["episodic"] == ["a thing"]


def test_extractor_returns_empty_on_garbage() -> None:
    parsed = extractor.parse_extraction("totally not json")
    assert parsed == {"episodic": [], "semantic": []}


def test_extractor_persist_writes_to_both_stores() -> None:
    counts = extractor.persist_extraction(
        {
            "episodic": ["user finished a marathon"],
            "semantic": [
                {"key": "user_runs", "value": True, "evidence": "user said 'I run'"},
                {"key": "invalid key with spaces", "value": "skipped"},
            ],
        }
    )
    assert counts == {"episodic": 1, "semantic": 1}
    assert episodic.count() == 1
    assert semantic.get("user_runs") is not None


def test_extractor_should_extract_gates_on_interval_and_min_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "extractor_interval", 2)
    monkeypatch.setattr(settings, "extractor_min_chars", 5)

    history_short_user = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hi back"},
        {"role": "user", "content": "yo"},
    ]
    assert extractor.should_extract(history_short_user) is False  # last user msg too short

    history_one_user_only = [{"role": "user", "content": "this is a long message"}]
    assert extractor.should_extract(history_one_user_only) is False  # not at interval boundary

    history_at_boundary = [
        {"role": "user", "content": "hello there friend"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "this is a long message"},
    ]
    assert extractor.should_extract(history_at_boundary) is True


# ----------------------------- Recall + context_builder ----------------------


def test_recall_renders_semantic_block() -> None:
    semantic.upsert("user_name", "Ihya")
    semantic.upsert("user_pet", "calico cat")
    block = recall.recall("hello")
    assert "Known facts about the user:" in block.semantic_block
    assert "user_name" in block.semantic_block
    assert "calico cat" in block.semantic_block


def test_recall_renders_episodic_block_when_memories_exist() -> None:
    episodic.add("user adopted a calico cat named Mochi")
    block = recall.recall("tell me about my cat")
    assert "Relevant memories from past chats:" in block.episodic_block
    assert "Mochi" in block.episodic_block


def test_recall_returns_empty_when_nothing_stored() -> None:
    block = recall.recall("anything")
    assert block.semantic_block == ""
    assert block.episodic_block == ""


def test_context_builder_injects_recall_into_system_prompt() -> None:
    save_card(CompanionCard(name="Echo"))
    semantic.upsert("user_name", "Ihya")
    episodic.add("user adopted a cat named Mochi last weekend")

    msgs = context_builder.build_messages("s1", "tell me about my pet")
    system = msgs[0]["content"]
    assert "Echo" in system
    assert "user_name" in system
    assert "Mochi" in system


# ----------------------------- HTTP routes -----------------------------------


def test_memory_summary_route() -> None:
    semantic.upsert("k", 1)
    episodic.add("memory")
    with TestClient(app) as client:
        resp = client.get("/memory/summary")
        assert resp.status_code == 200
        assert resp.json() == {"semantic_count": 1, "episodic_count": 1}


def test_memory_semantic_routes() -> None:
    with TestClient(app) as client:
        resp = client.get("/memory/semantic")
        assert resp.json() == []

        resp = client.put(
            "/memory/semantic",
            json={"key": "user_age", "value": 25, "evidence": "user said so"},
        )
        assert resp.status_code == 200
        assert resp.json()["value"] == 25

        resp = client.get("/memory/semantic")
        assert len(resp.json()) == 1

        resp = client.delete("/memory/semantic/user_age")
        assert resp.status_code == 204
        resp = client.get("/memory/semantic")
        assert resp.json() == []


def test_memory_episodic_routes() -> None:
    with TestClient(app) as client:
        resp = client.post("/memory/episodic", json={"text": "had a great walk"})
        assert resp.status_code == 200
        assert "id" in resp.json()

        resp = client.post("/memory/episodic/query", json={"text": "walk", "top_k": 1})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = client.delete("/memory/episodic")
        assert resp.status_code == 204

        resp = client.get("/memory/summary")
        assert resp.json()["episodic_count"] == 0
