"""Tests for SplitService — validation, happy paths, and cache behaviour."""
from __future__ import annotations

import pytest

from services.split_service import SplitService


@pytest.fixture()
def svc(fresh_db) -> SplitService:
    """Return a fresh SplitService singleton for each test."""
    SplitService._instance = None
    return SplitService.instance()


# ── Validation: total amount ──────────────────────────────────────────────────

class TestValidateAmount:
    def test_negative_total_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="greater than zero"):
            svc.add_split("X", -100, "2026-06-17", [{"name": "A", "share": 50}], 50)

    def test_zero_total_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="greater than zero"):
            svc.add_split("X", 0, "2026-06-17", [{"name": "A", "share": 0}], 0)

    def test_non_numeric_total_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="must be a number"):
            svc.add_split("X", "abc", "2026-06-17", [{"name": "A", "share": 50}], 50)


# ── Validation: description ───────────────────────────────────────────────────

class TestValidateDescription:
    def test_empty_description_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="required"):
            svc.add_split("", 600, "2026-06-17", [{"name": "A", "share": 300}], 300)

    def test_whitespace_only_description_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="required"):
            svc.add_split("   ", 600, "2026-06-17", [{"name": "A", "share": 300}], 300)


# ── Validation: date ─────────────────────────────────────────────────────────

class TestValidateDate:
    def test_invalid_date_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            svc.add_split("Dinner", 600, "not-a-date", [{"name": "A", "share": 300}], 300)


# ── Validation: members ───────────────────────────────────────────────────────

class TestValidateMembers:
    def test_empty_members_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="at least one"):
            svc.add_split("Dinner", 600, "2026-06-17", [], 600)

    def test_duplicate_member_name_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Dd]uplicate"):
            svc.add_split(
                "Dinner", 900, "2026-06-17",
                [{"name": "Alice", "share": 300}, {"name": "alice", "share": 300}],
                300,
            )


# ── Validation: share totals ──────────────────────────────────────────────────

class TestValidateShareTotals:
    def test_shares_under_total_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Ss]hares"):
            svc.add_split("Dinner", 1000, "2026-06-17", [{"name": "Alice", "share": 300}], 300)

    def test_shares_over_total_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Ss]hares"):
            svc.add_split("Dinner", 1000, "2026-06-17", [{"name": "Alice", "share": 600}], 600)

    def test_my_share_exceeds_total_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Cc]annot be greater"):
            svc.add_split("Dinner", 500, "2026-06-17", [{"name": "Bob", "share": 100}], 600)

    def test_within_one_rupee_tolerance_accepted(self, svc) -> None:
        """Shares within ±₹1 of total should NOT raise."""
        result = svc.add_split(
            "Dinner", 900, "2026-06-17",
            [{"name": "Alice", "share": 300}, {"name": "Bob", "share": 299.5}],
            300,
        )
        assert result.id is not None


# ── Happy path ────────────────────────────────────────────────────────────────

class TestAddSplitHappyPath:
    def test_returns_split_with_id(self, svc) -> None:
        result = svc.add_split(
            "Lunch", 600, "2026-06-17",
            [{"name": "Bob", "share": 200}, {"name": "Carol", "share": 200}],
            200,
        )
        assert result.id is not None
        assert isinstance(result.id, int)

    def test_stored_split_appears_in_get_all(self, svc) -> None:
        svc.add_split(
            "Dinner", 900, "2026-06-17",
            [{"name": "Alice", "share": 300}, {"name": "Bob", "share": 300}],
            300,
        )
        splits = svc.get_all_splits()
        assert len(splits) == 1
        assert splits[0].description == "Dinner"


# ── delete_split ──────────────────────────────────────────────────────────────

class TestDeleteSplit:
    def test_delete_removes_split(self, svc) -> None:
        s = svc.add_split(
            "Test", 600, "2026-06-17",
            [{"name": "Bob", "share": 300}],
            300,
        )
        svc.delete_split(s.id)
        assert svc.get_all_splits() == []

    def test_delete_nonexistent_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="not found"):
            svc.delete_split(9999)

    def test_delete_passes_int_to_repo(self, svc) -> None:
        """Regression: delete_split must pass int, not ORM object, to BaseRepository."""
        from unittest.mock import patch
        from repositories.base_repository import BaseRepository

        s = svc.add_split(
            "IntGuard", 600, "2026-06-17",
            [{"name": "X", "share": 300}],
            300,
        )
        calls = []
        original = BaseRepository.delete

        def spy(self, entity_id):
            calls.append(type(entity_id))
            return original(self, entity_id)

        with patch.object(BaseRepository, "delete", spy):
            svc.delete_split(s.id)

        assert calls == [int], f"Expected int, got {calls}"


# ── parse_members ─────────────────────────────────────────────────────────────

class TestParseMembers:
    def test_parses_valid_json(self, svc) -> None:
        import json
        from models.split import Split
        s = Split(members_json=json.dumps([{"name": "Alice", "share": 300}]))
        result = SplitService.parse_members(s)
        assert result == [{"name": "Alice", "share": 300}]

    def test_returns_empty_list_on_invalid_json(self, svc) -> None:
        from models.split import Split
        s = Split(members_json="not-json")
        assert SplitService.parse_members(s) == []

    def test_returns_empty_list_when_none(self, svc) -> None:
        from models.split import Split
        s = Split(members_json=None)
        assert SplitService.parse_members(s) == []


# ── Cache invalidation after delete ──────────────────────────────────────────

class TestCacheInvalidation:
    def test_cache_cleared_after_delete(self, svc) -> None:
        s = svc.add_split(
            "CacheTest", 600, "2026-06-17",
            [{"name": "Bob", "share": 300}],
            300,
        )
        # Prime the cache
        svc.get_all_splits()
        from services.cache_service import CacheService
        assert CacheService.instance().get_lru("splits:all") is not None

        # Delete invalidates cache via EventBus → CacheService
        from services.cache_service import CacheService as CS
        CS.instance().register_invalidators()
        svc.delete_split(s.id)
        assert CS.instance().get_lru("splits:all") is None
