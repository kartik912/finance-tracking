"""ORM model for the notebooks table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Integer, String

from config.database import Base


class Notebook(Base):
    """A notebook that groups related notes together."""

    __tablename__ = "notebooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    color = Column(String(20))
    emoji = Column(String(10))
    created_at = Column(String(30), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "emoji": self.emoji,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return f"<Notebook id={self.id} name={self.name!r}>"
