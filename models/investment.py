"""ORM model for the investments table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Float, Integer, String

from config.database import Base


class Investment(Base):
    """A single investment holding (stock, MF, FD, crypto, etc.)."""

    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    # DB column is 'type'; mapped to investment_type to avoid SQLAlchemy
    # polymorphic-discriminator collision.
    investment_type = Column("type", String(50), nullable=False)
    amount_invested = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    date = Column(String(20), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.investment_type,
            "amount_invested": self.amount_invested,
            "current_value": self.current_value,
            "date": self.date,
        }
