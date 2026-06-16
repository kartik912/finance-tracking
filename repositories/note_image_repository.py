"""Repository for the note_images table."""
from __future__ import annotations

from models.note_image import NoteImage
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NoteImageRepository(BaseRepository[NoteImage]):
    """CRUD operations for :class:`~models.note_image.NoteImage`.

    Add image-specific query methods here (e.g. get_by_note).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(NoteImage, Events.NOTE_IMAGE_WRITE)
