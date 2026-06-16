"""Repository for the debts table."""
from __future__ import annotations

from config.database import get_session
from models.debt import Debt
from repositories.base_repository import BaseRepository


class DebtRepository(BaseRepository[Debt]):
    """CRUD operations for :class:`~models.debt.Debt`."""

    def get_by_id(self, entity_id: int) -> Debt | None:
        """Return a Debt by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Debt, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Debt]:
        """Return all debts ordered by id."""
        session = get_session()
        try:
            return session.query(Debt).order_by(Debt.id).all()
        finally:
            session.remove()

    def insert(self, entity: Debt) -> Debt:
        """Persist a new debt record and return it with its assigned id."""
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

    def update(self, entity: Debt) -> Debt:
        """Merge changes to an existing debt and return the updated instance."""
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
        """Delete a debt by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Debt, entity_id)
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
