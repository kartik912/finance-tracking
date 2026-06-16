"""ORM model for the splits table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Float, Integer, String, Text

from config.database import Base


class Split(Base):
    """A shared bill split among multiple people."""

    __tablename__ = "splits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String(500), nullable=False)
    total_amount = Column(Float, nullable=False)
    date = Column(String(20), nullable=False)
    # JSON-encoded list of member objects: [{"name": ..., "share": ...}, ...]
    members_json = Column(Text, nullable=False)
    my_share = Column(Float, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "description": self.description,
            "total_amount": self.total_amount,
            "date": self.date,
            "members_json": self.members_json,
            "my_share": self.my_share,
        }

    def __repr__(self) -> str:
        return f"<Split id={self.id} total={self.total_amount}>"
