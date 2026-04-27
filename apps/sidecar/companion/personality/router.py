"""HTTP routes for the personality module."""

from __future__ import annotations

from fastapi import APIRouter

from companion.personality.card import (
    CompanionCard,
    clear_card,
    get_card,
    get_or_default,
    save_card,
)
from companion.personality.prompt_compiler import compile_system_prompt

router = APIRouter(prefix="/personality", tags=["personality"])


@router.get("/card", response_model=CompanionCard | None)
def read_card() -> CompanionCard | None:
    """Return the saved companion card, or null if onboarding is incomplete."""
    return get_card()


@router.put("/card", response_model=CompanionCard)
def upsert_card(card: CompanionCard) -> CompanionCard:
    """Replace the saved card with `card`. Used by the companion-card form."""
    return save_card(card)


@router.delete("/card", status_code=204)
def reset_card() -> None:
    """Wipe the saved card so first-run flow is shown again. Useful for debugging."""
    clear_card()


@router.get("/system_prompt", response_model=str)
def read_system_prompt() -> str:
    """Return the compiled system prompt that will be sent to the LLM."""
    return compile_system_prompt(get_or_default())
