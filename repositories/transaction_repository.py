"""Repository for the transactions table."""
from __future__ import annotations

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
