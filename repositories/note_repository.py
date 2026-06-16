"""Repository for the notes table."""
from __future__ import annotations

from models.note import Note
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """CRUD operations for :class:`~models.note.Note`.

    Add note-specific query methods here (e.g. get_by_notebook, get_by_type).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Note, Events.NOTE_WRITE)
