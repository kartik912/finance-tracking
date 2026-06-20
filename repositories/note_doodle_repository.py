"""Repository for the note_doodles table."""
from __future__ import annotations

from config.database import get_session
from models.note_doodle import NoteDoodle
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NoteDoodleRepository(BaseRepository[NoteDoodle]):
    """CRUD operations for :class:`~models.note_doodle.NoteDoodle`.

    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(NoteDoodle, Events.NOTE_DOODLE_WRITE)

    def get_by_note(self, note_id: int) -> list[NoteDoodle]:
        """Return all doodles attached to a note."""
        session = get_session()
        try:
            return (
                session.query(NoteDoodle)
                .filter(NoteDoodle.note_id == note_id)
                .order_by(NoteDoodle.id.asc())
                .all()
            )
        finally:
            session.remove()
