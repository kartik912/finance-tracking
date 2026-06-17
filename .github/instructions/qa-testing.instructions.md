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

## Naming & Structure Rules

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
