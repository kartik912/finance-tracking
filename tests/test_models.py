"""Tests for ORM model to_dict() and __repr__() methods."""
from __future__ import annotations

from models.category import Category
from models.split import Split
from models.transaction import Transaction


class TestCategoryModel:
    def test_to_dict_has_required_keys(self) -> None:
        c = Category(name="Food", icon="restaurant", color="#FF5722", is_default=True)
        d = c.to_dict()
        assert set(d.keys()) >= {"id", "name", "icon", "color", "is_default"}

    def test_to_dict_values_match(self) -> None:
        c = Category(name="Travel", icon="flight", color="#1E88E5", is_default=False)
        d = c.to_dict()
        assert d["name"] == "Travel"
        assert d["icon"] == "flight"
        assert d["color"] == "#1E88E5"
        assert d["is_default"] is False

    def test_repr_does_not_crash(self) -> None:
        c = Category(name="Food")
        assert "Food" in repr(c)


class TestTransactionModel:
    def test_to_dict_has_required_keys(self) -> None:
        t = Transaction(
            date="2026-06-01",
            amount=100.0,
            transaction_type="expense",
            category_id=None,
            description="Lunch",
            person_id=None,
        )
        d = t.to_dict()
        assert set(d.keys()) >= {"id", "date", "amount", "category_id", "description", "type", "person_id"}

    def test_transaction_type_not_shadowed_by_type_column(self) -> None:
        """transaction_type must not clash with SQLAlchemy polymorphic 'type'."""
        t = Transaction(transaction_type="expense", amount=50.0, date="2026-01-15")
        assert t.transaction_type == "expense"

    def test_repr_does_not_crash(self) -> None:
        t = Transaction(transaction_type="income", amount=200.0, date="2026-06-01")
        r = repr(t)
        assert "income" in r
        assert "200" in r


class TestSplitModel:
    def test_to_dict_has_required_keys(self) -> None:
        s = Split(
            description="Dinner",
            total_amount=900.0,
            date="2026-06-17",
            members_json='[{"name":"Alice","share":300}]',
            my_share=300.0,
        )
        d = s.to_dict()
        assert set(d.keys()) >= {"id", "description", "total_amount", "date", "members_json", "my_share"}

    def test_to_dict_values_match(self) -> None:
        s = Split(
            description="Pizza",
            total_amount=600.0,
            date="2026-06-10",
            members_json="[]",
            my_share=200.0,
        )
        d = s.to_dict()
        assert d["description"] == "Pizza"
        assert d["total_amount"] == 600.0
        assert d["my_share"] == 200.0

    def test_repr_does_not_crash(self) -> None:
        s = Split(description="Test", total_amount=100.0, date="2026-06-17", members_json="[]", my_share=50.0)
        r = repr(s)
        assert "100" in r
