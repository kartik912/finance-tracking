"""Service layer for bill splits — Phase 2.6.

Validates all inputs before writing to the repository and exposes
LRU-cached reads so the UI never hits the DB directly.

Layer rule: depends only on repositories and cache_service; no raw SQL.
"""
from __future__ import annotations

import json
import threading
from datetime import date as _date
from typing import Any

from models.split import Split
from repositories.split_repository import SplitRepository
from services.cache_service import CacheService

_CACHE_KEY = "splits:all"


class SplitService:
    """Business logic for bill splits. Singleton via :meth:`instance`."""

    _instance: SplitService | None = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> SplitService:
        """Return the application-wide singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._repo = SplitRepository()
        self._cache = CacheService.instance()

    # ── Validation helpers ────────────────────────────────────────────

    @staticmethod
    def _validate_amount(value: Any, field: str = "Amount") -> float:
        """Validate *value* is a positive finite number <= 10 M."""
        try:
            amt = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a number.")
        if amt <= 0:
            raise ValueError(f"{field} must be greater than zero.")
        if amt > 10_000_000:
            raise ValueError(f"{field} exceeds the maximum allowed value.")
        return amt

    @staticmethod
    def _validate_text(value: str, field: str = "Description", max_len: int = 500) -> str:
        """Validate *value* is non-empty and within *max_len* characters."""
        value = (value or "").strip()
        if not value:
            raise ValueError(f"{field} is required.")
        if len(value) > max_len:
            raise ValueError(f"{field} must be at most {max_len} characters.")
        return value

    @staticmethod
    def _validate_date(value: str) -> str:
        """Validate *value* is a valid ISO-8601 date string."""
        try:
            _date.fromisoformat(value)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return value

    # ── Public service methods ────────────────────────────────────────

    def add_split(
        self,
        description: str,
        total_amount: float | str,
        split_date: str,
        members: list[dict[str, Any]],
        my_share: float | str,
    ) -> Split:
        """Validate inputs and persist a new bill split.

        *members* is a list of ``{"name": str, "share": float}`` dicts
        representing the other participants (not including the current user).
        """
        description = self._validate_text(description, "Description")
        total_amount = self._validate_amount(total_amount, "Total amount")
        split_date = self._validate_date(split_date)
        my_share = self._validate_amount(my_share, "My share")

        if not members:
            raise ValueError("Add at least one other member to the split.")

        validated: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        for m in members:
            name = self._validate_text(str(m.get("name", "")), "Member name", max_len=200)
            name_lower = name.lower()
            if name_lower in seen_names:
                raise ValueError(f"Duplicate member name: '{name}'. Each member must be unique.")
            seen_names.add(name_lower)
            share = self._validate_amount(m.get("share", 0), f"Share for {name}")
            validated.append({"name": name, "share": share})

        # My share must not exceed total
        if my_share > total_amount:
            raise ValueError("My share cannot be greater than the total amount.")

        # Sum of all shares (members + me) must equal total (within 1 rupee tolerance)
        member_sum = sum(v["share"] for v in validated)
        grand_total = round(member_sum + my_share, 2)
        tolerance = 1.0
        if abs(grand_total - total_amount) > tolerance:
            diff = total_amount - grand_total
            if diff > 0:
                raise ValueError(
                    f"Shares don't add up. Total is \u20b9{total_amount:,.2f} but all shares"
                    f" sum to \u20b9{grand_total:,.2f} — \u20b9{diff:,.2f} unaccounted."
                )
            else:
                raise ValueError(
                    f"Shares exceed the total. All shares sum to \u20b9{grand_total:,.2f}"
                    f" but total is only \u20b9{total_amount:,.2f}."
                )

        split = Split(
            description=description,
            total_amount=total_amount,
            date=split_date,
            members_json=json.dumps(validated),
            my_share=my_share,
        )
        self._repo.insert(split)
        return split

    def get_all_splits(self) -> list[Split]:
        """Return all splits ordered by date DESC (LRU cached)."""
        cached = self._cache.get_lru(_CACHE_KEY)
        if cached is not None:
            return cached
        result = self._repo.get_recent(limit=100)
        self._cache.set_lru(_CACHE_KEY, result)
        return result

    def delete_split(self, split_id: int) -> None:
        """Delete the split with the given *split_id*."""
        split = self._repo.get_by_id(split_id)
        if split is None:
            raise ValueError(f"Split {split_id} not found.")
        self._repo.delete(split_id)

    @staticmethod
    def parse_members(split: Split) -> list[dict[str, Any]]:
        """Deserialise *members_json* into a list of ``{"name", "share"}`` dicts."""
        try:
            return json.loads(split.members_json)
        except (json.JSONDecodeError, TypeError):
            return []
