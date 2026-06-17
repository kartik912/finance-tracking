# Finance Tracking App

A personal Android app built with Python + Flet for daily finance tracking, investment management,
goal setting, rich notes (text/image/doodle), and an AI chatbot - all stored locally on-device.

---

## Features

- **Finance Tracker** - Log daily expenses and income by user-created categories (custom name, icon, and color)
- **Debt Tracker** - Track who owes whom (and how much)
- **Bill Splits** - Create and manage shared expense splits
- **Investments** - Portfolio tracker: stocks, mutual funds, FDs, crypto
- **Financial Goals** - Set goals with target amounts and track progress
- **Notes** - Grouped notebooks with text, image, and doodle (finger-drawing) support
- **AI Chatbot** - Finance-aware assistant powered by Gemini 1.5 Flash

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| UI Framework | Flet (Python + Flutter) | Material Design 3, Canvas drawing, Windows APK build |
| Database ORM | SQLAlchemy 2.0 + SQLite (WAL mode) | Type-safe ORM queries; WAL gives faster concurrent reads |
| In-Process Cache | cachetools (LRU + TTL) | Caches frequent DB queries in-memory; no server needed, works on Android |
| AI Chatbot | Google Gemini 1.5 Flash (google-genai) | Free tier: 15 req/min, 1M tokens/day |
| Android Build | flet build apk | Native Windows support, no WSL/Docker needed |
| Future Sync | Supabase free tier | Cloud backup when needed |

---

## Project Structure

Layered, SOLID-compliant architecture. Each layer has one responsibility and depends only on layers below it.

```
finance_tracking_app/
+-- main.py                          <- App entry: ft.Theme, NavigationBar, page.go() routing
+-- create_db.py                     <- Dev helper: python create_db.py
+-- seed.py                          <- Dev helper: python seed.py (realistic sample data)
+-- requirements.txt
|
+-- config/
|   +-- database.py                  <- SQLAlchemy engine, SessionLocal, Base, init_db(), create_tables()
|   +-- settings.py                  <- AppConfig dataclass; loads/saves config.json at runtime
|
+-- models/                          <- ORM model layer - one SQLAlchemy class per table, subclasses Base
|   +-- category.py
|   +-- transaction.py
|   +-- person.py
|   +-- debt.py
|   +-- split.py
|   +-- investment.py
|   +-- goal.py
|   +-- notebook.py
|   +-- note.py
|   +-- note_image.py
|   +-- note_doodle.py
|   +-- chat_message.py
|
+-- repositories/                    <- Data-access layer - all ORM queries live here
|   +-- base_repository.py           <- Concrete Generic[T]: get_by_id, get_all, insert, update, delete
|   +-- category_repository.py
|   +-- transaction_repository.py
|   +-- person_repository.py
|   +-- debt_repository.py
|   +-- split_repository.py
|   +-- investment_repository.py
|   +-- goal_repository.py
|   +-- notebook_repository.py
|   +-- note_repository.py
|   +-- note_image_repository.py
|   +-- note_doodle_repository.py
|   +-- chat_message_repository.py
|
+-- observers/
|   +-- event_bus.py                 <- Pub/sub; repositories publish events, cache subscribes
|
+-- services/                        <- Business-logic layer - no SQL, depends on repositories
|   +-- cache_service.py             <- LRUCache (128) + TTLCache (60s); auto-invalidates via EventBus
|   +-- finance_service.py           <- (Phase 2) aggregations, totals, breakdowns
|   +-- ai_service.py                <- (Phase 6) Gemini API wrapper with finance context
|
+-- screens/                         <- One file per screen, each exports build(page) -> ft.View
|   +-- dashboard.py                 <- (Phase 4 placeholder)
|   +-- finance_tracker.py           <- (Phase 2 placeholder)
|   +-- investments.py               <- (Phase 3 placeholder)
|   +-- goals.py                     <- (Phase 3 placeholder)
|   +-- notebooks.py                 <- (Phase 5 placeholder)
|
+-- components/                      <- Reusable Flet widgets (Phase 2+)
+-- assets/                          <- Icons, fonts
```

---

## Database Schema

| Table | Key Fields |
|---|---|
| categories | id, name, icon, color, is_default |
| transactions | id, date, amount, category_id, description, type*, person_id |
| people | id, name, notes |
| debts | id, person_id, amount, direction, description, settled |
| splits | id, description, total_amount, date, members_json, my_share |
| investments | id, name, type*, amount_invested, current_value, date |
| goals | id, name, category, target_amount, current_amount, deadline, color |
| notebooks | id, name, color, emoji, created_at |
| notes | id, notebook_id, title, content_text, note_type, created_at |
| note_images | id, note_id, image_path |
| note_doodles | id, note_id, doodle_path |
| chat_messages | id, role, content, timestamp |

