"""Unit tests for NoteService — validation, CRUD, cache invalidation."""
from __future__ import annotations

import pytest

from services.note_service import NoteService
from services.notebook_service import NotebookService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(fresh_db) -> NoteService:
    return NoteService.instance()


@pytest.fixture()
def nb(fresh_db) -> int:
    """Return the id of a freshly created notebook."""
    nb = NotebookService.instance().add_notebook("Test NB", "#1E88E5", "\U0001f4d3")
    return nb.id


# ---------------------------------------------------------------------------
# create_note — happy path
# ---------------------------------------------------------------------------

class TestCreateNote:
    def test_create_returns_note(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "Hello")
        assert note is not None
        assert note.id is not None

    def test_create_sets_title(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "My Title")
        assert note.title == "My Title"

    def test_create_empty_title_defaults_to_untitled(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "")
        assert note.title == "Untitled"

    def test_create_note_type_unified(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified")
        assert note.note_type == "unified"

    def test_create_note_type_text(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "text")
        assert note.note_type == "text"

    def test_create_note_is_retrievable(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "Retrieve me")
        fetched = svc.get_note_by_id(note.id)
        assert fetched is not None
        assert fetched.title == "Retrieve me"


# ---------------------------------------------------------------------------
# create_note — validation / boundary
# ---------------------------------------------------------------------------

class TestCreateNoteValidation:
    def test_invalid_notebook_id_raises(self, svc: NoteService) -> None:
        with pytest.raises(ValueError, match="notebook_id"):
            svc.create_note(0, "unified")

    def test_negative_notebook_id_raises(self, svc: NoteService) -> None:
        with pytest.raises(ValueError):
            svc.create_note(-1, "unified")

    def test_invalid_note_type_raises(self, svc: NoteService, nb: int) -> None:
        with pytest.raises(ValueError, match="note_type"):
            svc.create_note(nb, "spreadsheet")

    def test_title_exactly_500_chars_ok(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "x" * 500)
        assert len(note.title) == 500

    def test_title_over_500_chars_raises(self, svc: NoteService, nb: int) -> None:
        with pytest.raises(ValueError, match="500"):
            svc.create_note(nb, "unified", "x" * 501)


# ---------------------------------------------------------------------------
# update_note_text — happy path + boundary
# ---------------------------------------------------------------------------

class TestUpdateNoteText:
    def test_update_returns_updated_note(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified")
        updated = svc.update_note_text(note.id, "New Title", "Some content")
        assert updated is not None
        assert updated.title == "New Title"
        assert updated.content_text == "Some content"

    def test_update_empty_title_defaults_to_untitled(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "Original")
        updated = svc.update_note_text(note.id, "", "content")
        assert updated.title == "Untitled"

    def test_update_title_exactly_500_chars_ok(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified")
        updated = svc.update_note_text(note.id, "a" * 500, "")
        assert updated is not None

    def test_update_title_over_500_raises(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified")
        with pytest.raises(ValueError, match="500"):
            svc.update_note_text(note.id, "a" * 501, "")

    def test_update_content_exactly_50000_chars_ok(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified")
        updated = svc.update_note_text(note.id, "T", "x" * 50_000)
        assert updated is not None

    def test_update_content_over_50000_raises(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified")
        with pytest.raises(ValueError, match="50,000"):
            svc.update_note_text(note.id, "T", "x" * 50_001)

    def test_update_nonexistent_note_returns_none(self, svc: NoteService, nb: int) -> None:
        result = svc.update_note_text(99999, "T", "c")
        assert result is None


# ---------------------------------------------------------------------------
# update_note_strokes
# ---------------------------------------------------------------------------

class TestUpdateNoteStrokes:
    def test_update_strokes_persists(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified")
        import json
        strokes = json.dumps([{"x1": 0, "y1": 0, "x2": 1, "y2": 1,
                                "color": "#000", "size": 3}])
        updated = svc.update_note_strokes(note.id, strokes)
        assert updated is not None
        assert updated.content_strokes == strokes

    def test_update_strokes_nonexistent_returns_none(self, svc: NoteService) -> None:
        result = svc.update_note_strokes(99999, "[]")
        assert result is None


# ---------------------------------------------------------------------------
# delete_note
# ---------------------------------------------------------------------------

class TestDeleteNote:
    def test_delete_removes_note(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "To delete")
        svc.delete_note(note.id)
        assert svc.get_note_by_id(note.id) is None

    def test_delete_nonexistent_does_not_raise(self, svc: NoteService) -> None:
        svc.delete_note(99999)  # must not raise

    def test_delete_note_absent_from_list(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "Gone")
        svc.delete_note(note.id)
        notes = svc.get_notes_for_notebook(nb)
        assert all(n.id != note.id for n in notes)


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

class TestNoteCacheInvalidation:
    def test_create_invalidates_cache(self, svc: NoteService, nb: int) -> None:
        # Prime cache
        svc.get_notes_for_notebook(nb)
        note = svc.create_note(nb, "unified", "Fresh")
        notes = svc.get_notes_for_notebook(nb)
        assert any(n.id == note.id for n in notes)

    def test_update_invalidates_cache(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "Original")
        svc.get_notes_for_notebook(nb)  # prime
        svc.update_note_text(note.id, "Updated", "")
        fetched = svc.get_note_by_id(note.id)
        assert fetched.title == "Updated"

    def test_delete_invalidates_cache(self, svc: NoteService, nb: int) -> None:
        note = svc.create_note(nb, "unified", "Bye")
        svc.get_notes_for_notebook(nb)  # prime
        svc.delete_note(note.id)
        notes = svc.get_notes_for_notebook(nb)
        assert all(n.id != note.id for n in notes)
