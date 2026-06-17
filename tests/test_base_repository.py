"""Tests for BaseRepository generic CRUD operations."""
from __future__ import annotations

import pytest

from models.category import Category
from repositories.base_repository import BaseRepository
from observers.event_bus import Events


class CategoryRepo(BaseRepository[Category]):
    """Minimal concrete subclass for testing BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Category, Events.CATEGORY_WRITE)


def _make_cat(name: str = "Test", is_default: bool = False) -> Category:
    return Category(name=name, icon=None, color="#000000", is_default=is_default)


class TestInsert:
    def test_insert_returns_entity_with_id(self, fresh_db) -> None:
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("Food"))
        assert cat.id is not None
        assert isinstance(cat.id, int)

    def test_insert_persists_data(self, fresh_db) -> None:
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("Groceries"))
        fetched = repo.get_by_id(cat.id)
        assert fetched is not None
        assert fetched.name == "Groceries"


class TestGetById:
    def test_returns_none_for_missing_id(self, fresh_db) -> None:
        repo = CategoryRepo()
        assert repo.get_by_id(9999) is None

    def test_returns_correct_entity(self, fresh_db) -> None:
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("Transport"))
        result = repo.get_by_id(cat.id)
        assert result.name == "Transport"


class TestGetAll:
    def test_empty_table_returns_empty_list(self, fresh_db) -> None:
        repo = CategoryRepo()
        assert repo.get_all() == []

    def test_returns_all_inserted(self, fresh_db) -> None:
        repo = CategoryRepo()
        repo.insert(_make_cat("A"))
        repo.insert(_make_cat("B"))
        repo.insert(_make_cat("C"))
        assert len(repo.get_all()) == 3


class TestUpdate:
    def test_update_changes_field(self, fresh_db) -> None:
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("Old"))
        cat.name = "New"
        updated = repo.update(cat)
        assert updated.name == "New"
        assert repo.get_by_id(cat.id).name == "New"


class TestDelete:
    def test_delete_existing_returns_true(self, fresh_db) -> None:
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("DeleteMe"))
        assert repo.delete(cat.id) is True

    def test_delete_removes_entity(self, fresh_db) -> None:
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("Gone"))
        repo.delete(cat.id)
        assert repo.get_by_id(cat.id) is None

    def test_delete_missing_id_returns_false(self, fresh_db) -> None:
        repo = CategoryRepo()
        assert repo.delete(99999) is False

    def test_delete_accepts_int(self, fresh_db) -> None:
        """Regression guard: delete() must receive an int, not an ORM object."""
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("IntCheck"))
        result = repo.delete(cat.id)
        assert result is True


class TestEventBusFiredOnWrite:
    def test_insert_fires_event(self, fresh_db) -> None:
        from observers.event_bus import get_bus
        received = []
        get_bus().subscribe(Events.CATEGORY_WRITE, lambda data: received.append(data))
        repo = CategoryRepo()
        repo.insert(_make_cat("EventTest"))
        assert len(received) == 1
        assert "id" in received[0]

    def test_delete_fires_event(self, fresh_db) -> None:
        from observers.event_bus import get_bus
        received = []
        repo = CategoryRepo()
        cat = repo.insert(_make_cat("EventDelete"))
        get_bus().subscribe(Events.CATEGORY_WRITE, lambda data: received.append(data))
        repo.delete(cat.id)
        assert len(received) == 1
