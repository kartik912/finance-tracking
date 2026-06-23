# Finance Tracking App — Progress

Single source of truth for what's done, in progress, and deferred. The Finance App Dev
agent reads this before starting work and updates it after finishing a sub-task — it does
NOT live in the agent persona file anymore, so updating progress doesn't require editing
a file that's reloaded into every chat turn.

## Phase 1 — Project Scaffold & Database ✅
- 1.1 ✅ Environment setup
- 1.2 ✅ Database base (`config/database.py`)
- 1.3 ✅ ORM models
- 1.4 ✅ Config layer (`config/settings.py`)
- 1.5 ✅ Observer / event bus
- 1.6 ✅ Repository layer
- 1.7 ✅ Cache service
- 1.8 ✅ App shell (`main.py`)

## Phase 2 — Finance Tracker
- 2.1 ✅ Transaction list
- 2.2 ✅ Add/Edit modal
- ~~2.3 Category system~~ — removed, seeded defaults + chips only
- ~~2.4 People management~~ — removed, inline in Bill Splits
- ~~2.5 Debt tracker~~ — removed, implicit in bill splits
- 2.6 ✅ Bill splits
- 2.7 ✅ Finance service

## Phase 3 — Investments & Goals
- 3.1 ✅ Investments screen
- 3.2 ✅ Add/Edit investment modal
- 3.3 ✅ Goals screen
- 3.4 ✅ Add goal modal

## Phase 4 — Dashboard (depends on Phase 2 + 3)
- 4.1 ✅ Summary cards
- 4.2 ✅ Recent transactions
- 4.3 ✅ Category chart
- 4.4 ✅ Quick-add FAB

## Phase 5 — Notes Module
- 5.1 ⬜ Notebooks grid
- 5.2 ⬜ Notes list
- 5.3 ⬜ Text note editor
- 5.4 ⬜ Image note
- 5.5 ⬜ Doodle canvas

## Phase 6 — AI Chatbot
- 6.1 ⬜ Gemini service
- 6.2 ⬜ API key config
- 6.3 ⬜ Chat screen

## Phase 7 — Polish & Build
- 7.1 ⬜ Theme
- 7.2 ⬜ Navigation polish
- 7.3 ⬜ APK build
- 7.4 ⬜ Device testing

---

**Rule:** Phases must be completed in order — Phase 4 depends on Phase 2 + 3. Whenever
the plan changes (new feature, schema update, new convention), update this file in the
same turn and confirm the change was made.
