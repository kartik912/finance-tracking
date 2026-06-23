"""Screen construction smoke tests.

Every screen's ``build()`` function is called against a minimal page stub.
If a screen crashes during construction (wrong Flet API, missing attribute,
etc.) it is caught here — before the user ever sees it.

This covers the most common class of bug in this project: code that compiles
fine and passes all service-layer unit tests but raises the moment Flet tries
to render the view.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any


# ---------------------------------------------------------------------------
# Minimal page stub
# ---------------------------------------------------------------------------

class _FakeRoute:
    """Simulates page.push_route — returns a coroutine that does nothing."""
    async def __call__(self, route: str) -> None:
        pass


class _FakePage:
    """Minimal stand-in for ``ft.Page`` used during build() calls."""

    def __init__(self) -> None:
        self.overlay: list[Any] = []
        self.views: list[Any] = []
        self.route = "/"
        self.push_route = _FakeRoute()

    def update(self) -> None:
        pass

    def run_task(self, coro_or_fn: Any, *args: Any, **kwargs: Any) -> None:
        pass

    def open(self, dlg: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import pytest


@pytest.fixture()
def page(fresh_db) -> _FakePage:  # noqa: F811
    return _FakePage()


# ---------------------------------------------------------------------------
# notebooks.py
# ---------------------------------------------------------------------------

class TestNotebooksScreen:
    def test_build_empty_db(self, page: _FakePage) -> None:
        """build() must not raise on an empty database."""
        import screens.notebooks as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None

    def test_build_with_notebooks(self, page: _FakePage) -> None:
        """build() must not raise when notebooks exist."""
        from services.notebook_service import NotebookService
        svc = NotebookService.instance()
        svc.add_notebook("Work", "#1E88E5", "\U0001f4d3")
        svc.add_notebook("Personal", "#43A047", "\U0001f4d5")
        import screens.notebooks as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None

    def test_build_returns_view(self, page: _FakePage) -> None:
        import screens.notebooks as m
        view = m.build(page)  # type: ignore[arg-type]
        assert hasattr(view, "route")
        assert view.route == "/notes"

    def test_appbar_has_delete_action(self, page: _FakePage) -> None:
        """AppBar must expose the delete-notebooks icon button."""
        import flet as ft
        import screens.notebooks as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view.appbar is not None
        assert view.appbar.actions  # type: ignore[union-attr]
        icons = [
            a.icon
            for a in view.appbar.actions  # type: ignore[union-attr]
            if isinstance(a, ft.IconButton)
        ]
        assert ft.Icons.DELETE_OUTLINE in icons

    def test_delete_dialog_builds_without_crash(self, page: _FakePage) -> None:
        """_show_delete_selection() must not crash when notebooks exist."""
        from services.notebook_service import NotebookService
        svc = NotebookService.instance()
        svc.add_notebook("ToDelete", "#E53935", "\U0001f4d3")
        import flet as ft
        import screens.notebooks as m
        view = m.build(page)  # type: ignore[arg-type]
        # Find the delete IconButton and fire its on_click handler directly
        delete_btn = next(
            a for a in view.appbar.actions  # type: ignore[union-attr]
            if isinstance(a, ft.IconButton) and a.icon == ft.Icons.DELETE_OUTLINE
        )
        # Call on_click with None — handler ignores the event arg
        delete_btn.on_click(None)  # type: ignore[arg-type]
        # The dialog should have been appended to the overlay
        assert len(page.overlay) == 1

    def test_delete_selection_removes_notebook(self, page: _FakePage) -> None:
        """Deleting a selected notebook via the service removes it."""
        from services.notebook_service import NotebookService
        svc = NotebookService.instance()
        nb = svc.add_notebook("Bye", "#E53935", "\U0001f4d3")
        assert len(svc.get_all()) == 1
        svc.delete_notebook(nb.id)
        assert svc.get_all() == []

    def test_delete_nothing_selected_leaves_notebooks(self, page: _FakePage) -> None:
        """If no checkboxes are ticked, no notebooks are deleted."""
        from services.notebook_service import NotebookService
        svc = NotebookService.instance()
        svc.add_notebook("Keep1", "#1E88E5", "\U0001f4d3")
        svc.add_notebook("Keep2", "#43A047", "\U0001f4d5")
        # Simulate: delete with empty selected_ids list
        selected_ids: list[int] = []
        for nb_id in list(selected_ids):
            svc.delete_notebook(nb_id)
        assert len(svc.get_all()) == 2


# ---------------------------------------------------------------------------
# notes_list.py
# ---------------------------------------------------------------------------

class TestNotesListScreen:
    def test_build_with_valid_notebook(self, page: _FakePage) -> None:
        from services.notebook_service import NotebookService
        nb = NotebookService.instance().add_notebook("Test", "#1E88E5", "\U0001f4d3")
        import screens.notes_list as m
        view = m.build(page, nb.id)  # type: ignore[arg-type]
        assert view is not None

    def test_build_with_nonexistent_notebook(self, page: _FakePage) -> None:
        """build() must not crash if notebook_id doesn't exist."""
        import screens.notes_list as m
        view = m.build(page, 9999)  # type: ignore[arg-type]
        assert view is not None

    def test_build_with_notes(self, page: _FakePage) -> None:
        from services.notebook_service import NotebookService
        from services.note_service import NoteService
        nb = NotebookService.instance().add_notebook("Test", "#1E88E5", "\U0001f4d3")
        NoteService.instance().create_note(nb.id, "unified", "Hello")
        NoteService.instance().create_note(nb.id, "unified", "World")
        import screens.notes_list as m
        view = m.build(page, nb.id)  # type: ignore[arg-type]
        assert view is not None

    def test_build_route_contains_notebook_id(self, page: _FakePage) -> None:
        from services.notebook_service import NotebookService
        nb = NotebookService.instance().add_notebook("R", "#1E88E5", "\U0001f4d3")
        import screens.notes_list as m
        view = m.build(page, nb.id)  # type: ignore[arg-type]
        assert str(nb.id) in view.route


