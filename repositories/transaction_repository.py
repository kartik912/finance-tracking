"""Repository for the transactions table."""
from __future__ import annotations

from config.database import get_session
from models.transaction import Transaction
from observers.event_bus import Events, get_bus
from repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """CRUD operations for :class:`~models.transaction.Transaction`."""

    def get_by_id(self, entity_id: int) -> Transaction | None:
        """Return a Transaction by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Transaction, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Transaction]:
        """Return all transactions ordered by id."""
        session = get_session()
        try:
            return session.query(Transaction).order_by(Transaction.id).all()
        finally:
            session.remove()

    def insert(self, entity: Transaction) -> Transaction:
        """Persist a new transaction and return it with its assigned id."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            get_bus().publish(Events.TRANSACTION_WRITE, {"id": entity.id})
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: Transaction) -> Transaction:
        """Merge changes to an existing transaction and return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            get_bus().publish(Events.TRANSACTION_WRITE, {"id": merged.id})
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete a transaction by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Transaction, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            get_bus().publish(Events.TRANSACTION_WRITE, {"id": entity_id})
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
