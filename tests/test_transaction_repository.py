"""Tests for TransactionRepository — specifically the get_by_month query."""
from __future__ import annotations

import pytest

from repositories.transaction_repository import TransactionRepository


def _insert(repo: TransactionRepository, date: str, amount: float, tx_type: str) -> None:
    from models.transaction import Transaction
    repo.insert(Transaction(
        date=date,
        amount=amount,
        transaction_type=tx_type,
        category_id=None,
        description="test",
        person_id=None,
    ))


class TestGetByMonth:
    def test_returns_only_matching_month(self, fresh_db) -> None:
        repo = TransactionRepository()
        _insert(repo, "2026-06-01", 100.0, "expense")
        _insert(repo, "2026-05-15", 200.0, "expense")
        result = repo.get_by_month(2026, 6)
        assert len(result) == 1
        assert result[0].date == "2026-06-01"

    def test_returns_empty_for_month_with_no_data(self, fresh_db) -> None:
        repo = TransactionRepository()
        _insert(repo, "2026-06-10", 50.0, "income")
        assert repo.get_by_month(2025, 1) == []

    def test_returns_multiple_in_same_month(self, fresh_db) -> None:
        repo = TransactionRepository()
        _insert(repo, "2026-06-01", 10.0, "expense")
        _insert(repo, "2026-06-15", 20.0, "income")
        _insert(repo, "2026-06-30", 30.0, "expense")
        result = repo.get_by_month(2026, 6)
        assert len(result) == 3

    def test_results_ordered_newest_first(self, fresh_db) -> None:
        repo = TransactionRepository()
        _insert(repo, "2026-06-01", 10.0, "expense")
        _insert(repo, "2026-06-20", 20.0, "expense")
        _insert(repo, "2026-06-10", 30.0, "expense")
        result = repo.get_by_month(2026, 6)
        dates = [r.date for r in result]
        assert dates == sorted(dates, reverse=True)

    def test_does_not_bleed_into_adjacent_months(self, fresh_db) -> None:
        repo = TransactionRepository()
        _insert(repo, "2026-05-31", 1.0, "expense")   # May — must NOT appear
        _insert(repo, "2026-06-01", 2.0, "expense")   # June — must appear
        _insert(repo, "2026-07-01", 3.0, "expense")   # July — must NOT appear
        result = repo.get_by_month(2026, 6)
        assert len(result) == 1
        assert result[0].date == "2026-06-01"
