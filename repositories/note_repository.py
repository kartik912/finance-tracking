"""Repository for the notes table."""
from __future__ import annotations

from config.database import get_session
from models.note import Note
from repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """CRUD operations for :class:`~models.note.Note`."""

    def get_by_id(self, entity_id: int) -> Note | None:
        """Return a Note by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Note, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Note]:
        """Return all notes ordered by id."""
        session = get_session()
        try:
            return session.query(Note).order_by(Note.id).all()
        finally:
            session.remove()

    def insert(self, entity: Note) -> Note:
        """Persist a new note and return it with its assigned id."""
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

    def update(self, entity: Note) -> Note:
        """Merge changes to an existing note and return the updated instance."""
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
        """Delete a note by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Note, entity_id)
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
