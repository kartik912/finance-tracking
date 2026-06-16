"""Repository for the note_images table."""
from __future__ import annotations

from config.database import get_session
from models.note_image import NoteImage
from repositories.base_repository import BaseRepository


class NoteImageRepository(BaseRepository[NoteImage]):
    """CRUD operations for :class:`~models.note_image.NoteImage`."""

    def get_by_id(self, entity_id: int) -> NoteImage | None:
        """Return a NoteImage by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(NoteImage, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[NoteImage]:
        """Return all note images ordered by id."""
        session = get_session()
        try:
            return session.query(NoteImage).order_by(NoteImage.id).all()
        finally:
            session.remove()

    def insert(self, entity: NoteImage) -> NoteImage:
        """Persist a new note image and return it with its assigned id."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: NoteImage) -> NoteImage:
        """Merge changes to an existing note image and return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete a note image by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(NoteImage, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
