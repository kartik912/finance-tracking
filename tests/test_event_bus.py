"""Tests for EventBus — subscribe, publish, multiple subscribers."""
from __future__ import annotations

import threading

import pytest

from observers.event_bus import EventBus, Events, get_bus


@pytest.fixture(autouse=True)
def fresh_bus() -> None:
    """Give each test a clean EventBus instance (independent of fresh_db)."""
    EventBus._instance = None  # type: ignore[attr-defined]
    yield
    EventBus._instance = None  # type: ignore[attr-defined]


class TestSubscribeAndPublish:
    def test_handler_invoked_on_publish(self) -> None:
        bus = get_bus()
        received: list = []
        bus.subscribe(Events.TRANSACTION_WRITE, lambda data: received.append(data))
        bus.publish(Events.TRANSACTION_WRITE, {"id": 42})
        assert received == [{"id": 42}]

    def test_multiple_subscribers_all_fire(self) -> None:
        bus = get_bus()
        log: list[str] = []
        bus.subscribe(Events.CATEGORY_WRITE, lambda d: log.append("A"))
        bus.subscribe(Events.CATEGORY_WRITE, lambda d: log.append("B"))
        bus.publish(Events.CATEGORY_WRITE, {})
        assert "A" in log
        assert "B" in log

    def test_unrelated_event_does_not_fire(self) -> None:
        bus = get_bus()
        fired: list = []
        bus.subscribe(Events.CATEGORY_WRITE, lambda d: fired.append(d))
        bus.publish(Events.TRANSACTION_WRITE, {"id": 1})
        assert fired == []

    def test_published_data_passed_to_handler(self) -> None:
        bus = get_bus()
        received: list = []
        bus.subscribe(Events.GOAL_WRITE, lambda d: received.append(d))
        payload = {"name": "Vacation", "amount": 50000}
        bus.publish(Events.GOAL_WRITE, payload)
        assert received[0] == payload

    def test_get_bus_returns_same_singleton(self) -> None:
        bus1 = get_bus()
        bus2 = get_bus()
        assert bus1 is bus2

    def test_thread_safe_publish(self) -> None:
        """Multiple threads publishing must not lose events."""
        bus = get_bus()
        received: list = []
        lock = threading.Lock()

        def handler(data: dict) -> None:
            with lock:
                received.append(data)

        bus.subscribe(Events.TRANSACTION_WRITE, handler)

        threads = [
            threading.Thread(target=bus.publish, args=(Events.TRANSACTION_WRITE, {"i": i}))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(received) == 20
