"""Repository for the notebooks table."""
from __future__ import annotations

from config.database import get_session
from models.notebook import Notebook
from repositories.base_repository import BaseRepository


class NotebookRepository(BaseRepository[Notebook]):
    """CRUD operations for :class:`~models.notebook.Notebook`."""

    def get_by_id(self, entity_id: int) -> Notebook | None:
        """Return a Notebook by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Notebook, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Notebook]:
        """Return all notebooks ordered by id."""
        session = get_session()
        try:
            return session.query(Notebook).order_by(Notebook.id).all()
        finally:
            session.remove()

    def insert(self, entity: Notebook) -> Notebook:
        """Persist a new notebook and return it with its assigned id."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: Notebook) -> Notebook:
        """Merge changes to an existing notebook and return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete a notebook by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Notebook, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
