"""Tests for NoteService — Phase 5."""
from __future__ import annotations

import os
import tempfile

import pytest

from services.note_service import NoteService
from services.notebook_service import NotebookService


@pytest.fixture()
def nb_svc(fresh_db) -> NotebookService:
    return NotebookService.instance()


@pytest.fixture()
def svc(fresh_db) -> NoteService:
    return NoteService.instance()


@pytest.fixture()
def notebook_id(nb_svc: NotebookService) -> int:
    nb = nb_svc.add_notebook("Test Notebook", "#1E88E5", "\U0001f4d3")
    return nb.id


# ---------------------------------------------------------------------------
# create_note
# ---------------------------------------------------------------------------

class TestCreateNote:
    def test_creates_text_note(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "text", "My Note")
        assert note.id is not None
        assert note.note_type == "text"
        assert note.title == "My Note"
        assert note.notebook_id == notebook_id

    def test_creates_image_note(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "image")
        assert note.note_type == "image"
        assert note.title == "Untitled"

    def test_creates_doodle_note(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "doodle")
        assert note.note_type == "doodle"

    def test_invalid_type_raises(self, svc: NoteService, notebook_id: int):
        with pytest.raises(ValueError, match="note_type"):
            svc.create_note(notebook_id, "unknown")

    def test_invalid_notebook_id_raises(self, svc: NoteService):
        with pytest.raises(ValueError, match="Invalid"):
            svc.create_note(0, "text")

    def test_title_too_long_raises(self, svc: NoteService, notebook_id: int):
        with pytest.raises(ValueError, match="500"):
            svc.create_note(notebook_id, "text", "x" * 501)


# ---------------------------------------------------------------------------
# get_notes_for_notebook
# ---------------------------------------------------------------------------

class TestGetNotes:
    def test_empty_list(self, svc: NoteService, notebook_id: int):
        assert svc.get_notes_for_notebook(notebook_id) == []

    def test_returns_notes_for_notebook(self, svc: NoteService, notebook_id: int):
        svc.create_note(notebook_id, "text", "Note A")
        svc.create_note(notebook_id, "text", "Note B")
        notes = svc.get_notes_for_notebook(notebook_id)
        assert len(notes) == 2

    def test_cache_invalidated_after_add(self, svc: NoteService, notebook_id: int):
        svc.get_notes_for_notebook(notebook_id)  # prime cache
        svc.create_note(notebook_id, "text", "New")
        assert len(svc.get_notes_for_notebook(notebook_id)) == 1


# ---------------------------------------------------------------------------
# update_note_text
# ---------------------------------------------------------------------------

class TestUpdateNoteText:
    def test_updates_content(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "text", "Old")
        updated = svc.update_note_text(note.id, "New Title", "Hello world")
        assert updated.title == "New Title"
        assert updated.content_text == "Hello world"

    def test_nonexistent_returns_none(self, svc: NoteService, notebook_id: int):
        result = svc.update_note_text(9999, "Title", "Content")
        assert result is None

    def test_content_too_long_raises(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "text")
        with pytest.raises(ValueError, match="50,000"):
            svc.update_note_text(note.id, "Title", "x" * 50_001)

    def test_empty_title_becomes_untitled(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "text", "Name")
        updated = svc.update_note_text(note.id, "  ", "body")
        assert updated.title == "Untitled"


# ---------------------------------------------------------------------------
# delete_note
# ---------------------------------------------------------------------------

class TestDeleteNote:
    def test_deletes_note(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "text", "Temp")
        svc.delete_note(note.id)
        assert svc.get_notes_for_notebook(notebook_id) == []

    def test_delete_cleans_image_files(self, svc: NoteService, notebook_id: int, tmp_path):
        """Deleting a note should delete attached image files from disk."""
        note = svc.create_note(notebook_id, "image", "Img Note")
        # Create a real temp image file to attach
        fake_img = tmp_path / "test.jpg"
        fake_img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)  # minimal JPEG-like bytes
        img_rec = svc.add_image(note.id, str(fake_img))
        abs_stored = svc.resolve_image_path(img_rec.image_path)
        assert os.path.isfile(abs_stored)

        svc.delete_note(note.id)
        assert not os.path.isfile(abs_stored)


# ---------------------------------------------------------------------------
# add_image / delete_image
# ---------------------------------------------------------------------------

class TestImageOps:
    def test_add_image(self, svc: NoteService, notebook_id: int, tmp_path):
        note = svc.create_note(notebook_id, "image")
        fake = tmp_path / "pic.png"
        fake.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        img = svc.add_image(note.id, str(fake))
        assert img.id is not None
        assert img.note_id == note.id
        abs_path = svc.resolve_image_path(img.image_path)
        assert os.path.isfile(abs_path)

    def test_add_nonexistent_image_raises(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "image")
        with pytest.raises(ValueError, match="not found"):
            svc.add_image(note.id, "/no/such/file.jpg")

    def test_delete_image_removes_file(self, svc: NoteService, notebook_id: int, tmp_path):
        note = svc.create_note(notebook_id, "image")
        fake = tmp_path / "del.jpg"
        fake.write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)
        img = svc.add_image(note.id, str(fake))
        abs_path = svc.resolve_image_path(img.image_path)
        assert os.path.isfile(abs_path)
        svc.delete_image(img.id)
        assert not os.path.isfile(abs_path)

    def test_get_images_for_note(self, svc: NoteService, notebook_id: int, tmp_path):
        note = svc.create_note(notebook_id, "image")
        for i in range(2):
            f = tmp_path / f"img{i}.png"
            f.write_bytes(b"\x89PNG\r\n" + b"\x00" * 20)
            svc.add_image(note.id, str(f))
        imgs = svc.get_images_for_note(note.id)
        assert len(imgs) == 2


# ---------------------------------------------------------------------------
# get_doodles_for_note
# ---------------------------------------------------------------------------

class TestDoodleOps:
    def test_no_doodles_initially(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "doodle")
        assert svc.get_doodles_for_note(note.id) == []

    def test_save_doodle_moves_file(self, svc: NoteService, notebook_id: int, tmp_path):
        note = svc.create_note(notebook_id, "doodle")
        png = tmp_path / "draw.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        doodle = svc.save_doodle(note.id, str(png))
        assert doodle.id is not None
        abs_path = svc.resolve_doodle_path(doodle.doodle_path)
        assert os.path.isfile(abs_path)
        # Original file should be moved (no longer at src)
        assert not png.exists()

    def test_save_nonexistent_doodle_raises(self, svc: NoteService, notebook_id: int):
        note = svc.create_note(notebook_id, "doodle")
        with pytest.raises(ValueError, match="not found"):
            svc.save_doodle(note.id, "/no/file.png")
