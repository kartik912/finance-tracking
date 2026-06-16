"""In-process cache service backed by ``cachetools``.

Two cache tiers
---------------
* **LRU cache** (``_lru``) — max 128 entries; used for list queries that
  should stay fresh as long as memory allows.
* **TTL cache** (``_ttl``) — 60-second expiry; used for aggregates and
  summaries that can tolerate being slightly stale.

Auto-invalidation
-----------------
On startup, :func:`register_invalidators` subscribes a handler for every
``*.write`` event published by the repositories. When a write occurs, all
cache keys that belong to the affected entity group are removed from both
tiers so the next read fetches fresh data.

Thread safety
-------------
All reads and writes to both caches are wrapped in ``_lock`` so concurrent
Flet/Flutter threads cannot corrupt the cache state.

Usage::

    from services.cache_service import CacheService

    cache = CacheService.instance()
    cache.register_invalidators()     # call once from main.py

    # Store a value
    cache.set_lru("categories:all", categories_list)

    # Retrieve (returns None on miss or expiry)
    result = cache.get_lru("categories:all")

    # Manually invalidate a group
    cache.invalidate("categories")
"""
from __future__ import annotations

import threading
from typing import Any

from cachetools import LRUCache, TTLCache

from observers.event_bus import Events, get_bus

# Cache key group → matching key prefixes to invalidate on write
_INVALIDATION_MAP: dict[str, str] = {
    Events.CATEGORY_WRITE:     "categories",
    Events.TRANSACTION_WRITE:  "transactions",
    Events.PERSON_WRITE:       "people",
    Events.DEBT_WRITE:         "debts",
    Events.SPLIT_WRITE:        "splits",
    Events.INVESTMENT_WRITE:   "investments",
    Events.GOAL_WRITE:         "goals",
    Events.NOTEBOOK_WRITE:     "notebooks",
    Events.NOTE_WRITE:         "notes",
    Events.NOTE_IMAGE_WRITE:   "note_images",
    Events.NOTE_DOODLE_WRITE:  "note_doodles",
    Events.CHAT_MESSAGE_WRITE: "chat_messages",
}


class CacheService:
    """Thread-safe two-tier in-process cache (LRU + TTL).

    Use :meth:`instance` to obtain the singleton — never instantiate directly.
    """

    _instance: CacheService | None = None
    _class_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._lru: LRUCache = LRUCache(maxsize=128)
        self._ttl: TTLCache = TTLCache(maxsize=128, ttl=60)

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> CacheService:
        """Return the application-wide singleton :class:`CacheService`."""
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # LRU cache operations
    # ------------------------------------------------------------------

    def get_lru(self, key: str) -> Any | None:
        """Return the LRU-cached value for *key*, or ``None`` on a miss."""
        with self._lock:
            return self._lru.get(key)

    def set_lru(self, key: str, value: Any) -> None:
        """Store *value* in the LRU cache under *key*."""
        with self._lock:
            self._lru[key] = value

    # ------------------------------------------------------------------
    # TTL cache operations
    # ------------------------------------------------------------------

    def get_ttl(self, key: str) -> Any | None:
        """Return the TTL-cached value for *key*, or ``None`` on miss/expiry."""
        with self._lock:
            return self._ttl.get(key)

    def set_ttl(self, key: str, value: Any) -> None:
        """Store *value* in the TTL cache under *key* (expires after 60 s)."""
        with self._lock:
            self._ttl[key] = value

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------

    def invalidate(self, prefix: str) -> None:
        """Remove every key that starts with *prefix* from both cache tiers.

        Example: ``invalidate("categories")`` removes ``"categories:all"``,
        ``"categories:1"``, etc.
        """
        with self._lock:
            for cache in (self._lru, self._ttl):
                stale = [k for k in list(cache.keys()) if k.startswith(prefix)]
                for key in stale:
                    cache.pop(key, None)

    def clear(self) -> None:
        """Flush both cache tiers entirely (useful for testing)."""
        with self._lock:
            self._lru.clear()
            self._ttl.clear()

    # ------------------------------------------------------------------
    # EventBus integration
    # ------------------------------------------------------------------

    def register_invalidators(self) -> None:
        """Subscribe to all ``*.write`` events so caches auto-invalidate.

        Call this once from ``main.py`` after ``init_db()`` and before
        navigating to any screen.
        """
        bus = get_bus()
        for event, prefix in _INVALIDATION_MAP.items():
            # Capture prefix in the default arg to avoid closure over loop var
            def _handler(data: Any, _prefix: str = prefix) -> None:
                self.invalidate(_prefix)

            bus.subscribe(event, _handler)
