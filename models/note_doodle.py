"""ORM model for the note_doodles table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, ForeignKey, Integer, String

from config.database import Base


class NoteDoodle(Base):
    """A relative path to a doodle PNG attached to a note."""

    __tablename__ = "note_doodles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    # Stored as a path relative to the app data directory.
    # Reconstruct the absolute path at read time.
    doodle_path = Column(String(500), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "note_id": self.note_id,
            "doodle_path": self.doodle_path,
        }

    def __repr__(self) -> str:
        return f"<NoteDoodle id={self.id} note_id={self.note_id}>"
