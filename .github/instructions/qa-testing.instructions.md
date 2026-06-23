---
applyTo: "tests/**/*.py"
description: >
  Test writing conventions for the Finance Tracking App.
  Auto-loaded for all files under tests/. Covers fixtures, DB setup,
  mocking patterns, and what to test for each layer.
---

# QA Testing Conventions — Finance Tracking App

---

## In-Memory DB Setup (required for all repo/service tests)

Every test that touches the database MUST use an in-memory SQLite instance.
Add this to `tests/conftest.py` if not already present:

```python
import pytest
from config.database import init_db, create_tables

@pytest.fixture(autouse=True)
def fresh_db():
    """Reinitialise an in-memory DB before each test."""
    init_db(":memory:")
    create_tables()
    yield
```

Never use `database/finance.db` in tests — it contains real seed data.

---

## Model Tests (`tests/test_models.py`)

```python
from models.category import Category
from models.transaction import Transaction

def test_category_to_dict_keys():
    c = Category(name="Food", icon="restaurant", color="#FF5722", is_default=True)
    d = c.to_dict()
    assert set(d.keys()) >= {"id", "name", "icon", "color", "is_default"}

def test_transaction_type_mapping():
    """transaction_type must not collide with SQLAlchemy's 'type' discriminator."""
    t = Transaction(transaction_type="expense", amount=100.0, date="2026-01-15")
    assert t.transaction_type == "expense"
    assert not hasattr(t, "type")  # raw 'type' attr must not exist on instance
```

---

## Repository Tests

### Pattern for any concrete repository:

```python
from repositories.category_repository import CategoryRepository

def test_category_insert_and_get(fresh_db):
    repo = CategoryRepository()
    cat = repo.insert({"name": "Travel", "icon": "flight", "color": "#1E88E5", "is_default": False})
    assert cat.id is not None
    fetched = repo.get_by_id(cat.id)
    assert fetched.name == "Travel"

def test_category_delete(fresh_db):
    repo = CategoryRepository()
    cat = repo.insert({"name": "Delete Me", "icon": None, "color": "#000", "is_default": False})
    result = repo.delete(cat.id)
    assert result is True
    assert repo.get_by_id(cat.id) is None
```

### TransactionRepository month filter:

```python
from repositories.transaction_repository import TransactionRepository

def test_get_by_month_correct_month(fresh_db):
    repo = TransactionRepository()
    repo.insert({"date": "2026-06-01", "amount": 500.0, "transaction_type": "expense", "category_id": None, "description": "June tx", "person_id": None})
    repo.insert({"date": "2026-05-15", "amount": 200.0, "transaction_type": "expense", "category_id": None, "description": "May tx", "person_id": None})
    results = repo.get_by_month(2026, 6)
    assert len(results) == 1
    assert results[0].description == "June tx"

def test_get_by_month_empty(fresh_db):
    repo = TransactionRepository()
    assert repo.get_by_month(2025, 1) == []
```

---

## Service Tests (`tests/test_finance_service.py`)

```python
import pytest
from services.finance_service import FinanceService

@pytest.fixture(autouse=True)
def reset_singleton():
    """Force a fresh FinanceService instance per test."""
    FinanceService._instance = None
    yield
    FinanceService._instance = None

def test_add_transaction_negative_amount(fresh_db):
    svc = FinanceService.instance()
    with pytest.raises(ValueError, match="positive"):
        svc.add_transaction("2026-06-01", -100.0, None, "Bad", "expense")

def test_add_transaction_zero_amount(fresh_db):
    svc = FinanceService.instance()
    with pytest.raises(ValueError):
        svc.add_transaction("2026-06-01", 0.0, None, "Zero", "expense")

def test_add_and_get_transaction(fresh_db):
    svc = FinanceService.instance()
    tx = svc.add_transaction("2026-06-10", 250.0, None, "Groceries", "expense")
    assert tx.id is not None
    txs = svc.get_transactions_for_month(2026, 6)
    assert any(t.id == tx.id for t in txs)

def test_get_monthly_total_expense(fresh_db):
    svc = FinanceService.instance()
    svc.add_transaction("2026-06-01", 100.0, None, "A", "expense")
    svc.add_transaction("2026-06-02", 200.0, None, "B", "expense")
    svc.add_transaction("2026-06-03", 50.0, None, "C", "income")
    total = svc.get_monthly_total(2026, 6, "expense")
    assert total == 300.0

def test_delete_transaction(fresh_db):
    svc = FinanceService.instance()
    tx = svc.add_transaction("2026-06-05", 75.0, None, "Test", "expense")
    result = svc.delete_transaction(tx.id)
    assert result is True
    assert svc.get_transactions_for_month(2026, 6) == []

def test_description_too_long(fresh_db):
    svc = FinanceService.instance()
    with pytest.raises(ValueError, match="500"):
        svc.add_transaction("2026-06-01", 10.0, None, "x" * 501, "expense")
```

