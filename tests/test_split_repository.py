"""Tests for SplitRepository — get_recent query method."""
from __future__ import annotations

import pytest

from models.split import Split
from repositories.split_repository import SplitRepository


def _make_split(description: str, total: float, date: str, my_share: float) -> Split:
    import json
    members = [{"name": "Alice", "share": round(total - my_share, 2)}]
    return Split(
        description=description,
        total_amount=total,
        date=date,
        members_json=json.dumps(members),
        my_share=my_share,
    )


class TestGetRecent:
    def test_returns_empty_list_when_no_data(self, fresh_db) -> None:
        repo = SplitRepository()
        assert repo.get_recent() == []

    def test_returns_all_inserted_splits(self, fresh_db) -> None:
        repo = SplitRepository()
        repo.insert(_make_split("Lunch", 600.0, "2026-06-10", 200.0))
        repo.insert(_make_split("Dinner", 900.0, "2026-06-15", 300.0))
        result = repo.get_recent()
        assert len(result) == 2

    def test_ordered_by_date_newest_first(self, fresh_db) -> None:
        repo = SplitRepository()
        repo.insert(_make_split("Old", 300.0, "2026-05-01", 100.0))
        repo.insert(_make_split("New", 600.0, "2026-06-17", 200.0))
        result = repo.get_recent()
        assert result[0].date == "2026-06-17"
        assert result[1].date == "2026-05-01"

    def test_limit_respected(self, fresh_db) -> None:
        repo = SplitRepository()
        for i in range(5):
            repo.insert(_make_split(f"Split {i}", 300.0, f"2026-06-{10 + i:02d}", 100.0))
        result = repo.get_recent(limit=3)
        assert len(result) == 3


class TestInsertAndGetById:
    def test_round_trip(self, fresh_db) -> None:
        repo = SplitRepository()
        s = repo.insert(_make_split("Test", 900.0, "2026-06-17", 300.0))
        fetched = repo.get_by_id(s.id)
        assert fetched is not None
        assert fetched.description == "Test"
        assert fetched.total_amount == 900.0

    def test_get_by_id_missing_returns_none(self, fresh_db) -> None:
        repo = SplitRepository()
        assert repo.get_by_id(9999) is None
