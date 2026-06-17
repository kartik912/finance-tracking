"""Tests for CacheService — LRU eviction, TTL, and EventBus invalidation."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from cachetools import TTLCache

from services.cache_service import CacheService


@pytest.fixture()
def cache(fresh_db) -> CacheService:
    """Return a fresh CacheService instance for each test."""
    CacheService._instance = None
    svc = CacheService.instance()
    svc.clear()
    return svc


class TestLRUCache:
    def test_set_and_get(self, cache) -> None:
        cache.set_lru("test:key", [1, 2, 3])
        assert cache.get_lru("test:key") == [1, 2, 3]

    def test_miss_returns_none(self, cache) -> None:
        assert cache.get_lru("nonexistent:key") is None

    def test_evicts_at_capacity(self, cache) -> None:
        """LRU cache must not grow beyond maxsize=128."""
        for i in range(130):
            cache.set_lru(f"key:{i}", i)
        # After 130 inserts the cache holds at most 128 entries
        assert len(cache._lru) <= 128


class TestTTLCache:
    def test_set_and_get(self, cache) -> None:
        cache.set_ttl("ttl:key", "value")
        assert cache.get_ttl("ttl:key") == "value"

    def test_miss_returns_none(self, cache) -> None:
        assert cache.get_ttl("nonexistent") is None

    def test_expired_entry_returns_none(self, cache) -> None:
        """TTL entries must expire — simulate time passing by patching TTLCache."""
        # Replace the internal TTL cache with one that has 0.01s TTL
        cache._ttl = TTLCache(maxsize=128, ttl=0.01)
        cache.set_ttl("fast:expire", "hello")
        time.sleep(0.05)
        assert cache.get_ttl("fast:expire") is None


class TestInvalidate:
    def test_invalidate_removes_matching_lru_key(self, cache) -> None:
        cache.set_lru("splits:all", ["a", "b"])
        cache.invalidate("splits")
        assert cache.get_lru("splits:all") is None

    def test_invalidate_removes_matching_ttl_key(self, cache) -> None:
        cache.set_ttl("splits:summary", 999)
        cache.invalidate("splits")
        assert cache.get_ttl("splits:summary") is None

    def test_invalidate_does_not_remove_unrelated_keys(self, cache) -> None:
        cache.set_lru("categories:all", ["cat1"])
        cache.invalidate("splits")
        assert cache.get_lru("categories:all") == ["cat1"]

    def test_clear_flushes_everything(self, cache) -> None:
        cache.set_lru("a:1", 1)
        cache.set_ttl("b:2", 2)
        cache.clear()
        assert cache.get_lru("a:1") is None
        assert cache.get_ttl("b:2") is None


class TestEventBusInvalidation:
    def test_split_write_event_clears_splits_cache(self, fresh_db) -> None:
        """Publishing SPLIT_WRITE should invalidate splits:* keys if invalidators registered."""
        from observers.event_bus import Events, get_bus
        CacheService._instance = None
        svc = CacheService.instance()
        svc.clear()
        svc.register_invalidators()

        svc.set_lru("splits:all", ["cached"])
        get_bus().publish(Events.SPLIT_WRITE, {"id": 1})
        assert svc.get_lru("splits:all") is None
