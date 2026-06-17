"""Service layer for savings goals — Phase 3.3 + 3.4.

Validates inputs, computes progress, and exposes LRU-cached reads.

Layer rule: depends only on repositories and cache_service; no raw SQL.
"""
from __future__ import annotations

import threading
from datetime import date as _date
from typing import Any

from models.goal import Goal
from repositories.goal_repository import GoalRepository
from services.cache_service import CacheService

_CACHE_ALL = "goals:all"

# Preset color swatches for goal card backgrounds
GOAL_COLORS: list[str] = [
    "#E53935",  # Red
    "#8E24AA",  # Purple
    "#1E88E5",  # Blue
    "#43A047",  # Green
    "#FB8C00",  # Orange
    "#00ACC1",  # Cyan
    "#F06292",  # Pink
    "#5E35B1",  # Deep Purple
]
DEFAULT_GOAL_COLOR = "#1E88E5"
_MAX_NAME = 200
_MAX_CATEGORY = 100
_MAX_AMOUNT = 1_000_000_000  # 1 billion


class GoalService:
    """Business logic for savings goals. Singleton via :meth:`instance`."""

    _instance: GoalService | None = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> GoalService:
        """Return the application-wide singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._repo = GoalRepository()
        self._cache = CacheService.instance()

    # ── Validation helpers ────────────────────────────────────────────

    def _validate_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Name is required.")
        if len(name) > _MAX_NAME:
            raise ValueError(f"Name must be at most {_MAX_NAME} characters.")

    def _validate_amount(self, amount: float, label: str) -> None:
        if amount < 0:
            raise ValueError(f"{label} must be zero or positive.")
        if amount > _MAX_AMOUNT:
            raise ValueError(f"{label} must be at most {_MAX_AMOUNT:,.0f}.")

    def _validate_date(self, raw: str | None) -> None:
        if raw is None:
            return
        try:
            _date.fromisoformat(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Date must be in YYYY-MM-DD format. Got: {raw!r}"
            ) from exc

    # ── Reads ─────────────────────────────────────────────────────────

    def get_all_goals(self) -> list[Goal]:
        """Return all goals, ordered by deadline ascending (no deadline last).

        LRU-cached via :class:`~services.cache_service.CacheService`.
        """
        cached = self._cache.get_lru(_CACHE_ALL)
        if cached is not None:
            return cached  # type: ignore[return-value]
        goals = self._repo.get_all()
        goals.sort(
            key=lambda g: (g.deadline is None, g.deadline or "")
        )
        self._cache.set_lru(_CACHE_ALL, goals)
        return goals

    @staticmethod
    def progress_pct(goal: Goal) -> float:
        """Return 0–100 progress percentage (capped at 100)."""
        if not goal.target_amount or goal.target_amount <= 0:
            return 100.0
        pct = goal.current_amount / goal.target_amount * 100
        return round(min(pct, 100.0), 2)

    # ── Writes ────────────────────────────────────────────────────────

    def add_goal(
        self,
        name: str,
        category: str | None,
        target_amount: float,
        current_amount: float,
        deadline: str | None,
        color: str | None,
    ) -> Goal:
        """Validate and insert a new goal. Returns the inserted Goal."""
        self._validate_name(name)
        self._validate_amount(target_amount, "Target amount")
        self._validate_amount(current_amount, "Current amount")
        if current_amount > target_amount and target_amount > 0:
            raise ValueError("Current amount cannot exceed target amount.")
        self._validate_date(deadline)
        clean_color = (color or DEFAULT_GOAL_COLOR).strip()

        goal = Goal(
            name=name.strip(),
            category=(category or "").strip() or None,
            target_amount=round(target_amount, 2),
            current_amount=round(current_amount, 2),
            deadline=deadline,
            color=clean_color,
        )
        self._cache.invalidate(_CACHE_ALL)
        return self._repo.insert(goal)

    def update_goal(
        self,
        goal_id: int,
        name: str,
        category: str | None,
        target_amount: float,
        current_amount: float,
        deadline: str | None,
        color: str | None,
    ) -> Goal:
        """Validate and update an existing goal. Returns the updated Goal."""
        self._validate_name(name)
        self._validate_amount(target_amount, "Target amount")
        self._validate_amount(current_amount, "Current amount")
        self._validate_date(deadline)

        goal = self._repo.get_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: id={goal_id}")

        goal.name = name.strip()
        goal.category = (category or "").strip() or None
        goal.target_amount = round(target_amount, 2)
        goal.current_amount = round(current_amount, 2)
        goal.deadline = deadline
        goal.color = (color or DEFAULT_GOAL_COLOR).strip()

        self._cache.invalidate(_CACHE_ALL)
        return self._repo.update(goal)

    def add_funds(self, goal_id: int, amount: float) -> Goal:
        """Add *amount* to goal.current_amount (capped at target).

        Raises :class:`ValueError` if goal not found or amount invalid.
        """
        self._validate_amount(amount, "Amount")
        if amount == 0:
            raise ValueError("Amount must be greater than zero.")
        goal = self._repo.get_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: id={goal_id}")
        goal.current_amount = round(
            min(goal.current_amount + amount, goal.target_amount), 2
        )
        self._cache.invalidate(_CACHE_ALL)
        return self._repo.update(goal)

    def delete_goal(self, goal_id: int) -> None:
        """Delete a goal. Raises :class:`ValueError` if not found."""
        goal = self._repo.get_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: id={goal_id}")
        self._cache.invalidate(_CACHE_ALL)
        self._repo.delete(goal_id)
