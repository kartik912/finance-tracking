"""Repository for the goals table."""
from __future__ import annotations

from models.goal import Goal
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class GoalRepository(BaseRepository[Goal]):
    """CRUD operations for :class:`~models.goal.Goal`.

    Add goal-specific query methods here (e.g. get_by_category, get_in_progress).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Goal, Events.GOAL_WRITE)
