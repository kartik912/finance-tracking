"""ORM model for the goals table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Float, Integer, String

from config.database import Base


class Goal(Base):
    """A savings goal with a target amount and optional deadline."""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, nullable=False, default=0.0)
    deadline = Column(String(20))
    color = Column(String(20))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "deadline": self.deadline,
            "color": self.color,
        }

    def __repr__(self) -> str:
        return f"<Goal id={self.id} name={self.name!r} target={self.target_amount}>"
