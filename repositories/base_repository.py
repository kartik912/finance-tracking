"""Abstract base repository defining the standard CRUD interface.

Every concrete repository must subclass ``BaseRepository[T]`` and implement
all five abstract methods. No SQL or ORM logic lives here — only the contract.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Generic CRUD contract for all entity repositories.

    Type parameter ``T`` is the SQLAlchemy ORM model class the repository manages.
    """

    @abstractmethod
    def get_by_id(self, entity_id: int) -> T | None:
        """Return a single entity by primary key, or ``None`` if not found."""

    @abstractmethod
    def get_all(self) -> list[T]:
        """Return all rows for this entity, ordered by primary key ascending."""

    @abstractmethod
    def insert(self, entity: T) -> T:
        """Persist a new entity and return it with its assigned primary key."""

    @abstractmethod
    def update(self, entity: T) -> T:
        """Merge and persist changes to an existing entity; return the updated instance."""

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete the entity with the given primary key.

        Returns ``True`` if a row was deleted, ``False`` if nothing was found.
        """
