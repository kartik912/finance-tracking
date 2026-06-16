"""Pytest fixtures shared across the test suite."""
from __future__ import annotations

import json
import os

import pytest


@pytest.fixture()
def config_path(tmp_path: pytest.TempPathFactory) -> str:
    """Return the path to a temporary config.json file inside a temp dir.

    The file does NOT exist yet — tests that need a pre-existing file must
    create it themselves. Tests that call ``save()`` will write here.
    Automatically cleaned up by pytest after each test.
    """
    return str(tmp_path / "config.json")


@pytest.fixture()
def existing_config(tmp_path: pytest.TempPathFactory) -> tuple[str, dict]:
    """Write a valid config.json to a temp dir and return (path, data)."""
    data = {
        "gemini_api_key": "test-api-key-abc",
        "db_path": "database/finance.db",
        "theme_mode": "dark",
        "currency_symbol": "$",
    }
    path = str(tmp_path / "config.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path, data
