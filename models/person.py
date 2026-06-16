"""ORM model for the people table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Integer, String

from config.database import Base


class Person(Base):
    """A contact used for debt tracking and bill splits."""

    __tablename__ = "people"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    notes = Column(String(500))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "name": self.name,
            "notes": self.notes,
        }

    def __repr__(self) -> str:
        return f"<Person id={self.id} name={self.name!r}>"