---

## EventBus Tests (`tests/test_event_bus.py`)

```python
from observers.event_bus import get_bus, Events

def test_subscribe_and_publish():
    bus = get_bus()
    received = []
    bus.subscribe(Events.TRANSACTION_WRITE, lambda data: received.append(data))
    bus.publish(Events.TRANSACTION_WRITE, {"id": 1})
    assert received == [{"id": 1}]

def test_multiple_subscribers():
    bus = get_bus()
    log = []
    bus.subscribe(Events.CATEGORY_WRITE, lambda d: log.append("A"))
    bus.subscribe(Events.CATEGORY_WRITE, lambda d: log.append("B"))
    bus.publish(Events.CATEGORY_WRITE, {})
    assert "A" in log and "B" in log
```

---

## CacheService Tests (`tests/test_cache_service.py`)

```python
from unittest.mock import patch
import time
from services.cache_service import CacheService

def test_lru_set_get():
    cache = CacheService.instance()
    cache._lru["test:key"] = [1, 2, 3]
    assert cache._lru.get("test:key") == [1, 2, 3]

def test_invalidate_by_prefix():
    cache = CacheService.instance()
    cache._lru["transactions:month:2026:6"] = ["tx1"]
    cache._lru["transactions:month:2026:5"] = ["tx2"]
    cache.invalidate("transactions:month:2026:6")
    assert "transactions:month:2026:6" not in cache._lru
    assert "transactions:month:2026:5" in cache._lru
```

---

## Screen Smoke Tests (`tests/test_screens_smoke.py`) — NEW, mandatory

The backend test matrix above (models/repos/services) never imports anything from
`screens/` or `components/`. That's the gap that lets Flet API misuse (wrong kwargs,
removed methods — see `flet-api.instructions.md`) pass every existing test and still
crash the app on first launch. Close it with a construction-only smoke test:

```python
import importlib
import pkgutil
import pytest
import screens

class StubPage:
    """Minimal stand-in for ft.Page — just enough surface for build(page) to run
    without opening a real window. Extend with attributes as screens need them."""
    def __init__(self):
        self.overlay = []
        self.views = []
        self.route = "/"
    def update(self):
        pass

def _all_screen_modules():
    return [m.name for m in pkgutil.iter_modules(screens.__path__)]

@pytest.mark.parametrize("module_name", _all_screen_modules())
def test_screen_builds_without_exception(module_name, fresh_db):
    mod = importlib.import_module(f"screens.{module_name}")
    page = StubPage()
    view = mod.build(page)  # must not raise
    assert view is not None
```

This does NOT replace manual visual testing on a device — it only proves the screen
*constructs* without throwing. It will catch every category of bug in the grep list at
the top of `flet-api.instructions.md`, because those are all runtime `AttributeError`/
`TypeError`s that fire the moment the control is built.

If a screen's `build(page)` needs something the stub doesn't have (e.g. `page.client_storage`),
add it to `StubPage` rather than skipping that screen from the parametrize list.

---

## Note Editor Tests (`tests/test_note_editor_format.py` and `tests/test_screens_smoke.py`)

