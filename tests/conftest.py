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


@pytest.fixture()
def fresh_db():
    """Provide a clean in-memory SQLite DB for each test.

    Resets the SQLAlchemy engine + scoped session singletons and also resets
    any service-layer singletons that hold a reference to the old engine so
    tests never share state.
    """
    from config.database import create_tables, init_db, reset_db

    # Reset engine so init_db creates a fresh in-memory instance
    reset_db()
    init_db(":memory:")
    create_tables()

    # Reset service singletons so they bind to the new DB
    from services.cache_service import CacheService
    from services.finance_service import FinanceService
    from services.investment_service import InvestmentService
    from services.goal_service import GoalService

    CacheService._instance = None  # type: ignore[attr-defined]
    FinanceService._instance = None  # type: ignore[attr-defined]
    InvestmentService._instance = None  # type: ignore[attr-defined]
    GoalService._instance = None  # type: ignore[attr-defined]

    # Reset Phase 5 service singletons
    from services.notebook_service import NotebookService
    from services.note_service import NoteService
    NotebookService._instance = None  # type: ignore[attr-defined]
    NoteService._instance = None  # type: ignore[attr-defined]

    # Reset EventBus so subscriptions from previous tests don't accumulate
    from observers.event_bus import EventBus
    EventBus._instance = None  # type: ignore[attr-defined]

    yield

    # Teardown
    FinanceService._instance = None  # type: ignore[attr-defined]
    CacheService._instance = None  # type: ignore[attr-defined]
    EventBus._instance = None  # type: ignore[attr-defined]
    from services.notebook_service import NotebookService
    from services.note_service import NoteService
    NotebookService._instance = None  # type: ignore[attr-defined]
    NoteService._instance = None  # type: ignore[attr-defined]
    reset_db()
