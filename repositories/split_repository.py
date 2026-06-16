"""Repository for the splits table."""
from __future__ import annotations

from config.database import get_session
from models.split import Split
from observers.event_bus import Events, get_bus
from repositories.base_repository import BaseRepository


class SplitRepository(BaseRepository[Split]):
    """CRUD operations for :class:`~models.split.Split`."""

    def get_by_id(self, entity_id: int) -> Split | None:
        """Return a Split by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Split, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Split]:
        """Return all splits ordered by id."""
        session = get_session()
        try:
            return session.query(Split).order_by(Split.id).all()
        finally:
            session.remove()

    def insert(self, entity: Split) -> Split:
        """Persist a new split and return it with its assigned id."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            get_bus().publish(Events.SPLIT_WRITE, {"id": entity.id})
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: Split) -> Split:
        """Merge changes to an existing split and return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            get_bus().publish(Events.SPLIT_WRITE, {"id": merged.id})
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete a split by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Split, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            get_bus().publish(Events.SPLIT_WRITE, {"id": entity_id})
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