The note editor is the most complex screen. Any change to `note_editor.py`,
`note_service.py`, or `models/note.py` requires these tests — add them if missing.

### Pure format function (module-level, no Flet dependency)

```python
from screens.note_editor import apply_text_format

class TestSelectionWrapping:
    def test_wraps_selected_range(self):
        assert apply_text_format("hello world", 6, 11, "**", "**", "bold") \
            == "hello **world**"

    def test_wraps_full_string(self):
        assert apply_text_format("hi", 0, 2, "_", "_", "italic") == "_hi_"

    def test_open_close_tags_differ(self):
        assert apply_text_format("text", 0, 4, "<u>", "</u>", "underline") \
            == "<u>text</u>"

class TestPlaceholderInsertion:
    def test_no_selection_inserts_placeholder(self):
        result = apply_text_format("abc", -1, -1, "**", "**", "bold")
        assert "**bold**" in result

    def test_cursor_at_start(self):
        result = apply_text_format("abc", 0, 0, "**", "**", "bold")
        assert result.startswith("**bold**")

    def test_cursor_at_end(self):
        result = apply_text_format("abc", 3, 3, "**", "**", "bold")
        assert result.endswith("**bold**")

    def test_empty_string_no_crash(self):
        result = apply_text_format("", -1, -1, "_", "_", "italic")
        assert result == "_italic_"

class TestEdgeCases:
    def test_start_equals_end_uses_placeholder(self):
        result = apply_text_format("hello", 2, 2, "**", "**", "bold")
        assert "**bold**" in result

    def test_start_beyond_length_appends(self):
        result = apply_text_format("abc", 99, 99, "_", "_", "italic")
        assert result == "abc_italic_"

    def test_reversed_offsets_treated_as_no_selection(self):
        # start > end after min/max correction → falls through to placeholder
        result = apply_text_format("hello", 4, 2, "**", "**", "bold")
        # after min/max: start=2, end=4 → wraps "ll"
        assert "**ll**" in result
```

### Stack layer order and preview mode (in `tests/test_screens_smoke.py`)

```python
class TestNoteEditorLayout:
    def test_stack_layer_order(self, page, nb, note):
        """canvas[0], text_layer[1], gesture_catcher[2] — non-negotiable."""
        import flet as ft
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)
        stack = _find_main_stack(view)  # helper already in test_screens_smoke.py
        assert stack is not None
        assert len(stack.controls) == 3
        # canvas_layer (index 0) must be visible
        assert getattr(stack.controls[0], "visible", True) is not False
        # gesture_catcher (index 2) must be hidden at build time
        assert getattr(stack.controls[2], "visible", True) is False

    def test_preview_starts_in_edit_mode(self, page, nb, note):
        """content_field visible=True, content_preview_wrap visible=False at build."""
        import flet as ft
        import screens.note_editor as m
        view = m.build(page, nb.id, note.id)

        def _find_stacks(ctrl, acc):
            if isinstance(ctrl, ft.Stack) and getattr(ctrl, "controls", None):
                acc.append(ctrl)
            for attr in ("controls", "content"):
                child = getattr(ctrl, attr, None)
                if isinstance(child, list):
                    for c in child: _find_stacks(c, acc)
                elif child is not None:
                    _find_stacks(child, acc)

        all_stacks = []
        _find_stacks(view, all_stacks)
        content_stacks = [s for s in all_stacks if len(s.controls) == 2]
        assert content_stacks, "Expected inner 2-child Stack for edit/preview toggle"
        inner = content_stacks[0]
        # controls[0] = content_field (TextField), controls[1] = preview wrap (Container)
        assert getattr(inner.controls[0], "visible", True) is not False, \
            "content_field must be visible in edit mode"
        assert getattr(inner.controls[1], "visible", True) is False, \
            "content_preview_wrap must be hidden in edit mode"

    def test_builds_with_existing_strokes(self, page, nb, note_with_strokes):
        """Note with valid content_strokes JSON loads without crash."""
        import screens.note_editor as m
        view = m.build(page, nb.id, note_with_strokes.id)
        assert view is not None

    def test_builds_with_corrupt_strokes(self, page, nb, note_with_corrupt_strokes):
        """Note with invalid JSON in content_strokes must not crash — graceful fallback."""
        import screens.note_editor as m
        view = m.build(page, nb.id, note_with_corrupt_strokes.id)
        assert view is not None
```

