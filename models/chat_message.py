"""ORM model for the chat_messages table."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Integer, String, Text

from config.database import Base


class ChatMessage(Base):
    """A single message in the AI chatbot conversation history."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 'user' or 'model'
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(String(30), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for the UI layer."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
