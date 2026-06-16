"""Repository for the chat_messages table."""
from __future__ import annotations

from config.database import get_session
from models.chat_message import ChatMessage
from repositories.base_repository import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """CRUD operations for :class:`~models.chat_message.ChatMessage`."""

    def get_by_id(self, entity_id: int) -> ChatMessage | None:
        """Return a ChatMessage by primary key, or ``None`` if not found."""
        session = get_session()
        try:
            return session.get(ChatMessage, entity_id)
        finally:
            session.remove()

    def get_all(self) -> list[ChatMessage]:
        """Return all chat messages ordered by id."""
        session = get_session()
        try:
            return session.query(ChatMessage).order_by(ChatMessage.id).all()
        finally:
            session.remove()

    def insert(self, entity: ChatMessage) -> ChatMessage:
        """Persist a new chat message and return it with its assigned id."""
        session = get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def update(self, entity: ChatMessage) -> ChatMessage:
        """Merge changes to an existing chat message and return the updated instance."""
        session = get_session()
        try:
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()

    def delete(self, entity_id: int) -> bool:
        """Delete a chat message by id. Returns ``True`` if deleted, ``False`` if not found."""
        session = get_session()
        try:
            obj = session.get(ChatMessage, entity_id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.remove()
