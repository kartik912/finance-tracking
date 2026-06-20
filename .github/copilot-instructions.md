# Finance Tracking App — Global Orientation

This file is always loaded by Copilot Chat. Keep it short — detailed rules live in
scoped instruction files so they don't bloat every request's context.

## What this project is
Personal Android app: **Python + Flet 0.85.3 + SQLAlchemy + SQLite**, layered architecture
(screens → services → repositories → models), built with `flet build apk` on Windows.

## Source of truth
- **PROGRESS.md** — current phase, what's done, what's next. Check before starting work.
- **KNOWN_ISSUES.md** — bugs that already bit us once. Check before writing Flet UI code.
- `.github/instructions/*.instructions.md` — auto-attached rules scoped by file path (`applyTo`).
- `.github/agents/*.agent.md` — personas for Finance App Dev, QA, GitHub Ops.

## Non-negotiables (apply regardless of which agent is active)
1. Never push to GitHub without explicit user confirmation of the exact commit/branch.
2. Never commit `config.json` (real keys), `database/finance.db`, `__pycache__/`, or build artifacts.
3. A feature is "done" only after `scripts/qa_check.ps1` exits 0 — not just "pytest passed."
   That script includes the UI-construction smoke test; plain pytest does not.
4. If you write or touch any `.py` file with Flet UI code, the rules in
   `flet-api.instructions.md` override your training data — that file exists because the
   defaults you'd otherwise guess are wrong for this Flet version.

## Working directory
`C:\Users\KartikYadav\Desktop\personal_projects\finance_tracking_app` — confirm cwd before
running any command.
