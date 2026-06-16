"""ORM model for the categories table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Column, Integer, String

from config.database import Base


class Category(Base):
    """Expense/income category with an optional icon and color."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    icon = Column(String(100))
    color = Column(String(20))
    is_default = Column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "is_default": self.is_default,
        }

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
