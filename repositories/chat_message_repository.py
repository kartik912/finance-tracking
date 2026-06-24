"""Repository for the chat_messages table."""
from __future__ import annotations

from models.chat_message import ChatMessage
from observers.event_bus import Events, get_bus
from repositories.base_repository import BaseRepository
from config.database import get_session


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """CRUD operations for :class:`~models.chat_message.ChatMessage`.

    Extends the base with chat-specific queries: ordered history and clear-all.
    """

    def __init__(self) -> None:
        super().__init__(ChatMessage, Events.CHAT_MESSAGE_WRITE)

    def get_all_ordered(self) -> list[ChatMessage]:
        """Return all messages ordered oldest-first (by id ascending)."""
        session = get_session()
        try:
            return (
                session.query(ChatMessage)
                .order_by(ChatMessage.id)
                .all()
            )
        finally:
            session.remove()

    def get_last_n(self, n: int) -> list[ChatMessage]:
        """Return the *n* most recent messages, returned in chronological order."""
        session = get_session()
        try:
            rows = (
                session.query(ChatMessage)
                .order_by(ChatMessage.id.desc())
                .limit(n)
                .all()
            )
            return list(reversed(rows))
        finally:
            session.remove()

    def clear_all(self) -> None:
        """Delete every message in the conversation history."""
        session = get_session()
        try:
            session.query(ChatMessage).delete()
            session.commit()
            get_bus().publish(self._write_event)
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
