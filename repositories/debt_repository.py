"""Repository for the debts table."""
from __future__ import annotations

from models.debt import Debt
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class DebtRepository(BaseRepository[Debt]):
    """CRUD operations for :class:`~models.debt.Debt`.

    Add debt-specific query methods here (e.g. get_unsettled, get_by_person).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Debt, Events.DEBT_WRITE)