> **type column mapping:** transactions.type and investments.type are mapped to Python attributes
> transaction_type and investment_type to avoid collision with SQLAlchemy's internal polymorphic
> discriminator. Always use Transaction(transaction_type=...) and Investment(investment_type=...).

---

## Implementation Phases

### Phase 1 - Project Scaffold & Database (COMPLETE)

- **1.1 DONE Environment setup** - pip install -r requirements.txt, full folder structure, requirements.txt
- **1.2 DONE Database base** (config/database.py) - SQLAlchemy engine, scoped SessionLocal, Base; thread-safe init_db(path) singleton with WAL + foreign keys via event.listens_for; create_tables() lazy-imports all 12 model modules; run_migration(version)
- **1.3 DONE ORM models** (models/<entity>.py) - 12 files, one class Entity(Base) per table; Column definitions; each has to_dict() -> dict[str, Any] and __repr__()
- **1.4 DONE Config layer** (config/settings.py) - AppConfig dataclass; load() -> AppConfig reads config.json with defaults for missing fields; save(config) writes it; unknown keys stored in extra; never hardcode secrets
- **1.5 DONE Observer / event bus** (observers/event_bus.py) - thread-safe pub/sub; EventBus.subscribe(event, handler), EventBus.publish(event, data); Events namespace with 12 write-event constants; singleton via get_bus()
- **1.6 DONE Repository layer** (repositories/) - BaseRepository[T] CONCRETE generic base implementing full CRUD via self._model_class + self._write_event; 12 slim concrete subclasses call super().__init__(ModelClass, Events.X_WRITE) and add only entity-specific query methods; every write publishes to EventBus
- **1.7 DONE Cache service** (services/cache_service.py) - LRUCache (max 128) for list queries; TTLCache (60s) for aggregates; subscribes to all 12 EventBus write events to auto-invalidate; double-checked locking singleton via CacheService.instance()
- **1.8 DONE App shell** (main.py) - MD3 theme seeded from ft.Colors.INDIGO, 5-tab NavigationBar, lazy screen imports via importlib, on_route_change + on_view_pop (Android back button), placeholder screens for all 5 routes

### Phase 2 - Finance Tracker

- **2.1 Transaction list** - month/year selector, scrollable list grouped by date, TransactionCard with category icon + amount, swipe-to-delete (ft.Dismissible), FAB to add
- **2.2 Add/Edit modal** - amount numpad, description, category chips, date picker, expense/income toggle, optional person link
- **2.3 Category system** - user-created categories, each with a name, icon (picked from a preset icon set), and color; stored in a categories DB table; displayed as a horizontal chip row in forms; manage categories screen to add/edit/delete; sensible defaults (Food, Transport, Bills, etc.) seeded on first launch
- ~~**2.4 People management**~~ - REMOVED: no standalone people screen; people typed inline in Bill Splits
- ~~**2.5 Debt tracker**~~ - REMOVED: no separate debt tracker screen; debt is implicit in bill splits
- **2.6 DONE Bill splits** - title, total, members (typed inline), equal or custom split per member, split history list with total + my share
- **2.7 Finance service** (services/finance_service.py) - get_monthly_total, get_category_breakdown, get_net_debt, get_recent_transactions; all TTL-cached (60s); calls repositories only, no raw SQL

### Phase 3 - Investments & Goals

- **3.1 Investments screen** - summary bar (total invested, current value, P&L %), card list with type badge and colored delta, filter chips by type
- **3.2 Add/Edit investment modal** - name, type dropdown, amount invested, current value, date, notes; P&L auto-calculated
- **3.3 Goals screen** - 2-column grid, progress bar, target amounts, deadline badge, color-coded cards, Add funds button per goal
- **3.4 Add goal modal** - name, category, target amount, starting amount, deadline, color picker, emoji picker

### Phase 4 - Dashboard (depends on Phase 2 + 3)

- **4.1 Summary cards** - horizontal scroll: This Month's Spend, Net Debt, Portfolio Value, Goals Progress - each tappable to navigate
- **4.2 Recent transactions** - last 5 using shared TransactionCard, See all link
- **4.3 Category chart** - donut/arc chart drawn on ft.Canvas showing top 4 spend categories for current month
- **4.4 Quick-add FAB** - speed dial with 3 actions: Add Expense, Add Income, Add Split

### Phase 5 - Notes Module

- **5.1 Notebooks grid** - 2-column grid, emoji + name + color + note count, long-press to rename/delete, FAB to create notebook
- **5.2 Notes list** - within a notebook: vertical list with title, preview, last updated; FAB picks note type (Text / Image / Doodle)
- **5.3 Text note editor** - full-screen text field, auto-save (debounced 500ms), title field, basic toolbar (bold, italic, checklist), markdown preview toggle
- **5.4 Image note** - ft.FilePicker for gallery, multi-image support in horizontal strip, images saved to local storage as relative paths in note_images table
- **5.5 Doodle canvas** (components/doodle_canvas.py) - GestureDetector + Canvas, pan events draw cv.Line segments, toolbar with 8 colors + 3 brush sizes + eraser + clear; save as PNG via Pillow, reload as ft.Image

