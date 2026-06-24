"""Unit tests for ChatMessageRepository — get_all_ordered, get_last_n, clear_all."""
from __future__ import annotations

from datetime import datetime

import pytest

from models.chat_message import ChatMessage
from repositories.chat_message_repository import ChatMessageRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _msg(role: str, content: str) -> ChatMessage:
    return ChatMessage(
        role=role,
        content=content,
        timestamp=datetime.now().isoformat(timespec="seconds"),
    )


# ---------------------------------------------------------------------------
# get_all_ordered
# ---------------------------------------------------------------------------

class TestGetAllOrdered:
    def test_returns_empty_on_fresh_db(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        assert repo.get_all_ordered() == []

    def test_single_message_returned(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "hi"))
        result = repo.get_all_ordered()
        assert len(result) == 1
        assert result[0].content == "hi"

    def test_returns_messages_oldest_first(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "first"))
        repo.insert(_msg("model", "second"))
        repo.insert(_msg("user", "third"))
        result = repo.get_all_ordered()
        assert [m.content for m in result] == ["first", "second", "third"]

    def test_ids_ascending_in_result(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "alpha"))
        repo.insert(_msg("model", "beta"))
        result = repo.get_all_ordered()
        assert result[0].id < result[1].id


# ---------------------------------------------------------------------------
# get_last_n
# ---------------------------------------------------------------------------

class TestGetLastN:
    def test_returns_empty_on_fresh_db(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        assert repo.get_last_n(5) == []

    def test_returns_last_two_of_four(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "msg1"))
        repo.insert(_msg("model", "msg2"))
        repo.insert(_msg("user", "msg3"))
        repo.insert(_msg("model", "msg4"))
        result = repo.get_last_n(2)
        assert len(result) == 2
        assert result[0].content == "msg3"
        assert result[1].content == "msg4"

    def test_result_is_chronological_order(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "old"))
        repo.insert(_msg("model", "new"))
        result = repo.get_last_n(2)
        assert result[0].id < result[1].id

    def test_returns_all_when_n_exceeds_count(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "only"))
        result = repo.get_last_n(10)
        assert len(result) == 1
        assert result[0].content == "only"

    def test_n_equals_zero_returns_empty(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "something"))
        assert repo.get_last_n(0) == []


# ---------------------------------------------------------------------------
# clear_all
# ---------------------------------------------------------------------------

class TestClearAll:
    def test_clear_empties_table(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.insert(_msg("user", "hello"))
        repo.insert(_msg("model", "hi"))
        assert len(repo.get_all_ordered()) == 2
        repo.clear_all()
        assert repo.get_all_ordered() == []

    def test_clear_on_empty_table_does_not_raise(self, fresh_db) -> None:
        repo = ChatMessageRepository()
        repo.clear_all()  # must not raise
