"""Unit tests for NotebookService — validation, CRUD, cache invalidation."""
from __future__ import annotations

import pytest

from services.notebook_service import NotebookService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(fresh_db) -> NotebookService:
    return NotebookService.instance()


# ---------------------------------------------------------------------------
# add_notebook — happy path
# ---------------------------------------------------------------------------

class TestAddNotebook:
    def test_add_returns_notebook(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Work", "#1E88E5", "\U0001f4d3")
        assert nb is not None
        assert nb.id is not None

    def test_add_sets_name(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Personal", "#43A047", "\U0001f4d5")
        assert nb.name == "Personal"

    def test_add_sets_color(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Test", "#E53935", "\U0001f4d4")
        assert nb.color == "#E53935"

    def test_add_sets_emoji(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Test", "#1E88E5", "\U0001f4d6")
        assert nb.emoji == "\U0001f4d6"

    def test_add_notebook_is_retrievable(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Retrieve me", "#1E88E5", "\U0001f4d3")
        fetched = svc.get_by_id(nb.id)
        assert fetched is not None
        assert fetched.name == "Retrieve me"

    def test_add_multiple_notebooks_all_returned(self, svc: NotebookService) -> None:
        svc.add_notebook("A", "#1E88E5", "\U0001f4d3")
        svc.add_notebook("B", "#43A047", "\U0001f4d5")
        svc.add_notebook("C", "#E53935", "\U0001f4d4")
        all_nbs = svc.get_all()
        assert len(all_nbs) == 3


# ---------------------------------------------------------------------------
# add_notebook — validation / boundary
# ---------------------------------------------------------------------------

class TestAddNotebookValidation:
    def test_empty_name_raises(self, svc: NotebookService) -> None:
        with pytest.raises(ValueError, match="empty"):
            svc.add_notebook("", "#1E88E5", "\U0001f4d3")

    def test_whitespace_only_name_raises(self, svc: NotebookService) -> None:
        with pytest.raises(ValueError, match="empty"):
            svc.add_notebook("   ", "#1E88E5", "\U0001f4d3")

    def test_name_exactly_200_chars_ok(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("x" * 200, "#1E88E5", "\U0001f4d3")
        assert len(nb.name) == 200

    def test_name_over_200_chars_raises(self, svc: NotebookService) -> None:
        with pytest.raises(ValueError, match="200"):
            svc.add_notebook("x" * 201, "#1E88E5", "\U0001f4d3")


# ---------------------------------------------------------------------------
# update_notebook — happy path + boundary
# ---------------------------------------------------------------------------

class TestUpdateNotebook:
    def test_update_returns_updated(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Old Name", "#1E88E5", "\U0001f4d3")
        updated = svc.update_notebook(nb.id, "New Name")
        assert updated is not None
        assert updated.name == "New Name"

    def test_update_color(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Test", "#1E88E5", "\U0001f4d3")
        updated = svc.update_notebook(nb.id, "Test", color="#FF5722")
        assert updated.color == "#FF5722"

    def test_update_emoji(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Test", "#1E88E5", "\U0001f4d3")
        updated = svc.update_notebook(nb.id, "Test", emoji="\U0001f4d5")
        assert updated.emoji == "\U0001f4d5"

    def test_update_empty_name_raises(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Test", "#1E88E5", "\U0001f4d3")
        with pytest.raises(ValueError, match="empty"):
            svc.update_notebook(nb.id, "")

    def test_update_name_over_200_raises(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Test", "#1E88E5", "\U0001f4d3")
        with pytest.raises(ValueError, match="200"):
            svc.update_notebook(nb.id, "x" * 201)

    def test_update_nonexistent_returns_none(self, svc: NotebookService) -> None:
        result = svc.update_notebook(99999, "Ghost")
        assert result is None


# ---------------------------------------------------------------------------
# delete_notebook
# ---------------------------------------------------------------------------

class TestDeleteNotebook:
    def test_delete_removes_notebook(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Bye", "#1E88E5", "\U0001f4d3")
        svc.delete_notebook(nb.id)
        assert svc.get_by_id(nb.id) is None

    def test_delete_nonexistent_does_not_raise(self, svc: NotebookService) -> None:
        svc.delete_notebook(99999)  # must not raise

    def test_delete_absent_from_get_all(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Gone", "#1E88E5", "\U0001f4d3")
        svc.delete_notebook(nb.id)
        assert all(n.id != nb.id for n in svc.get_all())


# ---------------------------------------------------------------------------
# get_note_count
# ---------------------------------------------------------------------------

class TestGetNoteCount:
    def test_count_zero_for_empty_notebook(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Empty", "#1E88E5", "\U0001f4d3")
        assert svc.get_note_count(nb.id) == 0

    def test_count_increases_after_create(self, svc: NotebookService) -> None:
        from services.note_service import NoteService
        nb = svc.add_notebook("Counting", "#1E88E5", "\U0001f4d3")
        note_svc = NoteService.instance()
        note_svc.create_note(nb.id, "unified", "One")
        note_svc.create_note(nb.id, "unified", "Two")
        # Invalidate count cache so fresh value is read
        from services.cache_service import CacheService
        CacheService.instance().invalidate(f"notebooks:count:{nb.id}")
        assert svc.get_note_count(nb.id) == 2


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

class TestNotebookCacheInvalidation:
    def test_add_invalidates_cache(self, svc: NotebookService) -> None:
        svc.get_all()  # prime cache
        nb = svc.add_notebook("Fresh", "#1E88E5", "\U0001f4d3")
        all_nbs = svc.get_all()
        assert any(n.id == nb.id for n in all_nbs)

    def test_update_invalidates_cache(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Before", "#1E88E5", "\U0001f4d3")
        svc.get_all()  # prime cache
        svc.update_notebook(nb.id, "After")
        fetched = svc.get_by_id(nb.id)
        assert fetched.name == "After"

    def test_delete_invalidates_cache(self, svc: NotebookService) -> None:
        nb = svc.add_notebook("Temporary", "#1E88E5", "\U0001f4d3")
        svc.get_all()  # prime cache
        svc.delete_notebook(nb.id)
        all_nbs = svc.get_all()
        assert all(n.id != nb.id for n in all_nbs)
