"""Tests for FinanceService — validation, CRUD, and monthly aggregates."""
from __future__ import annotations

import pytest

from services.finance_service import FinanceService


# ── Validation ─────────────────────────────────────────────────────────

class TestAddTransactionValidation:
    def test_negative_amount_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError, match="greater than zero"):
            svc.add_transaction("2026-06-01", -50.0, None, "Bad", "expense")

    def test_zero_amount_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError, match="greater than zero"):
            svc.add_transaction("2026-06-01", 0.0, None, "Zero", "expense")

    def test_non_numeric_amount_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError, match="number"):
            svc.add_transaction("2026-06-01", "abc", None, "Bad", "expense")  # type: ignore[arg-type]

    def test_amount_over_limit_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError):
            svc.add_transaction("2026-06-01", 10_000_001.0, None, "Big", "expense")

    def test_description_too_long_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError, match="500"):
            svc.add_transaction("2026-06-01", 10.0, None, "x" * 501, "expense")

    def test_invalid_type_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError, match="income.*expense"):
            svc.add_transaction("2026-06-01", 10.0, None, "Bad", "transfer")

    def test_invalid_date_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError):
            svc.add_transaction("not-a-date", 10.0, None, "Bad", "expense")


# ── Happy path CRUD ────────────────────────────────────────────────────

class TestAddTransaction:
    def test_returns_transaction_with_id(self, fresh_db) -> None:
        svc = FinanceService.instance()
        tx = svc.add_transaction("2026-06-10", 250.0, None, "Groceries", "expense")
        assert tx.id is not None
        assert tx.amount == 250.0
        assert tx.transaction_type == "expense"

    def test_appears_in_monthly_list(self, fresh_db) -> None:
        svc = FinanceService.instance()
        tx = svc.add_transaction("2026-06-10", 100.0, None, "Lunch", "expense")
        txs = svc.get_transactions_for_month(2026, 6)
        assert any(t.id == tx.id for t in txs)

    def test_income_type_accepted(self, fresh_db) -> None:
        svc = FinanceService.instance()
        tx = svc.add_transaction("2026-06-05", 5000.0, None, "Salary", "income")
        assert tx.transaction_type == "income"


class TestDeleteTransaction:
    def test_delete_removes_from_month(self, fresh_db) -> None:
        svc = FinanceService.instance()
        tx = svc.add_transaction("2026-06-05", 75.0, None, "Test", "expense")
        result = svc.delete_transaction(tx.id)
        assert result is True
        assert svc.get_transactions_for_month(2026, 6) == []

    def test_delete_invalid_id_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError):
            svc.delete_transaction(-1)

    def test_delete_nonexistent_id_returns_false(self, fresh_db) -> None:
        svc = FinanceService.instance()
        result = svc.delete_transaction(99999)
        assert result is False


class TestUpdateTransaction:
    def test_update_changes_amount(self, fresh_db) -> None:
        svc = FinanceService.instance()
        tx = svc.add_transaction("2026-06-01", 100.0, None, "Original", "expense")
        updated = svc.update_transaction(tx.id, "2026-06-01", 200.0, None, "Updated", "expense")
        assert updated.amount == 200.0
        assert updated.description == "Updated"

    def test_update_nonexistent_raises(self, fresh_db) -> None:
        svc = FinanceService.instance()
        with pytest.raises(ValueError, match="not found"):
            svc.update_transaction(99999, "2026-06-01", 10.0, None, "X", "expense")


# ── Aggregates ─────────────────────────────────────────────────────────

class TestGetMonthlyTotal:
    def test_expense_total_correct(self, fresh_db) -> None:
        svc = FinanceService.instance()
        svc.add_transaction("2026-06-01", 100.0, None, "A", "expense")
        svc.add_transaction("2026-06-02", 200.0, None, "B", "expense")
        svc.add_transaction("2026-06-03", 50.0, None, "C", "income")
        total = svc.get_monthly_total(2026, 6, "expense")
        assert total == 300.0

    def test_income_total_correct(self, fresh_db) -> None:
        svc = FinanceService.instance()
        svc.add_transaction("2026-06-01", 1000.0, None, "Salary", "income")
        svc.add_transaction("2026-06-15", 500.0, None, "Freelance", "income")
        total = svc.get_monthly_total(2026, 6, "income")
        assert total == 1500.0

    def test_empty_month_returns_zero(self, fresh_db) -> None:
        svc = FinanceService.instance()
        total = svc.get_monthly_total(2025, 1, "expense")
        assert total == 0.0

    def test_different_months_isolated(self, fresh_db) -> None:
        svc = FinanceService.instance()
        svc.add_transaction("2026-05-01", 999.0, None, "May", "expense")
        svc.add_transaction("2026-06-01", 123.0, None, "June", "expense")
        assert svc.get_monthly_total(2026, 6, "expense") == 123.0
        assert svc.get_monthly_total(2026, 5, "expense") == 999.0