# ---------------------------------------------------------------------------
# note_editor.py
# ---------------------------------------------------------------------------

class TestNoteEditorScreen:
    def _make_note(self, nb_id: int, title: str = "Test note") -> Any:
        from services.note_service import NoteService
        return NoteService.instance().create_note(nb_id, "unified", title)

    def _make_notebook(self) -> Any:
        from services.notebook_service import NotebookService
        return NotebookService.instance().add_notebook("NB", "#1E88E5", "\U0001f4d3")

    def test_build_text_note(self, page: _FakePage) -> None:
        nb = self._make_notebook()
        note = self._make_note(nb.id, "My Note")
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]
        assert view is not None

    def test_build_note_with_content(self, page: _FakePage) -> None:
        from services.note_service import NoteService
        nb = self._make_notebook()
        note = self._make_note(nb.id)
        NoteService.instance().update_note_text(note.id, "Title", "Some content here")
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]
        assert view is not None

    def test_build_nonexistent_note(self, page: _FakePage) -> None:
        """build() must return a fallback view for a deleted note."""
        nb = self._make_notebook()
        import screens.note_editor as m
        view = m.build(page, nb.id, 99999)  # type: ignore[arg-type]
        assert view is not None

    def test_build_returns_correct_route(self, page: _FakePage) -> None:
        nb = self._make_notebook()
        note = self._make_note(nb.id)
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]
        assert str(note.id) in view.route

    def test_build_empty_title_shows_untitled(self, page: _FakePage) -> None:
        nb = self._make_notebook()
        note = self._make_note(nb.id, "")
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]
        assert view is not None

    def test_build_with_note_type_arg(self, page: _FakePage) -> None:
        """build() accepts optional note_type positional arg for back-compat."""
        nb = self._make_notebook()
        note = self._make_note(nb.id)
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id, "unified")  # type: ignore[arg-type]
        assert view is not None

    def test_note_editor_preview_starts_in_edit_mode(self, page: _FakePage) -> None:
        """content_preview_gesture must be hidden (visible=False) and content_field
        must be visible at build time (edit mode is the default)."""
        import flet as ft

        nb = self._make_notebook()
        note = self._make_note(nb.id, "Preview test")
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]

        found_preview_gestures: list[Any] = []

        def _walk(ctrl: Any) -> None:
            # content_preview_gesture: GestureDetector, visible=False, on_tap set
            if (
                isinstance(ctrl, ft.GestureDetector)
                and getattr(ctrl, "visible", True) is False
                and getattr(ctrl, "on_tap", None) is not None
            ):
                found_preview_gestures.append(ctrl)
            for attr in ("controls", "content"):
                child = getattr(ctrl, attr, None)
                if isinstance(child, list):
                    for c in child:
                        _walk(c)
                elif child is not None:
                    _walk(child)

        _walk(view)
        assert len(found_preview_gestures) == 1, (
            f"Expected exactly 1 content_preview_gesture (GestureDetector with "
            f"visible=False and on_tap set), found {len(found_preview_gestures)}"
        )
        gesture = found_preview_gestures[0]
        preview_wrap = getattr(gesture, "content", None)
        assert preview_wrap is not None, "content_preview_gesture must have content"
        assert getattr(preview_wrap, "visible", True) is False, (
            "content_preview_wrap must be hidden (visible=False) at build time"
        )

    def test_note_editor_builds_with_existing_strokes(self, page: _FakePage) -> None:
        """note.content_strokes with valid JSON must load without crash."""
        import json
        from services.note_service import NoteService

        nb = self._make_notebook()
        note = self._make_note(nb.id, "With Strokes")
        strokes = json.dumps([
            {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0,
             "color": "#F44336", "size": 3.0},
            {"x1": 10.0, "y1": 10.0, "x2": 20.0, "y2": 5.0,
             "color": "#212121", "size": 6.0},
        ])
        NoteService.instance().update_note_strokes(note.id, strokes)
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]
        assert view is not None

    def test_note_editor_builds_with_corrupt_strokes(self, page: _FakePage) -> None:
        """note.content_strokes with invalid JSON must not crash build() — graceful fallback."""
        from services.note_service import NoteService

        nb = self._make_notebook()
        note = self._make_note(nb.id, "Corrupt Strokes")
        NoteService.instance().update_note_strokes(note.id, "{{not: valid json[[[")
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]
        assert view is not None

    def test_canvas_layer_always_visible_in_stack(self, page: _FakePage) -> None:
        """Stack layer order: canvas_layer (index 0, bottom), text_layer (index 1),
        gesture_catcher (index 2, top — hidden in write mode).

        canvas_layer must be at the bottom so the text fields above it can
        receive focus; gesture_catcher on top captures touch only in draw mode.
        """
        import flet as ft
        nb = self._make_notebook()
        note = self._make_note(nb.id)
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)  # type: ignore[arg-type]

        # Walk the control tree to find the Stack with 3 children
        def _find_main_stack(ctrl: Any) -> Any:
            if isinstance(ctrl, ft.Stack) and getattr(ctrl, "controls", None):
                if len(ctrl.controls) == 3:  # canvas_layer, text_layer, gesture_catcher
                    return ctrl
            for attr in ("controls", "content"):
                child = getattr(ctrl, attr, None)
                if isinstance(child, list):
                    for c in child:
                        found = _find_main_stack(c)
                        if found:
                            return found
                elif child is not None:
                    found = _find_main_stack(child)
                    if found:
                        return found
            return None

        stack = _find_main_stack(view)
        assert stack is not None, "Could not find 3-child Stack (canvas+text+gesture)"

        # canvas_layer is index 0 (bottom), gesture_catcher is index 2 (top)
        canvas_layer = stack.controls[0]
        gesture_catcher = stack.controls[2]
        assert getattr(canvas_layer, "visible", True) is not False, \
            "canvas_layer must be visible by default (strokes persist across modes)"
        assert getattr(gesture_catcher, "visible", True) is False, \
            "gesture_catcher must be hidden in write mode at build time"


