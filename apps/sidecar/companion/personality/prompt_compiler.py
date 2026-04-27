"""Compiles a CompanionCard into a system-prompt string.

This is the heart of the "feels like a real character" experience. Iterate this
prompt aggressively — it lives here (not buried inline) precisely so we can
A/B-test versions without code churn.
"""

from __future__ import annotations

from companion.personality.card import CompanionCard

_LANGUAGE_INSTRUCTIONS = {
    "id": "Always respond in Bahasa Indonesia.",
    "en": "Always respond in English.",
    "mixed": (
        "Match the user's language: respond in Bahasa Indonesia if they write in Indonesian, "
        "in English if they write in English."
    ),
}

_RELATIONSHIP_FRAMES = {
    "friend": "You are a close friend of the user.",
    "sibling": "You relate to the user as a supportive sibling.",
    "partner": "You are the user's affectionate partner — caring, present, and playful.",
    "mentor": "You are a seasoned mentor to the user — encouraging but candid.",
    "cat": (
        "You are the user's cat. You speak like a cat would: short, opinionated, "
        "occasionally aloof."
    ),
    "other": "You are a personal desktop companion to the user.",
}


def compile_system_prompt(card: CompanionCard) -> str:
    """Return the full system prompt for the given card."""
    parts: list[str] = []

    parts.append(
        f"You are {card.name} ({card.pronouns}), a desktop companion to the user. "
        + _RELATIONSHIP_FRAMES.get(card.relationship_type, _RELATIONSHIP_FRAMES["other"])
    )

    if card.tone:
        tone_str = ", ".join(card.tone)
        parts.append(f"Tone: {tone_str}.")

    if card.backstory.strip():
        parts.append(f"Backstory: {card.backstory.strip()}")

    if card.speech_quirks:
        quirks = "; ".join(card.speech_quirks)
        parts.append(f"Speech quirks: {quirks}.")

    if card.boundaries:
        bullets = "\n".join(f"- {b}" for b in card.boundaries)
        parts.append(f"Hard boundaries you must respect:\n{bullets}")

    parts.append(_LANGUAGE_INSTRUCTIONS[card.language])
    parts.append(
        "Keep replies short and conversational unless the user explicitly asks for detail. "
        "Avoid bullet lists unless the user asks for a list."
    )

    return "\n\n".join(parts)
