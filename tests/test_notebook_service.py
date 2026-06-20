"""Tests for NotebookService — Phase 5."""
from __future__ import annotations

import pytest

from services.notebook_service import NotebookService


@pytest.fixture()
def svc(fresh_db) -> NotebookService:
    return NotebookService.instance()


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------

class TestGetAll:
    def test_empty_returns_list(self, svc: NotebookService):
        assert svc.get_all() == []

    def test_returns_created_notebook(self, svc: NotebookService):
        svc.add_notebook("Work", "#1E88E5", "\U0001f4d3")
        assert len(svc.get_all()) == 1

    def test_ordered_newest_first(self, svc: NotebookService):
        svc.add_notebook("First", "#1E88E5", "\U0001f4d3")
        svc.add_notebook("Second", "#43A047", "\U0001f4d5")
        names = [nb.name for nb in svc.get_all()]
        assert names[0] == "Second"


# ---------------------------------------------------------------------------
# add_notebook
# ---------------------------------------------------------------------------

class TestAddNotebook:
    def test_persists_fields(self, svc: NotebookService):
        nb = svc.add_notebook("My Notebook", "#F44336", "\u2728")
        assert nb.id is not None
        assert nb.name == "My Notebook"
        assert nb.color == "#F44336"
        assert nb.emoji == "\u2728"

    def test_empty_name_raises(self, svc: NotebookService):
        with pytest.raises(ValueError, match="empty"):
            svc.add_notebook("   ", "#1E88E5", "\U0001f4d3")

    def test_name_too_long_raises(self, svc: NotebookService):
        with pytest.raises(ValueError, match="200"):
            svc.add_notebook("x" * 201, "#1E88E5", "\U0001f4d3")

    def test_defaults_applied_when_empty_color(self, svc: NotebookService):
        nb = svc.add_notebook("Test", "", "")
        assert nb.color == "#1E88E5"

    def test_cache_invalidated_after_add(self, svc: NotebookService):
        svc.get_all()  # prime cache
        svc.add_notebook("New", "#1E88E5", "\U0001f4d3")
        assert len(svc.get_all()) == 1


# ---------------------------------------------------------------------------
# update_notebook
# ---------------------------------------------------------------------------

class TestUpdateNotebook:
    def test_rename(self, svc: NotebookService):
        nb = svc.add_notebook("Old", "#1E88E5", "\U0001f4d3")
        updated = svc.update_notebook(nb.id, "New Name")
        assert updated.name == "New Name"

    def test_nonexistent_returns_none(self, svc: NotebookService):
        result = svc.update_notebook(999, "Name")
        assert result is None

    def test_empty_name_raises(self, svc: NotebookService):
        nb = svc.add_notebook("A", "#1E88E5", "\U0001f4d3")
        with pytest.raises(ValueError):
            svc.update_notebook(nb.id, "")


# ---------------------------------------------------------------------------
# delete_notebook
# ---------------------------------------------------------------------------

class TestDeleteNotebook:
    def test_delete_removes_notebook(self, svc: NotebookService):
        nb = svc.add_notebook("Temp", "#1E88E5", "\U0001f4d3")
        svc.delete_notebook(nb.id)
        assert svc.get_all() == []

    def test_delete_invalidates_cache(self, svc: NotebookService):
        nb = svc.add_notebook("Temp", "#1E88E5", "\U0001f4d3")
        svc.get_all()  # prime cache
        svc.delete_notebook(nb.id)
        assert svc.get_all() == []


# ---------------------------------------------------------------------------
# get_note_count
# ---------------------------------------------------------------------------

class TestGetNoteCount:
    def test_count_zero_for_empty_notebook(self, svc: NotebookService):
        nb = svc.add_notebook("Empty", "#1E88E5", "\U0001f4d3")
        assert svc.get_note_count(nb.id) == 0