# ---------------------------------------------------------------------------
# DoodleBoard component
# ---------------------------------------------------------------------------

class TestDoodleBoard:
    def test_instantiation_does_not_raise(self) -> None:
        from components.doodle_canvas import DoodleBoard
        board = DoodleBoard()
        assert board.widget is not None

    def test_has_content_false_initially(self) -> None:
        from components.doodle_canvas import DoodleBoard
        board = DoodleBoard()
        assert board.has_content() is False

    def test_clear_does_not_raise_without_page(self) -> None:
        from components.doodle_canvas import DoodleBoard
        board = DoodleBoard()
        # Manually inject a shape so clear() has something to wipe
        import flet.canvas as cv
        import flet as ft
        board._shapes.append(cv.Line(
            x1=0, y1=0, x2=1, y2=1,
            paint=ft.Paint(color="#000000", stroke_width=2, style=ft.PaintingStyle.STROKE),
        ))
        # clear() guard: only calls canvas.update() if canvas.page is truthy
        board.clear()
        assert board.has_content() is False

    def test_export_png_empty_canvas(self) -> None:
        from components.doodle_canvas import DoodleBoard
        board = DoodleBoard()
        path = board.export_png()
        # Pillow may or may not be present in CI; just check it doesn't raise
        if path is not None:
            import os
            assert os.path.isfile(path)

    def test_export_png_with_shapes(self) -> None:
        import flet.canvas as cv
        import flet as ft
        from components.doodle_canvas import DoodleBoard
        board = DoodleBoard()
        # Inject a shape directly
        board._shapes.append(cv.Line(
            x1=10, y1=10, x2=100, y2=100,
            paint=ft.Paint(color="#F44336", stroke_width=5, style=ft.PaintingStyle.STROKE),
        ))
        assert board.has_content() is True
        path = board.export_png()
        if path is not None:
            import os
            assert os.path.isfile(path)

    def test_initial_pen_mode(self) -> None:
        from components import doodle_canvas
        board = doodle_canvas.DoodleBoard()
        assert board._is_eraser is False
        assert board._color in doodle_canvas._PALETTE

    def test_palette_has_eight_colors(self) -> None:
        from components import doodle_canvas
        assert len(doodle_canvas._PALETTE) == 8

    def test_pen_sizes_available(self) -> None:
        from components import doodle_canvas
        assert len(doodle_canvas._PEN_SIZES) >= 3

    def test_eraser_sizes_available(self) -> None:
        from components import doodle_canvas
        assert len(doodle_canvas._ERASER_SIZES) >= 2


