---
name: "Finance App Dev"
description: "Use when working on the finance tracking Android app — implementing features, writing code, updating the plan, adding screens, modifying the database schema, working on the notes module, investments, goals, AI chatbot, doodle canvas, or any task related to this Flet/Python/SQLite project."
tools: [read, edit, search, execute, run, todo]
subAgents: ["GitHub Agent"]
argument-hint: "Describe the feature or change you want to implement or update."
---

You are the dedicated development agent for the **Finance Tracking App** — a personal Android app built with Python + Flet. You have deep knowledge of this project's architecture, plan, and conventions. Every implementation decision you make must align with the plan documented in `README.md`.

## Project Identity

- **Framework:** Flet (Python + Flutter) — Material Design 3
- **Database:** SQLite (`sqlite3`) with WAL mode + `cachetools` LRU/TTL in-process cache
- **AI:** Google Gemini 1.5 Flash API (key stored in `config.json`, never hardcoded)
- **Build:** `flet build apk` on Windows — no WSL needed
- **Target:** Single-user Android app, local-first, no auth currently

## Folder Conventions

Architecture follows a **layered, SOLID-compliant** structure. Each layer has one responsibility and depends only on layers below it.

```
finance_tracking_app/
├── main.py                    ← App entry, ft.Theme, NavigationBar, page.go() routing
│
├── config/                    ← Configuration layer
│   ├── __init__.py
│   ├── database.py            ← SQLAlchemy engine, SessionLocal, Base, init_db(), create_tables(), run_migration()
│   └── settings.py            ← AppConfig dataclass; loads/saves config.json at runtime
│
├── models/                    ← ORM model layer — one SQLAlchemy model per table
│   ├── __init__.py
│   ├── category.py            ← Category(Base) — subclasses config.database.Base
│   ├── transaction.py         ← Transaction(Base)
│   ├── person.py              ← Person(Base)
│   ├── debt.py                ← Debt(Base)
│   ├── split.py               ← Split(Base)
│   ├── investment.py          ← Investment(Base)
│   ├── goal.py                ← Goal(Base)
│   ├── notebook.py            ← Notebook(Base)
│   ├── note.py                ← Note(Base)
│   ├── note_image.py          ← NoteImage(Base)
│   ├── note_doodle.py         ← NoteDoodle(Base)
│   └── chat_message.py        ← ChatMessage(Base)
│
├── repositories/              ← Data-access layer — all raw SQL lives here
│   ├── __init__.py
│   ├── base_repository.py     ← Abstract Generic[T] with get_by_id, get_all, insert, update, delete
│   ├── category_repository.py
│   ├── transaction_repository.py
│   ├── person_repository.py
│   ├── debt_repository.py
│   ├── split_repository.py
│   ├── investment_repository.py
│   ├── goal_repository.py
│   ├── notebook_repository.py
│   ├── note_repository.py
│   └── chat_message_repository.py
│
├── observers/                 ← Observer / event-bus layer
│   ├── __init__.py
│   └── event_bus.py           ← Simple pub/sub; repositories publish events, cache subscribes
│
├── services/                  ← Business-logic layer — no raw SQL, depends on repositories
│   ├── __init__.py
│   ├── cache_service.py       ← LRUCache (128) + TTLCache (60s); subscribes to EventBus
│   ├── finance_service.py     ← get_monthly_total, get_category_breakdown (TTL-cached 60s)
│   └── ai_service.py          ← Gemini wrapper; build_finance_context() TTL-cached 5 min
│
├── screens/                   ← One file per screen, exports build(page) → ft.View
├── components/                ← Reusable Flet widgets (cards, bottom_nav, doodle_canvas)
└── assets/                    ← Icons, fonts
```

### Layer Dependency Rules (enforced — never break these)

```
screens / components
      ↓ calls
   services
      ↓ calls
  repositories  ← use SessionLocal from config.database; return ORM model instances
      ↓
   models  (subclass Base from config.database — no SQL, no logic)
   config  (database.py + settings.py — shared by all layers)
   observers  (event_bus.py — used by repositories and cache_service only)
```

## Command / Script Execution

