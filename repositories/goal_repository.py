"""Repository for the goals table."""
from __future__ import annotations

from config.database import get_session
from models.goal import Goal
from repositories.base_repository import BaseRepository


class GoalRepository(BaseRepository[Goal]):
    """CRUD operations for :class:`~models.goal.Goal`."""

    def get_by_id(self, entity_id: int) -> Goal | None:
        """Return a Goal by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Goal, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Goal]:
        """Return all goals ordered by id."""
        session = get_session()
        try:
            return session.query(Goal).order_by(Goal.id).all()
        finally:
            session.remove()

    def insert(self, entity: Goal) -> Goal:
        """Persist a new goal and return it with its assigned id."""
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

    def update(self, entity: Goal) -> Goal:
        """Merge changes to an existing goal and return the updated instance."""
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
        """Delete a goal by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Goal, entity_id)
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
