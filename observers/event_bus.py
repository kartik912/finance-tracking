"""Lightweight synchronous pub/sub event bus.

Usage
-----
Repositories call ``get_bus().publish(event, data)`` after every write.
``CacheService`` calls ``get_bus().subscribe(event, handler)`` on startup
to auto-invalidate cached keys when data changes.

Events are plain strings (e.g. ``"category.write"``, ``"transaction.write"``).
Handlers are callables that receive the optional *data* payload.

Example::

    from observers.event_bus import get_bus

    bus = get_bus()
    bus.subscribe("category.write", lambda data: print("invalidate categories"))
    bus.publish("category.write", {"id": 1})
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable

Handler = Callable[[Any], None]


class EventBus:
    """Thread-safe synchronous pub/sub event bus.

    Handlers are called in subscription order on the same thread that
    calls ``publish``. For fire-and-forget behaviour, wrap handlers with
    ``threading.Thread`` inside the handler itself.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event: str, handler: Handler) -> None:
        """Register *handler* to be called whenever *event* is published.

        Subscribing the same handler twice for the same event is a no-op.
        """
        with self._lock:
            if handler not in self._handlers[event]:
                self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Handler) -> None:
        """Remove *handler* from *event*. Silently ignored if not subscribed."""
        with self._lock:
            handlers = self._handlers.get(event, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event: str, data: Any = None) -> None:
        """Call all handlers subscribed to *event*, passing *data*.

        A snapshot of the handler list is taken under the lock so that
        handlers may safely subscribe/unsubscribe during dispatch.
        """
        with self._lock:
            snapshot = list(self._handlers.get(event, []))

        for handler in snapshot:
            handler(data)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bus: EventBus | None = None
_bus_lock = threading.Lock()


def get_bus() -> EventBus:
    """Return the application-wide singleton :class:`EventBus` instance."""
    global _bus
    if _bus is None:
        with _bus_lock:
            if _bus is None:
                _bus = EventBus()
    return _bus


# ---------------------------------------------------------------------------
# Canonical event name constants (import these instead of raw strings)
# ---------------------------------------------------------------------------

class Events:
    """Namespace for all published event name constants."""

    CATEGORY_WRITE      = "category.write"
    TRANSACTION_WRITE   = "transaction.write"
    PERSON_WRITE        = "person.write"
    DEBT_WRITE          = "debt.write"
    SPLIT_WRITE         = "split.write"
    INVESTMENT_WRITE    = "investment.write"
    GOAL_WRITE          = "goal.write"
    NOTEBOOK_WRITE      = "notebook.write"
    NOTE_WRITE          = "note.write"
    NOTE_IMAGE_WRITE    = "note_image.write"
    NOTE_DOODLE_WRITE   = "note_doodle.write"
    CHAT_MESSAGE_WRITE  = "chat_message.write"
