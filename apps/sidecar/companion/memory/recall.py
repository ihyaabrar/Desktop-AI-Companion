"""Retrieve + format memory for the next chat turn.

This is the "what does the companion remember about you" layer. It runs once
per user turn, before the LLM call:
  * pulls every semantic fact (it's small, single-user)
  * pulls top-K episodic memories most similar to the current user message
and renders them into prompt-friendly markdown blocks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from companion.memory import episodic, semantic
from companion.settings import settings


@dataclass(frozen=True)
class RecalledMemory:
    semantic_block: str
    episodic_block: str

    def to_prompt_suffix(self) -> str:
        sections: list[str] = []
        if self.semantic_block:
            sections.append(self.semantic_block)
        if self.episodic_block:
            sections.append(self.episodic_block)
        return "\n\n".join(sections)


def _format_semantic(facts: list[semantic.SemanticFact]) -> str:
    if not facts:
        return ""
    lines = [f"- {f.key}: {json.dumps(f.value, ensure_ascii=False)}" for f in facts]
    return "Known facts about the user:\n" + "\n".join(lines)


def _format_episodic(memories: list[dict[str, object]]) -> str:
    if not memories:
        return ""
    lines = [f"- {m.get('text', '')}" for m in memories if m.get("text")]
    if not lines:
        return ""
    return "Relevant memories from past chats:\n" + "\n".join(lines)


def recall(user_message: str) -> RecalledMemory:
    """Build the recall blocks for the current user message."""
    facts = semantic.all_facts()
    try:
        episodes = episodic.query(user_message, top_k=settings.episodic_top_k)
    except Exception:
        episodes = []
    return RecalledMemory(
        semantic_block=_format_semantic(facts),
        episodic_block=_format_episodic(episodes),
    )
