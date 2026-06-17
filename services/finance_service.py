"""Business-logic service for the Finance Tracker module.

All methods validate their inputs, never write raw SQL, and depend only on
repositories and the cache. The service is a singleton accessed via
:meth:`FinanceService.instance`.

Caching strategy
----------------
* Frequent list reads → LRU cache (key ``transactions:month:{Y}:{M}``).
* Aggregate values (totals, breakdowns) → TTL cache (60 s).
* Auto-invalidation on every write is handled by EventBus → CacheService.
"""
from __future__ import annotations

import threading
from datetime import date

from models.category import Category
from models.transaction import Transaction
from repositories.category_repository import CategoryRepository
from repositories.transaction_repository import TransactionRepository
from services.cache_service import CacheService


class FinanceService:
    """Finance domain business logic — no raw SQL, depends on repositories only.

    Use :meth:`instance` to obtain the application-wide singleton.
    """

    _instance: FinanceService | None = None
    _class_lock = threading.Lock()

    def __init__(self) -> None:
        self._tx_repo = TransactionRepository()
        self._cat_repo = CategoryRepository()
        self._cache = CacheService.instance()

    @classmethod
    def instance(cls) -> FinanceService:
        """Return the application-wide singleton :class:`FinanceService`."""
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Category reads
    # ------------------------------------------------------------------

    def get_all_categories(self) -> list[Category]:
        """Return all categories ordered by id. LRU-cached."""
        key = "categories:all"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        result = self._cat_repo.get_all()
        self._cache.set_lru(key, result)
        return result

    # ------------------------------------------------------------------
    # Transaction reads
    # ------------------------------------------------------------------

    def get_transactions_for_month(self, year: int, month: int) -> list[Transaction]:
        """Return all transactions for *year*/*month*, newest first. LRU-cached."""
        key = f"transactions:month:{year}:{month}"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        result = self._tx_repo.get_by_month(year, month)
        self._cache.set_lru(key, result)
        return result

    def get_recent_transactions(self, limit: int = 5) -> list[Transaction]:
        """Return the most recent *limit* transactions across all months. LRU-cached."""
        key = f"transactions:recent:{limit}"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        all_txs = self._tx_repo.get_all()
        result = sorted(all_txs, key=lambda t: (t.date, t.id), reverse=True)[:limit]
        self._cache.set_lru(key, result)
        return result

    def get_monthly_total(self, year: int, month: int, tx_type: str) -> float:
        """Return the sum of *tx_type* transactions for *year*/*month*. TTL-cached 60 s."""
        key = f"transactions:total:{year}:{month}:{tx_type}"
        cached = self._cache.get_ttl(key)
        if cached is not None:
            return cached
        txs = self.get_transactions_for_month(year, month)
        total = sum(t.amount for t in txs if t.transaction_type == tx_type)
        self._cache.set_ttl(key, total)
        return total

    def get_category_breakdown(
        self, year: int, month: int
    ) -> list[tuple[Category, float]]:
        """Return (category, total_amount) pairs for expense transactions, TTL-cached.

        Results are sorted by total descending.
        """
        key = f"transactions:breakdown:{year}:{month}"
        cached = self._cache.get_ttl(key)
        if cached is not None:
            return cached

        txs = self.get_transactions_for_month(year, month)
        cats = {c.id: c for c in self.get_all_categories()}
        totals: dict[int | None, float] = {}
        for tx in txs:
            if tx.transaction_type == "expense":
                totals[tx.category_id] = totals.get(tx.category_id, 0.0) + tx.amount

        result = [
            (cats[cid], amt)
            for cid, amt in sorted(totals.items(), key=lambda x: x[1], reverse=True)
            if cid in cats
        ]
        self._cache.set_ttl(key, result)
        return result

    # ------------------------------------------------------------------
    # Transaction writes (with input validation)
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        tx_date: str,
        amount: float,
        category_id: int | None,
        description: str,
        transaction_type: str,
        person_id: int | None = None,
    ) -> Transaction:
        """Validate inputs and insert a new :class:`~models.transaction.Transaction`."""
        self._validate_amount(amount)
        self._validate_text(description, "description")
        self._validate_date(tx_date)
        if transaction_type not in ("income", "expense"):
            raise ValueError("transaction_type must be 'income' or 'expense'")
        tx = Transaction(
            date=tx_date,
            amount=float(amount),
            category_id=category_id,
            description=description[:500] if description else None,
            transaction_type=transaction_type,
            person_id=person_id,
        )
        return self._tx_repo.insert(tx)

    def update_transaction(
        self,
        transaction_id: int,
        tx_date: str,
        amount: float,
        category_id: int | None,
        description: str,
        transaction_type: str,
        person_id: int | None = None,
    ) -> Transaction:
        """Validate inputs and update an existing transaction."""
        self._validate_amount(amount)
        self._validate_text(description, "description")
        self._validate_date(tx_date)
        if transaction_type not in ("income", "expense"):
            raise ValueError("transaction_type must be 'income' or 'expense'")
        tx = self._tx_repo.get_by_id(transaction_id)
        if tx is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        tx.date = tx_date
        tx.amount = float(amount)
        tx.category_id = category_id
        tx.description = description[:500] if description else None
        tx.transaction_type = transaction_type
        tx.person_id = person_id
        return self._tx_repo.update(tx)

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction by primary key. Returns ``True`` if a row was deleted."""
        if not isinstance(transaction_id, int) or transaction_id <= 0:
            raise ValueError(f"Invalid transaction ID: {transaction_id!r}")
        return self._tx_repo.delete(transaction_id)

    # ------------------------------------------------------------------
    # Input validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Raise ValueError if *amount* is not a positive number within bounds."""
        try:
            val = float(amount)
        except (TypeError, ValueError):
            raise ValueError("Amount must be a number")
        if val <= 0:
            raise ValueError("Amount must be greater than zero")
        if val > 10_000_000:
            raise ValueError("Amount exceeds maximum allowed value (10,000,000)")

    @staticmethod
    def _validate_text(value: str, field_name: str) -> None:
        """Raise ValueError if *value* exceeds the 500-character limit."""
        if value and len(str(value)) > 500:
            raise ValueError(f"{field_name} must be 500 characters or fewer")

    @staticmethod
    def _validate_date(value: str) -> None:
        """Raise ValueError if *value* is not a valid ISO-format date string."""
        try:
            date.fromisoformat(str(value))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid date: {value!r}. Expected YYYY-MM-DD")
