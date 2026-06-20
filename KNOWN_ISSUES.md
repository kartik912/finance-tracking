# Known Issues & Resolved Gotchas

A running log of bugs that already bit this project once, root-caused, and fixed —
so the same mistake doesn't get reintroduced next session or by a fresh context window.

**Rule for the QA Agent:** when you find a bug whose root cause is a pattern not yet
covered in `flet-api.instructions.md` or `architecture.instructions.md`, fix/report it
first, then append a one-line entry here AND add the pattern to the grep list at the top
of `flet-api.instructions.md` if it's a Flet API issue. Keep entries short — this is a
lookup table, not a story.

| Date | Symptom | Root Cause | Fix | Where it's now enforced |
|---|---|---|---|---|
| (seed) | `AttributeError: module 'flet.border' has no attribute 'all'` | Flet 0.85 removed `ft.border.all()` | Use `ft.Border(left=..., top=..., right=..., bottom=...)` explicitly | `flet-api.instructions.md` §0, grep check |
| (seed) | `AttributeError: 'Page' object has no attribute 'go'` | `page.go()` deprecated in 0.85 | Use `page.run_task(page.push_route, ...)` or `await page.push_route(...)` | `flet-api.instructions.md` §8, grep check |
| (seed) | `AttributeError: 'Page' object has no attribute 'open'` | `page.open()`/`page.show_dialog()` don't exist/are unreliable in 0.85 | Use `page.overlay.append(dlg)` → `dlg.open = True` → `page.update()` | `flet-api.instructions.md` §4, grep check |
| (seed) | `TypeError: __init__() got an unexpected keyword argument 'text'` | `TextButton`/`FilledButton` take `content` (or positional), not `text=` | Use `ft.FilledButton("Save", ...)` | `flet-api.instructions.md` §6, grep check |

## How to add an entry
```
| 2026-06-21 | <what broke / error message> | <why> | <the fix> | <which file/check now catches it> |
```

If a bug slipped past `qa_check.ps1` entirely (not a Flet API issue, not a layer
violation, not a missing test) — note that explicitly here too, and consider whether
`qa_check.ps1` needs a new step rather than just a new test.
