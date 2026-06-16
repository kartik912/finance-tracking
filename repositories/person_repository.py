"""Repository for the persons table."""
from __future__ import annotations

from models.person import Person
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class PersonRepository(BaseRepository[Person]):
    """CRUD operations for :class:`~models.person.Person`.

    Add person-specific query methods here (e.g. get_by_name).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Person, Events.PERSON_WRITE)
