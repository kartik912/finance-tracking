"""Repository for the people table."""
from __future__ import annotations

from config.database import get_session
from models.person import Person
from observers.event_bus import Events, get_bus
from repositories.base_repository import BaseRepository


class PersonRepository(BaseRepository[Person]):
    """CRUD operations for :class:`~models.person.Person`."""

    def get_by_id(self, entity_id: int) -> Person | None:
        """Return a Person by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(Person, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[Person]:
        """Return all people ordered by id."""
        session = get_session()
        try:
            return session.query(Person).order_by(Person.id).all()
        finally:
            session.remove()

    def insert(self, entity: Person) -> Person:
        """Persist a new person and return it with its assigned id."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            get_bus().publish(Events.PERSON_WRITE, {"id": entity.id})
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: Person) -> Person:
        """Merge changes to an existing person and return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            get_bus().publish(Events.PERSON_WRITE, {"id": merged.id})
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete a person by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(Person, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            get_bus().publish(Events.PERSON_WRITE, {"id": entity_id})
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
