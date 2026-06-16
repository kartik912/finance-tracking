"""Repository for the categories table."""
from __future__ import annotations

from config.database import get_session
from models.category import Category
from observers.event_bus import Events, get_bus
from repositories.base_repository import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """CRUD operations for :class:`~models.category.Category`."""

    def get_by_id(self, entity_id: int) -> Category | None:
        """Return a Category by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Category, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Category]:
        """Return all categories ordered by id."""
        session = get_session()
        try:
            return session.query(Category).order_by(Category.id).all()
        finally:
            session.remove()

    def insert(self, entity: Category) -> Category:
        """Persist a new category and return it with its assigned id."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            get_bus().publish(Events.CATEGORY_WRITE, {"id": entity.id})
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: Category) -> Category:
        """Merge changes to an existing category and return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            get_bus().publish(Events.CATEGORY_WRITE, {"id": merged.id})
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete a category by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Category, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            get_bus().publish(Events.CATEGORY_WRITE, {"id": entity_id})
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
