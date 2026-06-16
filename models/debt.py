"""ORM model for the debts table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String

from config.database import Base


class Debt(Base):
    """A debt record between the user and a contact."""

    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(
        Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    amount = Column(Float, nullable=False)
    # 'i_owe' or 'they_owe'
    direction = Column(String(20), nullable=False)
    description = Column(String(500))
    settled = Column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "amount": self.amount,
            "direction": self.direction,
            "description": self.description,
            "settled": self.settled,
        }
