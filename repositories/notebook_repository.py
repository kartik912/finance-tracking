"""Repository for the notebooks table."""
from __future__ import annotations

from models.notebook import Notebook
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NotebookRepository(BaseRepository[Notebook]):
    """CRUD operations for :class:`~models.notebook.Notebook`.

    Add notebook-specific query methods here (e.g. get_by_name).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Notebook, Events.NOTEBOOK_WRITE)
