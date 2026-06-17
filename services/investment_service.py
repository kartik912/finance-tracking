"""Service layer for investments — Phase 3.1 + 3.2.

Validates all inputs, computes P&L, and exposes LRU/TTL-cached reads.

Layer rule: depends only on repositories and cache_service; no raw SQL.
"""
from __future__ import annotations

import threading
from datetime import date as _date
from typing import Any

from models.investment import Investment
from repositories.investment_repository import InvestmentRepository
from services.cache_service import CacheService

# Investment type constants (used for filter chips)
INVESTMENT_TYPES: list[str] = [
    "Stocks",
    "Mutual Funds",
    "Crypto",
    "Gold",
    "Fixed Deposit",
    "Other",
]

_CACHE_ALL = "investments:all"
_CACHE_SUMMARY = "investments:summary"


class InvestmentService:
    """Business logic for investments. Singleton via :meth:`instance`."""

    _instance: InvestmentService | None = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> InvestmentService:
        """Return the application-wide singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._repo = InvestmentRepository()
        self._cache = CacheService.instance()

    # ── Validation helpers ────────────────────────────────────────────

    @staticmethod
    def _validate_amount(value: Any, field: str = "Amount") -> float:
        """Validate *value* is a positive finite number <= 10 M."""
        try:
            amt = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a number.")
        if amt < 0:
            raise ValueError(f"{field} must be zero or greater.")
        if amt > 10_000_000:
            raise ValueError(f"{field} exceeds the maximum allowed value.")
        return amt

    @staticmethod
    def _validate_text(value: str, field: str = "Name", max_len: int = 200) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError(f"{field} is required.")
        if len(value) > max_len:
            raise ValueError(f"{field} must be at most {max_len} characters.")
        return value

    @staticmethod
    def _validate_type(value: str) -> str:
        value = (value or "").strip()
        if value not in INVESTMENT_TYPES:
            raise ValueError(f"Type must be one of: {', '.join(INVESTMENT_TYPES)}.")
        return value

    @staticmethod
    def _validate_date(value: str) -> str:
        try:
            _date.fromisoformat(value)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return value

    # ── P&L calculation ───────────────────────────────────────────────

    @staticmethod
    def pnl(investment: Investment) -> float:
        """Return profit/loss = current_value - amount_invested."""
        return round(investment.current_value - investment.amount_invested, 2)

    @staticmethod
    def pnl_pct(investment: Investment) -> float:
        """Return P&L as a percentage of amount_invested (0 if invested == 0)."""
        if investment.amount_invested == 0:
            return 0.0
        return round(
            (investment.current_value - investment.amount_invested)
            / investment.amount_invested
            * 100,
            2,
        )

    # ── Public service methods ────────────────────────────────────────

    def get_all_investments(self, type_filter: str | None = None) -> list[Investment]:
        """Return all investments, optionally filtered by type (LRU cached)."""
        if type_filter:
            key = f"investments:type:{type_filter}"
            cached = self._cache.get_lru(key)
            if cached is not None:
                return cached
            result = self._repo.get_by_type(type_filter)
            self._cache.set_lru(key, result)
            return result

        cached = self._cache.get_lru(_CACHE_ALL)
        if cached is not None:
            return cached
        result = self._repo.get_all_ordered()
        self._cache.set_lru(_CACHE_ALL, result)
        return result

    def get_summary(self) -> dict[str, float]:
        """Return portfolio summary (TTL-cached 60 s).

        Keys: ``total_invested``, ``total_current``, ``pnl``, ``pnl_pct``.
        """
        cached = self._cache.get_ttl(_CACHE_SUMMARY)
        if cached is not None:
            return cached
        investments = self.get_all_investments()
        total_invested = sum(i.amount_invested for i in investments)
        total_current = sum(i.current_value for i in investments)
        pnl = round(total_current - total_invested, 2)
        pnl_pct = (
            round(pnl / total_invested * 100, 2) if total_invested > 0 else 0.0
        )
        result = {
            "total_invested": total_invested,
            "total_current": total_current,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        }
        self._cache.set_ttl(_CACHE_SUMMARY, result)
        return result

    def add_investment(
        self,
        name: str,
        investment_type: str,
        amount_invested: float | str,
        current_value: float | str,
        inv_date: str,
    ) -> Investment:
        """Validate and persist a new investment."""
        name = self._validate_text(name, "Name")
        investment_type = self._validate_type(investment_type)
        amount_invested = self._validate_amount(amount_invested, "Amount invested")
        current_value = self._validate_amount(current_value, "Current value")
        inv_date = self._validate_date(inv_date)

        inv = Investment(
            name=name,
            investment_type=investment_type,
            amount_invested=amount_invested,
            current_value=current_value,
            date=inv_date,
        )
        self._repo.insert(inv)
        return inv

    def update_investment(
        self,
        investment_id: int,
        name: str,
        investment_type: str,
        amount_invested: float | str,
        current_value: float | str,
        inv_date: str,
    ) -> Investment:
        """Validate and update an existing investment."""
        inv = self._repo.get_by_id(investment_id)
        if inv is None:
            raise ValueError(f"Investment {investment_id} not found.")
        inv.name = self._validate_text(name, "Name")
        inv.investment_type = self._validate_type(investment_type)
        inv.amount_invested = self._validate_amount(amount_invested, "Amount invested")
        inv.current_value = self._validate_amount(current_value, "Current value")
        inv.date = self._validate_date(inv_date)
        self._repo.update(inv)
        return inv

    def delete_investment(self, investment_id: int) -> None:
        """Delete the investment with *investment_id*."""
        inv = self._repo.get_by_id(investment_id)
        if inv is None:
            raise ValueError(f"Investment {investment_id} not found.")
        self._repo.delete(investment_id)
