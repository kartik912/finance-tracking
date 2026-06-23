"""ORM model for the notes table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from config.database import Base


class Note(Base):
    """A single note inside a notebook (text, image, or doodle type)."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notebook_id = Column(
        Integer, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(500))
    content_text = Column(Text)
    content_strokes = Column(Text, nullable=True)  # JSON list of stroke dicts
    note_type = Column(String(20), nullable=False)
    created_at = Column(String(30), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "title": self.title,
            "content_text": self.content_text,
            "content_strokes": self.content_strokes,
            "note_type": self.note_type,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return f"<Note id={self.id} type={self.note_type!r} title={self.title!r}>"
