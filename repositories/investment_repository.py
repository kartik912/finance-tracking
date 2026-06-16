"""Repository for the investments table."""
from __future__ import annotations

from config.database import get_session
from models.investment import Investment
from repositories.base_repository import BaseRepository


class InvestmentRepository(BaseRepository[Investment]):
    """CRUD operations for :class:`~models.investment.Investment`."""

    def get_by_id(self, entity_id: int) -> Investment | None:
        """Return an Investment by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Investment, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Investment]:
        """Return all investments ordered by id."""
        session = get_session()
        try:
            return session.query(Investment).order_by(Investment.id).all()
        finally:
            session.remove()

    def insert(self, entity: Investment) -> Investment:
        """Persist a new investment and return it with its assigned id."""
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

    def update(self, entity: Investment) -> Investment:
        """Merge changes to an existing investment and return the updated instance."""
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
        """Delete an investment by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Investment, entity_id)
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