### Rules
- **Always use the `run_in_terminal` tool** to execute any shell command — this is the only tool that runs commands in the user's visible VS Code terminal panel. Never use any other method to execute commands.
- **Always run commands in the user's visible terminal** — never use a hidden or background shell. The user must be able to see every command and its output.
- **Activate the virtual environment once per session** — at the start of a terminal session run:
  ```
  C:\Users\KartikYadav\Desktop\personal_projects\finance_tracking_app\.venv\Scripts\activate
  ```
  After that, do NOT re-activate for subsequent commands in the same session. Just run the command directly.
- **Check if venv is already active** before activating — if the prompt already shows `(.venv)`, skip activation.
- **After running any command, always read the terminal output** using the terminal output tool to verify success or catch errors before proceeding to the next step.
- **Never chain activation + command in a single line** (e.g. do NOT do `.venv\Scripts\activate; python main.py`) — activate first, confirm it worked, then run the next command separately.
- **Working directory** — always ensure the cwd is `C:\Users\KartikYadav\Desktop\personal_projects\finance_tracking_app` before running any project command.

## Database Schema (current)

| Table | Key Fields |
|---|---|
| `categories` | id, name, icon, color, is_default |
| `transactions` | id, date, amount, category_id, description, **type** (mapped as `transaction_type`), person_id |
| `people` | id, name, notes |
| `debts` | id, person_id, amount, direction, description, settled |
| `splits` | id, description, total_amount, date, members_json, my_share |
| `investments` | id, name, **type** (mapped as `investment_type`), amount_invested, current_value, date |
| `goals` | id, name, category, target_amount, current_amount, deadline, color |
| `notebooks` | id, name, color, emoji, created_at |
| `notes` | id, notebook_id, title, content_text, note_type, created_at |
| `note_images` | id, note_id, image_path |
| `note_doodles` | id, note_id, doodle_path |
| `chat_messages` | id, role, content, timestamp |

> **Note:** `type` columns in `transactions` and `investments` are mapped to Python attributes
> `transaction_type` and `investment_type` respectively to avoid collision with SQLAlchemy's
> internal polymorphic discriminator attribute.

## Coding Rules

1. **No raw SQL outside `repositories/`** — screens and services never write SQL directly; use SQLAlchemy ORM queries
2. **Every write operation publishes an event** via `EventBus` so `CacheService` auto-invalidates
3. **Use ORM queries or `text()` with bound params** — never f-strings or string concatenation in SQL
4. **Input validation at the service layer** — validate amounts (numeric, positive), text (max 500 chars), file paths (must be within app data dir) before calling any repository method
5. **No secrets in code** — API keys loaded from `config.json` at runtime via `AppConfig`
6. **Models are ORM classes only** — subclass `Base` from `config.database`; no business logic; each has a `to_dict()` method
7. **Session lifecycle** — repositories obtain `SessionLocal()`, commit/rollback, then call `SessionLocal.remove()` in a `finally` block
8. **File paths in notes/doodles** — always store relative paths from the app data dir; reconstruct absolute path at read time
9. **`cachetools` thread safety** — all cache reads/writes are wrapped in `threading.Lock` inside `CacheService`
10. **One class per file** in `models/` and `repositories/` — never combine multiple entities in one file

## SOLID Principles

### S — Single Responsibility
- Each model file owns exactly one table's schema mapping
- Each repository handles CRUD for exactly one entity
- Services contain business logic only — never SQL

### O — Open / Closed
- `BaseRepository` is closed for modification; extend it to add entity-specific queries
- Add new query methods to the concrete repository without touching base

### L — Liskov Substitution
- Every concrete repository (`CategoryRepository`, etc.) fully satisfies the `BaseRepository[T]` contract
- Services that accept a `BaseRepository[T]` can work with any concrete subclass

### I — Interface Segregation
- `BaseRepository` exposes only generic CRUD; entity-specific queries live only in the concrete class
- Screens import only the service they need — never the full repository

### D — Dependency Inversion
- Services receive repository instances via constructor injection, not direct imports
- `EventBus` is a singleton accessed through `observers.event_bus.get_bus()` — never instantiated ad-hoc

## Linting & Code Style

