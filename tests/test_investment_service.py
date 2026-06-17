"""Tests for InvestmentService — Phase 3.1 + 3.2."""
from __future__ import annotations

import pytest


@pytest.fixture()
def svc(fresh_db):  # noqa: ANN001
    from services.investment_service import InvestmentService
    return InvestmentService.instance()


# ── add_investment ────────────────────────────────────────────────────

class TestAddInvestment:
    def test_add_returns_investment_with_correct_fields(self, svc) -> None:
        inv = svc.add_investment("My Stocks", "Stocks", 5000.0, 6000.0, "2026-01-01")
        assert inv.id is not None
        assert inv.name == "My Stocks"
        assert inv.investment_type == "Stocks"
        assert inv.amount_invested == 5000.0
        assert inv.current_value == 6000.0
        assert inv.date == "2026-01-01"

    def test_add_persists_to_db(self, svc) -> None:
        svc.add_investment("Gold Bar", "Gold", 10000.0, 11000.0, "2026-02-15")
        all_inv = svc.get_all_investments()
        assert any(i.name == "Gold Bar" for i in all_inv)

    def test_add_rejects_empty_name(self, svc) -> None:
        with pytest.raises(ValueError, match="Name"):
            svc.add_investment("", "Stocks", 1000.0, 1100.0, "2026-01-01")

    def test_add_rejects_name_too_long(self, svc) -> None:
        with pytest.raises(ValueError, match="Name"):
            svc.add_investment("x" * 201, "Stocks", 1000.0, 1100.0, "2026-01-01")

    def test_add_rejects_invalid_type(self, svc) -> None:
        with pytest.raises(ValueError, match="[Tt]ype"):
            svc.add_investment("Foo", "InvalidType", 1000.0, 1100.0, "2026-01-01")

    def test_add_rejects_negative_amount_invested(self, svc) -> None:
        with pytest.raises(ValueError, match="Amount invested"):
            svc.add_investment("Foo", "Stocks", -100.0, 100.0, "2026-01-01")

    def test_add_rejects_negative_current_value(self, svc) -> None:
        with pytest.raises(ValueError, match="Current value"):
            svc.add_investment("Foo", "Stocks", 100.0, -50.0, "2026-01-01")

    def test_add_rejects_bad_date(self, svc) -> None:
        with pytest.raises(ValueError, match="[Dd]ate"):
            svc.add_investment("Foo", "Stocks", 100.0, 110.0, "not-a-date")

    def test_add_allows_zero_amounts(self, svc) -> None:
        inv = svc.add_investment("Empty FD", "Fixed Deposit", 0.0, 0.0, "2026-01-01")
        assert inv.amount_invested == 0.0
        assert inv.current_value == 0.0


# ── pnl + pnl_pct ─────────────────────────────────────────────────────

class TestPnl:
    def test_pnl_gain(self, svc) -> None:
        inv = svc.add_investment("Up", "Stocks", 1000.0, 1500.0, "2026-01-01")
        assert svc.pnl(inv) == pytest.approx(500.0)
        assert svc.pnl_pct(inv) == pytest.approx(50.0)

    def test_pnl_loss(self, svc) -> None:
        inv = svc.add_investment("Down", "Crypto", 2000.0, 1800.0, "2026-01-01")
        assert svc.pnl(inv) == pytest.approx(-200.0)
        assert svc.pnl_pct(inv) == pytest.approx(-10.0)

    def test_pnl_zero_invested_returns_zero_pct(self, svc) -> None:
        inv = svc.add_investment("Zero", "Other", 0.0, 0.0, "2026-01-01")
        assert svc.pnl_pct(inv) == pytest.approx(0.0)


# ── get_all_investments ───────────────────────────────────────────────

class TestGetAllInvestments:
    def test_returns_empty_on_fresh_db(self, svc) -> None:
        assert svc.get_all_investments() == []

    def test_filter_by_type(self, svc) -> None:
        svc.add_investment("A", "Stocks", 100.0, 110.0, "2026-01-01")
        svc.add_investment("B", "Gold", 200.0, 210.0, "2026-01-02")
        svc.add_investment("C", "Stocks", 300.0, 320.0, "2026-01-03")
        stocks = svc.get_all_investments("Stocks")
        assert len(stocks) == 2
        assert all(i.investment_type == "Stocks" for i in stocks)

    def test_filter_none_returns_all(self, svc) -> None:
        svc.add_investment("A", "Stocks", 100.0, 110.0, "2026-01-01")
        svc.add_investment("B", "Gold", 200.0, 210.0, "2026-01-02")
        assert len(svc.get_all_investments()) == 2


# ── get_summary ───────────────────────────────────────────────────────

class TestGetSummary:
    def test_summary_empty(self, svc) -> None:
        s = svc.get_summary()
        assert s["total_invested"] == pytest.approx(0.0)
        assert s["total_current"] == pytest.approx(0.0)
        assert s["pnl"] == pytest.approx(0.0)
        assert s["pnl_pct"] == pytest.approx(0.0)

    def test_summary_with_investments(self, svc) -> None:
        svc.add_investment("A", "Stocks", 1000.0, 1200.0, "2026-01-01")
        svc.add_investment("B", "Gold",  500.0, 450.0, "2026-01-02")
        s = svc.get_summary()
        assert s["total_invested"] == pytest.approx(1500.0)
        assert s["total_current"] == pytest.approx(1650.0)
        assert s["pnl"] == pytest.approx(150.0)
        assert s["pnl_pct"] == pytest.approx(10.0)


# ── update_investment ─────────────────────────────────────────────────

class TestUpdateInvestment:
    def test_update_name_and_value(self, svc) -> None:
        inv = svc.add_investment("Old Name", "Stocks", 1000.0, 1100.0, "2026-01-01")
        svc.update_investment(
            investment_id=inv.id,
            name="New Name",
            investment_type="Mutual Funds",
            amount_invested=1000.0,
            current_value=1200.0,
            inv_date="2026-03-01",
        )
        updated = [i for i in svc.get_all_investments() if i.id == inv.id][0]
        assert updated.name == "New Name"
        assert updated.investment_type == "Mutual Funds"
        assert updated.current_value == 1200.0

    def test_update_nonexistent_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Nn]ot found|not found"):
            svc.update_investment(
                investment_id=9999,
                name="X",
                investment_type="Stocks",
                amount_invested=100.0,
                current_value=110.0,
                inv_date="2026-01-01",
            )


# ── delete_investment ─────────────────────────────────────────────────

class TestDeleteInvestment:
    def test_delete_removes_from_db(self, svc) -> None:
        inv = svc.add_investment("To Delete", "Crypto", 500.0, 400.0, "2026-01-01")
        svc.delete_investment(inv.id)
        assert not any(i.id == inv.id for i in svc.get_all_investments())

    def test_delete_nonexistent_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Nn]ot found|not found"):
            svc.delete_investment(9999)