### Phase 6 - AI Chatbot

- **6.1 Gemini service** (services/ai_service.py) - init_client(api_key), build_finance_context() pulls live DB data into system prompt (TTL-cached 5 min), send_message(history, message) with full conversation history
- **6.2 API key config** - one-time setup dialog on first open, stored in local config.json (never hardcoded or committed)
- **6.3 Chat screen** (screens/chatbot.py) - user bubbles right, AI bubbles left, typing indicator, keyboard-aware scroll, Finance Summary quick-prompt chip, last 50 messages persisted in DB

### Phase 7 - Polish & Build

- **7.1 Theme** - ft.Theme with seed color, custom font via pyproject.toml assets, components/theme.py constants
- **7.2 Navigation** - slide transitions, Android back button handling (pop or exit dialog), debt count badge on Finance tab
- **7.3 APK build** - add app icon, configure pyproject.toml (bundle_id, version), run flet build apk
- **7.4 Device testing** - CRUD persistence after kill, doodle save/reload, Gemini on mobile data, back button behavior, APK size check

---

## Setup

### Prerequisites

- Python 3.11+
- Android SDK (auto-downloaded by Flet on first flet build apk)
- A free Google AI Studio account for a Gemini API key (Phase 6)

### Install dependencies

    pip install -r requirements.txt

Or manually:

    pip install flet==0.85.3 sqlalchemy cachetools pillow google-genai

### Run in desktop dev mode (hot reload)

    flet run main.py

### Create database (dev)

    python create_db.py

### Seed with sample data (dev)

    python seed.py

### First launch

On first run the app will:
1. Create finance.db in the app's local data directory (page.app_data_dir) with all 12 tables
2. Register cache invalidators so the in-process cache auto-clears on any write
3. On first visit to the Chat screen - prompt for your Gemini API key (stored in config.json, never committed)

NOTE: config.json is in .gitignore and must NEVER be committed - it contains your real Gemini API key.

### Build Android APK

    flet build apk

Output: build/apk/app-release.apk - transfer to your Android device via USB or Google Drive and install.

On first flet build apk, Flet auto-downloads the Android SDK and JDK if not already present. This takes a few minutes once.

---

## Performance Optimizations

### Currently implemented

- **SQLite WAL mode** - PRAGMA journal_mode=WAL allows reads and writes to happen concurrently
- **In-process LRU cache** (cachetools) - list queries cached by key; evicted on any write via EventBus
- **TTL cache for aggregates** - monthly totals, category breakdown, finance AI context: cached 60s (5 min for AI); avoids re-running GROUP BY on every screen refresh
- **Debounced auto-save** - text notes auto-save with 500ms debounce
- **ORM with bound parameters** - all DB calls via SQLAlchemy ORM; no string-concatenated SQL, prevents SQL injection structurally

### Recommended additions

- **SQLite indexes** - add indexes on transactions(date), transactions(category_id), notes(notebook_id)
- **Pagination** - transaction list should load 30 rows at a time (lazy load on scroll)
- **Async DB calls** - wrap slow queries in asyncio or a thread pool; Flet supports page.run_thread
- **Image compression** - compress picked images to JPEG at 80% quality via Pillow
- **Doodle PNG optimization** - save at device density only, use optimize=True in Pillow

---

## Security

### Current (local-only app)

- **No hardcoded secrets** - Gemini API key stored in config.json in the app's private data directory (not in repo, in .gitignore)
- **ORM / parameterized SQL** - all queries use SQLAlchemy ORM; no raw string SQL; SQL injection is structurally impossible
- **Input validation** - validate amount fields (numeric, positive), text fields (max 500 chars), and file paths (restrict to app data directory) at the service layer before any DB write
- **Private storage** - DB file and config.json live in Android's app-private directory; not accessible to other apps without root

### Future - when login + cloud is added

- **Supabase Row Level Security (RLS)** - enforce at DB level; never rely on client-side filtering alone
- **JWT auth** - Supabase Auth issues short-lived JWTs (1 hour); refresh tokens stored in Android Keystore
- **HTTPS/TLS enforced** - all Supabase API calls over TLS; never allow HTTP fallback
- **SQLCipher for local DB** - if especially sensitive data is stored, encrypt the SQLite file at rest
- **API key rotation** - process to rotate the Gemini API key without a new APK deploy
- **Audit log table** - audit_log table (action, table_name, row_id, timestamp) for personal accountability
- **Data export & wipe** - Export all data as JSON and Wipe all local data options in settings

---

## Deferred / Future

- GPay / UPI integration (SMS parser or export file reader)
- Supabase cloud sync for cross-device backup
- Investment price auto-fetch (Yahoo Finance API)
- Goal deadline push notifications