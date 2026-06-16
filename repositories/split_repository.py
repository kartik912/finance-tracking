"""Repository for the splits table."""
from __future__ import annotations

from models.split import Split
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class SplitRepository(BaseRepository[Split]):
    """CRUD operations for :class:`~models.split.Split`.

    Add split-specific query methods here (e.g. get_recent).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Split, Events.SPLIT_WRITE)
