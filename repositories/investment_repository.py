"""Repository for the investments table."""
from __future__ import annotations

from models.investment import Investment
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class InvestmentRepository(BaseRepository[Investment]):
    """CRUD operations for :class:`~models.investment.Investment`.

    Add investment-specific query methods here (e.g. get_by_type).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Investment, Events.INVESTMENT_WRITE)