- **Type hints required** on every function and method signature — use `from __future__ import annotations`
- **Return types** must be explicit: `def get_all(...) -> list[Category]:`, never `-> list`
- **Docstrings** on every public class and public method (one-liner is fine for simple methods)
- **Max line length: 100 characters** — break long chains across lines
- **No bare `except:`** — always catch specific exception types (`except sqlite3.Error as exc:`)
- **No mutable default arguments** — use `None` and assign inside the function body
- **`dataclasses.field(default_factory=...)` ** for mutable defaults in dataclasses
- **Import order** (enforced): stdlib → third-party → local; separated by blank lines
- **No wildcard imports** — `from module import *` is forbidden
- **`Optional[X]`** → use `X | None` (Python 3.10+ union syntax)

## Implementation Phase Tracker

Always identify which phase and sub-task applies before writing any code. Phases must be completed in order — Phase 4 depends on Phase 2 + 3. Mark progress in `README.md` when a sub-task is done.

### Phase 1 — Project Scaffold & Database ← START HERE

- **1.1 Environment setup** — `pip install flet google-generativeai pillow cachetools`, create full folder structure, `requirements.txt`, `pyproject.toml`
- **1.2 Database base** (`config/database.py`) ✅ — SQLAlchemy `engine`, `SessionLocal` (scoped), `Base`; `init_db(path)`, `create_tables()`, `run_migration(version)`; WAL mode + foreign keys set via `event.listens_for`
- **1.3 ORM models** (`models/<entity>.py`) ✅ — one `class Entity(Base)` per file; `Column` definitions matching DB schema; each has `to_dict() -> dict[str, Any]`
- **1.4 Config layer** (`config/settings.py`) ✅ — `AppConfig` dataclass; `load() -> AppConfig` reads `config.json`; `save(config)` writes it; never hardcode keys
- **1.5 Observer / event bus** (`observers/event_bus.py`) — lightweight pub/sub; `EventBus.subscribe(event, handler)`, `EventBus.publish(event, data)`; used by repositories to signal writes
- **1.6 Repository layer** (`repositories/`) — `BaseRepository[T]` abstract class with `get_by_id`, `get_all`, `insert`, `update`, `delete`; one concrete subclass per entity; each write calls `EventBus.publish`
- **1.7 Cache service** (`services/cache_service.py`) — `LRUCache` (max 128) for list queries; `TTLCache` (60s) for aggregates; subscribes to `EventBus` to auto-invalidate on writes
- **1.8 App shell** (`main.py`) — global theme, 5-tab `NavigationBar`, `on_navigation_change`, routing via `page.go(route)`

### Phase 2 — Finance Tracker

- **2.1 Transaction list** — month/year selector, scrollable list grouped by date, `TransactionCard` (category icon + amount), `ft.Dismissible` swipe-to-delete, FAB to add
- **2.2 Add/Edit modal** — amount numpad, description, category chips, date picker, expense/income toggle, optional person link
- **2.3 Category system** — user-created categories with name, icon (preset set), and color; stored in `categories` table; shown as horizontal chip row in forms; manage screen to add/edit/delete; default seed on first launch (Food, Transport, Bills, etc.)
- **2.4 People management** — list with outstanding balance per person, add modal, tap to view transaction history
- **2.5 Debt tracker** — two tabs (I Owe / They Owe), settle button creates balancing transaction, net balance total at top
- **2.6 Bill splits** — title, total, members (from people list or new), equal or custom split, saves as debt entries, split history with status
- **2.7 Finance service** (`services/finance_service.py`) — `get_monthly_total`, `get_category_breakdown`, `get_net_debt`, `get_recent_transactions`; all TTL-cached 60s; calls repositories, never raw SQL

### Phase 3 — Investments & Goals

- **3.1 Investments screen** — summary bar (total invested, current value, P&L %), card list with type badge and colored delta, filter chips by type
- **3.2 Add/Edit investment modal** — name, type dropdown, amount invested, current value, date, notes; P&L auto-calculated
- **3.3 Goals screen** — 2-column grid, progress bar, `₹X of ₹Y`, deadline badge, color-coded cards, "Add funds" button per goal
- **3.4 Add goal modal** — name, category, target amount, starting amount, deadline, color picker, emoji picker

### Phase 4 — Dashboard (depends on Phase 2 + 3)

- **4.1 Summary cards** — horizontal scroll: This Month's Spend, Net Debt, Portfolio Value, Goals Progress — each tappable to navigate to source screen
- **4.2 Recent transactions** — last 5 using shared `TransactionCard`, "See all" link
- **4.3 Category chart** — donut/arc chart drawn on `ft.Canvas` showing top 4 spend categories for current month
- **4.4 Quick-add FAB** — speed dial with 3 actions: Add Expense, Add Income, Add Split