# ---------------------------------------------------------------------------
# dashboard.py
# ---------------------------------------------------------------------------

class TestDashboardScreen:
    def test_build_empty_db(self, page: _FakePage) -> None:
        import screens.dashboard as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None

    def test_build_returns_view(self, page: _FakePage) -> None:
        import screens.dashboard as m
        view = m.build(page)  # type: ignore[arg-type]
        assert hasattr(view, "route")
        assert view.route == "/"

    def test_build_with_transactions(self, page: _FakePage) -> None:
        from services.finance_service import FinanceService
        svc = FinanceService.instance()
        cats = svc.get_all_categories()
        if cats:
            svc.add_transaction(cats[0].id, 50.0, "income", "Test income", None)
            svc.add_transaction(cats[0].id, 20.0, "expense", "Test expense", None)
        import screens.dashboard as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None


# ---------------------------------------------------------------------------
# finance_tracker.py
# ---------------------------------------------------------------------------

class TestFinanceTrackerScreen:
    def test_build_empty_db(self, page: _FakePage) -> None:
        import screens.finance_tracker as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None

    def test_build_returns_view(self, page: _FakePage) -> None:
        import screens.finance_tracker as m
        view = m.build(page)  # type: ignore[arg-type]
        assert hasattr(view, "route")
        assert view.route == "/finance"

    def test_build_with_transactions(self, page: _FakePage) -> None:
        from services.finance_service import FinanceService
        svc = FinanceService.instance()
        cats = svc.get_all_categories()
        if cats:
            svc.add_transaction(cats[0].id, 100.0, "income", "Salary", None)
        import screens.finance_tracker as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None


# ---------------------------------------------------------------------------
# bill_splits.py
# ---------------------------------------------------------------------------

class TestBillSplitsScreen:
    def test_build_empty_db(self, page: _FakePage) -> None:
        import screens.bill_splits as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None

    def test_build_returns_view(self, page: _FakePage) -> None:
        import screens.bill_splits as m
        view = m.build(page)  # type: ignore[arg-type]
        assert hasattr(view, "route")
        assert view.route == "/splits"

    def test_build_with_splits(self, page: _FakePage) -> None:
        from services.split_service import SplitService
        svc = SplitService.instance()
        svc.add_split(
            "Dinner",
            90.0,
            "2026-01-01",
            [{"name": "Bob", "share": 45.0}],
            45.0,
        )
        import screens.bill_splits as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None


# ---------------------------------------------------------------------------
# goals.py
# ---------------------------------------------------------------------------

class TestGoalsScreen:
    def test_build_empty_db(self, page: _FakePage) -> None:
        import screens.goals as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None

    def test_build_returns_view(self, page: _FakePage) -> None:
        import screens.goals as m
        view = m.build(page)  # type: ignore[arg-type]
        assert hasattr(view, "route")
        assert view.route == "/goals"

    def test_build_with_goals(self, page: _FakePage) -> None:
        from services.goal_service import GoalService
        svc = GoalService.instance()
        svc.add_goal("Vacation", None, 2000.0, 0.0, None, None)
        import screens.goals as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None


# ---------------------------------------------------------------------------
# investments.py
# ---------------------------------------------------------------------------

class TestInvestmentsScreen:
    def test_build_empty_db(self, page: _FakePage) -> None:
        import screens.investments as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None

    def test_build_returns_view(self, page: _FakePage) -> None:
        import screens.investments as m
        view = m.build(page)  # type: ignore[arg-type]
        assert hasattr(view, "route")
        assert view.route == "/investments"

    def test_build_with_investments(self, page: _FakePage) -> None:
        from services.investment_service import InvestmentService
        svc = InvestmentService.instance()
        svc.add_investment("AAPL", "Stocks", 10.0, 150.0, "2026-01-01")
        import screens.investments as m
        view = m.build(page)  # type: ignore[arg-type]
        assert view is not None
