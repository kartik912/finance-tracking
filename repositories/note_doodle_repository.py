"""Repository for the note_doodles table."""
from __future__ import annotations

from config.database import get_session
from models.note_doodle import NoteDoodle
from repositories.base_repository import BaseRepository


class NoteDoodleRepository(BaseRepository[NoteDoodle]):
    """CRUD operations for :class:`~models.note_doodle.NoteDoodle`."""

    def get_by_id(self, entity_id: int) -> NoteDoodle | None:
        """Return a NoteDoodle by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(NoteDoodle, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[NoteDoodle]:
        """Return all note doodles ordered by id."""
        session = get_session()
        try:
            return session.query(NoteDoodle).order_by(NoteDoodle.id).all()
        finally:
            session.remove()

    def insert(self, entity: NoteDoodle) -> NoteDoodle:
        """Persist a new note doodle and return it with its assigned id."""
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

    def update(self, entity: NoteDoodle) -> NoteDoodle:
        """Merge changes to an existing note doodle and return the updated instance."""
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
        """Delete a note doodle by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(NoteDoodle, entity_id)
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