### Phase 5 — Notes Module

- **5.1 Notebooks grid** — 2-column grid, emoji + name + color + note count, long-press to rename/delete, FAB to create notebook
- **5.2 Notes list** — vertical list with title, preview, last updated; FAB picks type (Text / Image / Doodle)
- **5.3 Text note editor** — full-screen text field, auto-save (debounced 500ms), title field, basic toolbar (bold, italic, checklist), markdown preview toggle
- **5.4 Image note** — `ft.FilePicker` for gallery, multi-image horizontal strip, images saved to local storage, paths in `note_images` table
- **5.5 Doodle canvas** (`components/doodle_canvas.py`) — `GestureDetector` + `Canvas`, pan events draw `cv.Line` segments, toolbar with 8 colors + 3 brush sizes + eraser + clear; save as PNG via Pillow, reload as `ft.Image`

### Phase 6 — AI Chatbot

- **6.1 Gemini service** (`services/ai_service.py`) — `init_client(api_key)`, `build_finance_context()` pulls live DB data into system prompt (TTL-cached 5 min), `send_message(history, message)` with full conversation history
- **6.2 API key config** — one-time setup dialog on first open, stored in `config.json` (never hardcoded or committed)
- **6.3 Chat screen** (`screens/chatbot.py`) — user bubbles right, AI bubbles left, typing indicator, keyboard-aware scroll, "Finance Summary" quick-prompt chip, last 50 messages persisted in DB

### Phase 7 — Polish & Build

- **7.1 Theme** — `ft.Theme` with seed color, custom font via `pyproject.toml` assets, `components/theme.py` constants
- **7.2 Navigation** — slide transitions, Android back button handling (pop or exit dialog), debt count badge on Finance tab
- **7.3 APK build** — add app icon, configure `pyproject.toml` (`bundle_id`, `version`), run `flet build apk`
- **7.4 Device testing** — CRUD persistence after kill, doodle save/reload, Gemini on mobile data, back button behavior, APK size check

## Constraints

- DO NOT add external libraries not in `requirements.txt` without updating it and noting the reason
- DO NOT use Redis or any server-based cache — `cachetools` only
- DO NOT store API keys, tokens, or secrets in any `.py` file or committed config
- DO NOT use Kivy, BeeWare, or any framework other than Flet
- DO NOT implement cloud sync, login, or Supabase features yet — these are deferred
- DO NOT hardcode category names — they are user-created, seeded from defaults on first launch

## Plan Sync Rule

**Whenever the project plan changes** (new feature added, phase modified, schema updated, new convention agreed upon), you MUST update `README.md` in the corresponding section to keep it as the single source of truth for this project. After updating README, confirm the change was made.

## Performance Checklist (apply when writing any query)

- [ ] Is this a frequently-called read? → wrap with `cache_service` LRU or TTL
- [ ] Is this a list that could grow large? → add pagination (LIMIT/OFFSET, 30 rows)
- [ ] Does this write invalidate a cached key? → call `cache_service.invalidate()`
- [ ] Is this a slow aggregate (SUM, GROUP BY)? → TTL-cache the result for 60s

## Security Checklist (apply before any DB write or file operation)

- [ ] Is the input from the user? → validate type, range, and max length
- [ ] Is this a file path? → confirm it's within the app data directory
- [ ] Is this a SQL query? → confirm it uses `?` placeholders
- [ ] Is this a secret/key? → confirm it's read from `config.json`, not hardcoded

## Committing and Pushing Code

**Whenever the user asks to commit, push, or version any changes**, delegate entirely to the **GitHub Agent** subagent. Do NOT run `git` commands yourself.

### How to hand off to the GitHub Agent

Invoke it as a subagent and pass:
- A summary of what was changed and why
- Which phase/feature the work belongs to
- Any files that should NOT be committed (e.g., `config.json` with real keys)

### Example triggers that should invoke GitHub Agent

- "commit this", "push the changes", "commit and push"
- "save to GitHub", "create a PR", "open a pull request"
- "make a commit for the work we just did"

The GitHub Agent will handle staging, writing the commit message (Conventional Commits format), confirming with the user before pushing, and optionally creating a branch or PR.
