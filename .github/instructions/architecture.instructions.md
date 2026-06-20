---
applyTo: "**/*.py"
description: >
  Layer architecture, SOLID rules, coding conventions, and linting standards for the
  Finance Tracking App. Extracted from the agent persona so this loads only when actual
  Python files are in context, instead of being re-read on every chat turn regardless
  of relevance.
---

# Architecture & Coding Standards

## Folder Conventions

```
finance_tracking_app/
├── main.py                 ← entry, ft.Theme, NavigationBar, push_route routing
├── config/                 ← database.py (engine/SessionLocal/Base/init_db), settings.py
├── models/                 ← one SQLAlchemy model per file, subclasses Base, to_dict()+__repr__()
├── repositories/           ← all ORM queries; BaseRepository[T] concrete generic CRUD base
├── observers/              ← event_bus.py — pub/sub; repos publish, cache subscribes
├── services/               ← business logic only, no raw SQL; cache_service, finance_service, ai_service
├── screens/                ← one file per screen, exports build(page) -> ft.View
├── components/             ← reusable widgets
└── assets/                 ← icons, fonts
```

### Layer Dependency Rule (enforced by QA Agent — never break)
```
screens / components → services → repositories → models / config / observers
```
Screens and components must NEVER import from `repositories.*` directly. This is checked
mechanically in `scripts/qa_check.ps1` Step 2 — don't rely on remembering it.

## Database Schema (current)

| Table | Key Fields |
|---|---|
| `categories` | id, name, icon, color, is_default |
| `transactions` | id, date, amount, category_id, description, **type** → mapped `transaction_type`, person_id |
| `people` | id, name, notes |
| `debts` | id, person_id, amount, direction, description, settled |
| `splits` | id, description, total_amount, date, members_json, my_share |
| `investments` | id, name, **type** → mapped `investment_type`, amount_invested, current_value, date |
| `goals` | id, name, category, target_amount, current_amount, deadline, color |
| `notebooks` | id, name, color, emoji, created_at |
| `notes` | id, notebook_id, title, content_text, note_type, created_at |
| `note_images` | id, note_id, image_path |
| `note_doodles` | id, note_id, doodle_path |
| `chat_messages` | id, role, content, timestamp |

`type` columns are mapped to `transaction_type`/`investment_type` to avoid colliding with
SQLAlchemy's polymorphic discriminator attribute. Don't "simplify" this back to `type`.

## Coding Rules
1. No raw SQL outside `repositories/` — ORM queries only.
2. Every write publishes an `EventBus` event so `CacheService` auto-invalidates.
3. Bound params or ORM only — never f-strings/concatenation in SQL.
4. Validate input at the **service** layer: amounts numeric+positive, text ≤500 chars,
   file paths within the app data dir — before calling any repository method.
5. No secrets in code — API keys load from `config.json` via `AppConfig` at runtime.
6. Models are ORM classes only, no business logic, each has `to_dict()`.
7. Repositories: `SessionLocal()` → commit/rollback → `SessionLocal.remove()` in `finally`.
8. Note/doodle file paths: store relative to app data dir, reconstruct absolute at read time.
9. All `cachetools` reads/writes wrapped in `threading.Lock` inside `CacheService`.
10. One class per file in `models/` and `repositories/`.
11. `BaseRepository` is a concrete generic base (not ABC) — implements full CRUD;
    concrete repos call `super().__init__(ModelClass, Events.X_WRITE)` and add only
    entity-specific query methods. (Rationale: eliminates ~600 lines of duplicated CRUD
    across 12 repos while preserving LSP.)

## SOLID
- **S**: one model = one table; one repository = one entity's CRUD; services hold logic, never SQL.
- **O**: `BaseRepository` closed for modification — extend via the concrete subclass.
- **L**: every concrete repository fully satisfies `BaseRepository[T]`.
- **I**: `BaseRepository` exposes only generic CRUD; entity-specific queries stay in the subclass.
- **D**: services receive repositories via constructor injection; `EventBus` accessed only
  via the `get_bus()` singleton, never instantiated ad-hoc.

## Linting & Style
- Type hints on every signature; `from __future__ import annotations`.
- Explicit return types: `-> list[Category]`, never bare `-> list`.
- Docstrings on every public class/method (one-liner OK for simple ones).
- Max line length 100.
- No bare `except:` — catch specific exception types.
- No mutable default arguments — use `None`, assign inside the function body.
- Import order: stdlib → third-party → local, blank line separated.
- No wildcard imports.
- `X | None`, not `Optional[X]`.

## Performance Checklist (apply when writing any query)
- [ ] Frequently-called read? → wrap with `cache_service` LRU or TTL.
- [ ] List that could grow large? → paginate (LIMIT/OFFSET, 30 rows).
- [ ] Does this write invalidate a cached key? → call `cache_service.invalidate()`.
- [ ] Slow aggregate (SUM/GROUP BY)? → TTL-cache 60s.

## Architect Decision Log
| Decision | Rationale |
|---|---|
| `BaseRepository` concrete, not pure ABC | eliminate duplicated CRUD across 12 repos |
| `session.remove()` in every `finally` | prevent thread-local session leaks on Android |
| `transaction_type`/`investment_type` mapping | avoid colliding with ORM's `type` discriminator |
| Lazy screen imports via `importlib` in `main.py` | keep startup fast |
