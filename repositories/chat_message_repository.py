"""Repository for the chat_messages table."""
from __future__ import annotations

from models.chat_message import ChatMessage
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """CRUD operations for :class:`~models.chat_message.ChatMessage`.

    Add chat-specific query methods here (e.g. get_last_n, get_by_role).
    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(ChatMessage, Events.CHAT_MESSAGE_WRITE)
