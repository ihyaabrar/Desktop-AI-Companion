"""Background memory extractor.

After every N user turns, calls a small LLM pass that reads the recent
conversation + currently-known facts and returns a JSON object with new
episodic memories and semantic facts to persist. The extraction runs as an
asyncio task so it doesn't block the next user turn.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from companion.llm.router import LLMRouter
from companion.memory import episodic, semantic
from companion.settings import settings

log = logging.getLogger("companion.memory.extractor")

_EXTRACTION_SYSTEM_PROMPT = """You read a conversation between a user and their AI companion
and extract new things worth remembering.

Output a single JSON object with two fields:
  "episodic": an array of 0-3 short narrative strings — vivid moments, stories,
    or events from the conversation.
  "semantic": an array of 0-5 facts, each shaped like
    {"key": "<snake_case>", "value": <any>, "evidence": "<short quote>"}.

Rules:
- Episodic = events / experiences / things-that-happened.
  Semantic = stable facts, preferences, profile details.
- Skip anything already present in known_facts.
- Use snake_case English keys (e.g. user_name, user_likes_indonesian_food).
- Output ONLY the JSON object. No prose, no markdown fences."""


def _extractor_router() -> LLMRouter:
    return LLMRouter()


def _format_history(history: list[dict[str, str]]) -> str:
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)


def _format_known_facts(facts: list[semantic.SemanticFact]) -> str:
    if not facts:
        return "(none)"
    return "\n".join(f"- {f.key}: {json.dumps(f.value, ensure_ascii=False)}" for f in facts)


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_extraction(raw: str) -> dict[str, Any]:
    """Best-effort JSON parse of the extractor's reply."""
    raw = raw.strip()
    if not raw:
        return {"episodic": [], "semantic": []}

    # Strip possible ```json fences.
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"```\s*$", "", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(raw)
        if not match:
            log.warning("extractor: could not find a JSON object in reply")
            return {"episodic": [], "semantic": []}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            log.warning("extractor: JSON decode failed: %s", exc)
            return {"episodic": [], "semantic": []}

    return {
        "episodic": list(parsed.get("episodic") or []),
        "semantic": list(parsed.get("semantic") or []),
    }


def should_extract(history: list[dict[str, str]]) -> bool:
    """Heuristic gate so we don't waste an LLM call on trivial conversation."""
    user_turns = [t for t in history if t["role"] == "user"]
    if len(user_turns) < settings.extractor_interval:
        return False
    # Trigger once we hit the boundary (and again every interval-th turn).
    if len(user_turns) % settings.extractor_interval != 0:
        return False
    last_user = user_turns[-1]["content"]
    return len(last_user) >= settings.extractor_min_chars


def _persist_episodic(text: str) -> bool:
    """Wrap `episodic.add` so embedding/HTTP failures don't take down the whole pass."""
    try:
        episodic.add(text, kind="extracted")
        return True
    except Exception as exc:
        log.warning("extractor: failed to persist episodic item: %s", exc)
        return False


def persist_extraction(extraction: dict[str, Any]) -> dict[str, int]:
    """Store extracted memories. Returns counts of how many landed in each tier.

    Each item is persisted independently — a single embedding failure or an
    invalid semantic key never aborts the whole batch. The LLM extraction cost
    is already paid; we save what we can.
    """
    episodic_count = 0
    semantic_count = 0

    for item in extraction.get("episodic", []):
        text: str | None = None
        if isinstance(item, str) and item.strip():
            text = item.strip()
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            text = item["text"].strip()
        if text and _persist_episodic(text):
            episodic_count += 1

    for fact in extraction.get("semantic", []):
        if not isinstance(fact, dict):
            continue
        key = fact.get("key")
        if not isinstance(key, str) or not key.strip():
            continue
        try:
            semantic.upsert(
                key=key.strip(),
                value=fact.get("value"),
                evidence=fact.get("evidence"),
            )
            semantic_count += 1
        except ValueError as exc:
            log.warning("extractor: skipping invalid semantic key %r: %s", key, exc)
        except Exception as exc:
            log.warning("extractor: failed to persist semantic key %r: %s", key, exc)

    return {"episodic": episodic_count, "semantic": semantic_count}


async def extract_now(history: list[dict[str, str]]) -> dict[str, int]:
    """Synchronously run one extraction pass over `history`. Returns persistence counts."""
    if not history:
        return {"episodic": 0, "semantic": 0}

    known_facts = semantic.all_facts()
    user_prompt = (
        f"known_facts:\n{_format_known_facts(known_facts)}\n\n"
        f"conversation:\n{_format_history(history)}\n\n"
        "Return the JSON object now."
    )

    try:
        raw = await _extractor_router().complete(
            [
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=512,
        )
    except Exception as exc:
        log.warning("extractor: LLM call failed: %s", exc)
        return {"episodic": 0, "semantic": 0}

    extraction = parse_extraction(raw)
    return persist_extraction(extraction)


def schedule_extraction(history: list[dict[str, str]]) -> asyncio.Task[dict[str, int]] | None:
    """Fire-and-forget the extractor on the current event loop."""
    if not should_extract(history):
        return None
    return asyncio.create_task(extract_now(list(history)))
