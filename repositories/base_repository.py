"""Concrete generic base repository with default CRUD implementation.

Every concrete repository subclasses ``BaseRepository[T]`` and calls::

    super().__init__(ModelClass, Events.X_WRITE)

in its ``__init__``. The five standard CRUD methods are fully implemented here,
so concrete repositories only need to add entity-specific query methods.

Architectural note
------------------
Moving CRUD logic here (rather than keeping a pure ABC) eliminates ~600 lines of
identical boilerplate across 12 repositories while preserving the Liskov
Substitution Principle — every concrete subclass still satisfies the full
contract.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from config.database import get_session
from observers.event_bus import get_bus

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic CRUD base for all entity repositories.

    Parameters
    ----------
    model_class:
        The SQLAlchemy ORM model class this repository manages.
    write_event:
        The ``Events.*`` constant published after every write (insert/update/delete).
    """

    def __init__(self, model_class: type[T], write_event: str) -> None:
        self._model_class = model_class
        self._write_event = write_event

    # ------------------------------------------------------------------
    # Standard CRUD — override only when custom behaviour is needed
    # ------------------------------------------------------------------

    def get_by_id(self, entity_id: int) -> T | None:
        """Return a single entity by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(self._model_class, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[T]:
        """Return all rows ordered by primary key ascending."""
        session = get_session()
        try:
            return (
                session.query(self._model_class)
                .order_by(self._model_class.id)
                .all()
            )
        finally:
            session.remove()

    def insert(self, entity: T) -> T:
        """Persist a new entity and return it with its assigned primary key."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            get_bus().publish(self._write_event, {"id": entity.id})  # type: ignore[attr-defined]
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: T) -> T:
        """Merge and persist changes to an existing entity; return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            get_bus().publish(self._write_event, {"id": merged.id})  # type: ignore[attr-defined]
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete the entity with the given primary key.

        Returns ``True`` if a row was deleted, ``False`` if nothing was found.
        """
        session = get_session()
        try:
            obj = session.get(self._model_class, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            get_bus().publish(self._write_event, {"id": entity_id})
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
