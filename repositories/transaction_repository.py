"""Repository for the transactions table."""
from __future__ import annotations

from config.database import get_session
from models.transaction import Transaction
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """CRUD operations for :class:`~models.transaction.Transaction`.

    Add transaction-specific query methods here (e.g. get_by_month, get_by_category).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Transaction, Events.TRANSACTION_WRITE)

    def get_by_month(self, year: int, month: int) -> list[Transaction]:
        """Return all transactions for *year*/*month*, newest first.

        Filters on the ``date`` column (stored as ``YYYY-MM-DD`` ISO strings)
        using a LIKE prefix match so no raw SQL is required.
        """
        session = get_session()
        try:
            prefix = f"{year:04d}-{month:02d}"
            return (
                session.query(Transaction)
                .filter(Transaction.date.like(f"{prefix}-%"))
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .all()
            )
        finally:
            session.remove()
