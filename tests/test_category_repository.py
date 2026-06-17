"""Tests for CategoryRepository."""
from __future__ import annotations

import pytest

from models.category import Category
from repositories.category_repository import CategoryRepository


def _make_cat(name: str, is_default: bool = False) -> Category:
    return Category(name=name, icon=None, color="#AABBCC", is_default=is_default)


class TestInsertAndGetById:
    def test_round_trip(self, fresh_db) -> None:
        repo = CategoryRepository()
        cat = repo.insert(_make_cat("Food"))
        fetched = repo.get_by_id(cat.id)
        assert fetched is not None
        assert fetched.name == "Food"

    def test_inserted_id_is_int(self, fresh_db) -> None:
        repo = CategoryRepository()
        cat = repo.insert(_make_cat("Housing"))
        assert isinstance(cat.id, int)


class TestGetAll:
    def test_returns_all_inserted_categories(self, fresh_db) -> None:
        repo = CategoryRepository()
        repo.insert(_make_cat("A"))
        repo.insert(_make_cat("B"))
        result = repo.get_all()
        names = [c.name for c in result]
        assert "A" in names
        assert "B" in names

    def test_empty_db_returns_empty_list(self, fresh_db) -> None:
        repo = CategoryRepository()
        assert repo.get_all() == []


class TestDelete:
    def test_delete_removes_category(self, fresh_db) -> None:
        repo = CategoryRepository()
        cat = repo.insert(_make_cat("Temp"))
        repo.delete(cat.id)
        assert repo.get_by_id(cat.id) is None

    def test_delete_nonexistent_returns_false(self, fresh_db) -> None:
        repo = CategoryRepository()
        assert repo.delete(99999) is False
