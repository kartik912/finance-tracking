"""Repository for the note_doodles table."""
from __future__ import annotations

from models.note_doodle import NoteDoodle
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NoteDoodleRepository(BaseRepository[NoteDoodle]):
    """CRUD operations for :class:`~models.note_doodle.NoteDoodle`.

    Add doodle-specific query methods here (e.g. get_by_note).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(NoteDoodle, Events.NOTE_DOODLE_WRITE)
