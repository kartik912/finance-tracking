"""Tests for GoalService — Phase 3.3 + 3.4."""
from __future__ import annotations

import pytest


@pytest.fixture()
def svc(fresh_db):  # noqa: ANN001
    from services.goal_service import GoalService
    return GoalService.instance()


def _make(svc, **kwargs) -> object:  # noqa: ANN001
    defaults = dict(
        name="Test Goal",
        category="Savings",
        target_amount=10000.0,
        current_amount=1000.0,
        deadline="2026-12-31",
        color="#1E88E5",
    )
    defaults.update(kwargs)
    return svc.add_goal(**defaults)


# ── add_goal ──────────────────────────────────────────────────────────

class TestAddGoal:
    def test_add_returns_goal_with_correct_fields(self, svc) -> None:
        g = _make(svc, name="Holiday Fund", target_amount=50000.0, current_amount=5000.0)
        assert g.id is not None
        assert g.name == "Holiday Fund"
        assert g.target_amount == 50000.0
        assert g.current_amount == 5000.0
        assert g.color == "#1E88E5"

    def test_add_persists_to_db(self, svc) -> None:
        _make(svc, name="Car Fund")
        assert any(g.name == "Car Fund" for g in svc.get_all_goals())

    def test_add_rejects_empty_name(self, svc) -> None:
        with pytest.raises(ValueError, match="Name"):
            _make(svc, name="")

    def test_add_rejects_name_too_long(self, svc) -> None:
        with pytest.raises(ValueError, match="Name"):
            _make(svc, name="x" * 201)

    def test_add_rejects_negative_target(self, svc) -> None:
        with pytest.raises(ValueError, match="Target"):
            _make(svc, target_amount=-1000.0)

    def test_add_rejects_negative_current(self, svc) -> None:
        with pytest.raises(ValueError, match="Current"):
            _make(svc, current_amount=-100.0)

    def test_add_rejects_current_exceeds_target(self, svc) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            _make(svc, target_amount=1000.0, current_amount=2000.0)

    def test_add_rejects_bad_deadline(self, svc) -> None:
        with pytest.raises(ValueError, match="[Dd]ate"):
            _make(svc, deadline="not-a-date")

    def test_add_allows_no_deadline(self, svc) -> None:
        g = _make(svc, deadline=None)
        assert g.deadline is None

    def test_add_allows_zero_amounts(self, svc) -> None:
        g = _make(svc, target_amount=0.0, current_amount=0.0)
        assert g.target_amount == 0.0

    def test_default_color_applied_when_none(self, svc) -> None:
        from services.goal_service import DEFAULT_GOAL_COLOR
        g = _make(svc, color=None)
        assert g.color == DEFAULT_GOAL_COLOR


# ── progress_pct ──────────────────────────────────────────────────────

class TestProgressPct:
    def test_25_percent(self, svc) -> None:
        g = _make(svc, target_amount=10000.0, current_amount=2500.0)
        from services.goal_service import GoalService
        assert GoalService.progress_pct(g) == pytest.approx(25.0)

    def test_capped_at_100(self, svc) -> None:
        g = _make(svc, target_amount=100.0, current_amount=100.0)
        from services.goal_service import GoalService
        assert GoalService.progress_pct(g) == pytest.approx(100.0)

    def test_zero_target_returns_100(self, svc) -> None:
        g = _make(svc, target_amount=0.0, current_amount=0.0)
        from services.goal_service import GoalService
        assert GoalService.progress_pct(g) == pytest.approx(100.0)


# ── get_all_goals ─────────────────────────────────────────────────────

class TestGetAllGoals:
    def test_empty_on_fresh_db(self, svc) -> None:
        assert svc.get_all_goals() == []

    def test_sorted_by_deadline(self, svc) -> None:
        _make(svc, name="Later", deadline="2027-01-01")
        _make(svc, name="Sooner", deadline="2026-06-01")
        goals = svc.get_all_goals()
        assert goals[0].name == "Sooner"

    def test_no_deadline_sorted_last(self, svc) -> None:
        _make(svc, name="Has Deadline", deadline="2026-06-01")
        _make(svc, name="No Deadline", deadline=None)
        goals = svc.get_all_goals()
        assert goals[-1].name == "No Deadline"


# ── add_funds ─────────────────────────────────────────────────────────

class TestAddFunds:
    def test_adds_to_current_amount(self, svc) -> None:
        g = _make(svc, target_amount=10000.0, current_amount=1000.0)
        svc.add_funds(g.id, 2000.0)
        updated = [x for x in svc.get_all_goals() if x.id == g.id][0]
        assert updated.current_amount == pytest.approx(3000.0)

    def test_caps_at_target(self, svc) -> None:
        g = _make(svc, target_amount=10000.0, current_amount=9500.0)
        svc.add_funds(g.id, 1000.0)  # would exceed target
        updated = [x for x in svc.get_all_goals() if x.id == g.id][0]
        assert updated.current_amount == pytest.approx(10000.0)

    def test_rejects_zero_amount(self, svc) -> None:
        g = _make(svc)
        with pytest.raises(ValueError):
            svc.add_funds(g.id, 0.0)

    def test_rejects_negative_amount(self, svc) -> None:
        g = _make(svc)
        with pytest.raises(ValueError):
            svc.add_funds(g.id, -500.0)

    def test_rejects_nonexistent_goal(self, svc) -> None:
        with pytest.raises(ValueError, match="[Nn]ot found"):
            svc.add_funds(9999, 1000.0)


# ── update_goal ───────────────────────────────────────────────────────

class TestUpdateGoal:
    def test_update_fields(self, svc) -> None:
        g = _make(svc, name="Old", target_amount=5000.0)
        svc.update_goal(
            goal_id=g.id,
            name="New",
            category="Travel",
            target_amount=8000.0,
            current_amount=1000.0,
            deadline="2027-03-01",
            color="#E53935",
        )
        updated = [x for x in svc.get_all_goals() if x.id == g.id][0]
        assert updated.name == "New"
        assert updated.target_amount == 8000.0
        assert updated.color == "#E53935"

    def test_update_nonexistent_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Nn]ot found"):
            svc.update_goal(
                goal_id=9999, name="X", category=None,
                target_amount=100.0, current_amount=0.0,
                deadline=None, color=None,
            )


# ── delete_goal ───────────────────────────────────────────────────────

class TestDeleteGoal:
    def test_delete_removes_from_db(self, svc) -> None:
        g = _make(svc)
        svc.delete_goal(g.id)
        assert not any(x.id == g.id for x in svc.get_all_goals())

    def test_delete_nonexistent_raises(self, svc) -> None:
        with pytest.raises(ValueError, match="[Nn]ot found"):
            svc.delete_goal(9999)
