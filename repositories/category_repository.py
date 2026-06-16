"""Repository for the categorys table."""
from __future__ import annotations

from models.category import Category
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """CRUD operations for :class:`~models.category.Category`.

    Add category-specific query methods here (e.g. get_defaults, get_by_name).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Category, Events.CATEGORY_WRITE)
