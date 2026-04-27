"""Pytest fixtures shared across the sidecar test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from companion import db
from companion.conversation import context_builder
from companion.personality import card as card_module
from companion.settings import settings


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every test at a fresh empty data directory + reset in-memory state."""
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    db.reset_for_tests()
    context_builder.reset()
    # Ensure the card cache (if any) sees the new DB.
    card_module.clear_card()
    return tmp_path
