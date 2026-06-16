"""ORM model for the transactions table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Float, ForeignKey, Integer, String

from config.database import Base


class Transaction(Base):
    """A single income or expense transaction."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    description = Column(String(500))
    # DB column is named 'type'; mapped to transaction_type to avoid
    # collision with SQLAlchemy's internal polymorphic 'type' attribute.
    transaction_type = Column("type", String(20), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="SET NULL"))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "date": self.date,
            "amount": self.amount,
            "category_id": self.category_id,
            "description": self.description,
            "type": self.transaction_type,
            "person_id": self.person_id,
        }

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.transaction_type!r} amount={self.amount}>"
