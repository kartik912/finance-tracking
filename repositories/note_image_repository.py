"""Repository for the note_images table."""
from __future__ import annotations

from config.database import get_session
from models.note_image import NoteImage
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NoteImageRepository(BaseRepository[NoteImage]):
    """CRUD operations for :class:`~models.note_image.NoteImage`.

    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(NoteImage, Events.NOTE_IMAGE_WRITE)

    def get_by_note(self, note_id: int) -> list[NoteImage]:
        """Return all images attached to a note."""
        session = get_session()
        try:
            return (
                session.query(NoteImage)
                .filter(NoteImage.note_id == note_id)
                .order_by(NoteImage.id.asc())
                .all()
            )
        finally:
            session.remove()