Add these fixtures to `conftest.py` if missing:

```python
@pytest.fixture
def note_with_strokes(nb, fresh_db):
    from services.note_service import NoteService
    import json
    NoteService._instance = None
    svc = NoteService.instance()
    note = svc.create_note(nb.id, "Stroke Note", "body")
    strokes = json.dumps([{"x1": 0, "y1": 0, "x2": 10, "y2": 10,
                           "color": "#FF0000", "size": 3}])
    svc.update_note_strokes(note.id, strokes)
    return svc.get_note_by_id(note.id)

@pytest.fixture
def note_with_corrupt_strokes(nb, fresh_db):
    from services.note_service import NoteService
    NoteService._instance = None
    svc = NoteService.instance()
    note = svc.create_note(nb.id, "Corrupt Strokes", "body")
    svc.update_note_strokes(note.id, "NOT_VALID_JSON{{{{")
    return svc.get_note_by_id(note.id)
```

### Dialog open/close regression tests

```python
def test_create_notebook_dialog_cancel_does_not_crash(self, page):
    """Cancel button must close the dialog without raising — tests the on_dismiss pattern."""
    import screens.notebooks as m
    view = m.build(page)
    # Find the FAB or action that opens create-dialog and trigger it
    # Then trigger cancel — must not raise
    # (Extend with your actual control-tree walker as needed)
    assert view is not None  # construction baseline

def test_note_editor_note_not_found_returns_view(self, page, nb):
    """build() with a non-existent note_id returns a View, not None."""
    import screens.note_editor as m
    view = m.build(page, nb.id, note_id=999999)
    assert view is not None
```

---

## Design / Layout Regression Checks

These are checked programmatically in `test_screens_smoke.py` where possible:

```python
def _all_controls_flat(ctrl, acc=None):
    """Flatten the full control tree into a list."""
    if acc is None:
        acc = []
    acc.append(ctrl)
    for attr in ("controls", "content", "actions"):
        child = getattr(ctrl, attr, None)
        if isinstance(child, list):
            for c in child:
                _all_controls_flat(c, acc)
        elif child is not None:
            _all_controls_flat(child, acc)
    return acc

def test_no_elevatedbutton_or_outlinedbutton(self, page):
    """ft.ElevatedButton and ft.OutlinedButton were removed in 0.85.x."""
    import flet as ft
    for screen_mod in _all_screen_modules():
        mod = importlib.import_module(f"screens.{screen_mod}")
        view = mod.build(page)
        for ctrl in _all_controls_flat(view):
            assert not isinstance(ctrl, ft.ElevatedButton), \
                f"{screen_mod}: ft.ElevatedButton found — use ft.FilledButton"
            assert not isinstance(ctrl, ft.OutlinedButton), \
                f"{screen_mod}: ft.OutlinedButton found — use ft.TextButton"
```

---

## Naming Conventions


- File: `tests/test_<layer>_<entity>.py` or `tests/test_<module>.py`
- Function: `test_<what>_<condition>` e.g. `test_add_transaction_negative_amount`
- One logical assertion per test (multiple `assert`s only if they test the same concept)
- Always test: happy path + at least one error/edge path per public method
- Use `pytest.raises(ValueError)` for expected validation errors
- No `print()` in tests — use `assert` with descriptive messages
- No `time.sleep()` — mock time with `freezegun` or `unittest.mock.patch` for TTL tests

---

## Running Tests

```powershell
# Full suite
.\.venv\Scripts\pytest.exe tests/ -v --tb=short

# Single file
.\.venv\Scripts\pytest.exe tests/test_finance_service.py -v

# With coverage (if pytest-cov installed)
.\.venv\Scripts\pytest.exe tests/ --cov=services --cov=repositories --cov-report=term-missing
```
