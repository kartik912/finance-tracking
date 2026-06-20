"""Repository for the notes table."""
from __future__ import annotations

from config.database import get_session
from models.note import Note
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """CRUD operations for :class:`~models.note.Note`.

    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Note, Events.NOTE_WRITE)

    def get_by_notebook(self, notebook_id: int) -> list[Note]:
        """Return all notes for a notebook, ordered newest first."""
        session = get_session()
        try:
            return (
                session.query(Note)
                .filter(Note.notebook_id == notebook_id)
                .order_by(Note.created_at.desc())
                .all()
            )
        finally:
            session.remove()

    def count_by_notebook(self, notebook_id: int) -> int:
        """Return the number of notes in a notebook."""
        session = get_session()
        try:
            return (
                session.query(Note)
                .filter(Note.notebook_id == notebook_id)
                .count()
            )
        finally:
            session.remove()
