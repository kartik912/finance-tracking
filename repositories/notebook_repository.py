"""Repository for the notebooks table."""
from __future__ import annotations

from config.database import get_session
from models.notebook import Notebook
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class NotebookRepository(BaseRepository[Notebook]):
    """CRUD operations for :class:`~models.notebook.Notebook`.

    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Notebook, Events.NOTEBOOK_WRITE)

    def get_all_ordered(self) -> list[Notebook]:
        """Return all notebooks ordered by created_at descending."""
        session = get_session()
        try:
            return (
                session.query(Notebook)
                .order_by(Notebook.created_at.desc(), Notebook.id.desc())
                .all()
            )
        finally:
            session.remove()
