"""ORM model for the note_images table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, ForeignKey, Integer, String

from config.database import Base


class NoteImage(Base):
    """A relative path to an image attached to a note."""

    __tablename__ = "note_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    # Stored as a path relative to the app data directory.
    # Reconstruct the absolute path at read time.
    image_path = Column(String(500), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "note_id": self.note_id,
            "image_path": self.image_path,
        }

    def __repr__(self) -> str:
        return f"<NoteImage id={self.id} note_id={self.note_id}>"
