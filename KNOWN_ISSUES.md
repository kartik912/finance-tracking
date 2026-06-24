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

| 2026-06-20 | `RuntimeError: Control must be added to the page first` in `_refresh_images` | `control.page` raises `RuntimeError` in Flet 0.85.x when control isn't mounted yet — can't use as an if-guard during build | Wrap in `try/except RuntimeError` | `note_editor.py` `_refresh_images` |
| 2026-06-20 | `TypeError: object Future can't be used in 'await' expression` in `_pick_images` | `page.run_task()` returns `concurrent.futures.Future`, not a coroutine — cannot be `await`ed | In `async def` handlers call coroutine methods directly: `await file_picker.pick_files(...)` | `note_editor.py` `_pick_images` |
| 2026-06-20 | `RuntimeError: TimeoutException … Timeout waiting for invoke method listener for FilePicker` | `page.update()` called inside `_build_image_editor()` before route_change's `page.views.clear()+append+update()` — the second full-page update unmounts the FilePicker Flutter widget on the Dart side | Remove the premature `page.update()` from `_build_image_editor()`; let the route_change's own final `page.update()` batch-send the overlay append and the view together | `note_editor.py` `_build_image_editor` |
| 2026-06-20 | `AttributeError: 'DragStartEvent' object has no attribute 'local_x'` in `_on_pan_start` | Flet 0.85.x pan events use `e.local_position.x`/`e.local_position.y` (`Offset` object), not `e.local_x`/`e.local_y` | Use `e.local_position.x` and `e.local_position.y` on both `DragStartEvent` and `DragUpdateEvent` | `doodle_canvas.py` `_on_pan_start`/`_on_pan_update` |
| 2026-06-23 | `AlertDialog` does not close on Cancel or after Create | Calling `page.overlay.remove(dlg)` inside `_close_dlg` (synchronously, inside a button `on_click`) races with Flutter's dismiss animation — the overlay removal cancels the animation before it completes, leaving the dialog visually frozen open. The correct pattern (from `dashboard.py`): `_close_dlg` ONLY sets `dlg.open = False; page.update()`. Each dialog has `on_dismiss=_on_dlg_dismiss(dlg)` where that handler removes from overlay after Flutter fires the dismiss callback. | `screens/notebooks.py`, `screens/notes_list.py` `_close_dlg`; rule now in `flet-api.instructions.md` §4 |

| 2026-06-24 | `NameError: name 'get_bus' is not defined` in `ChatMessageRepository.clear_all()` | `get_bus` called at line 51 of `chat_message_repository.py` but only `Events` is imported from `observers.event_bus` — `get_bus` was omitted from the import | Add `get_bus` to the import: `from observers.event_bus import Events, get_bus` | `tests/test_chat_message_repository.py::TestClearAll` |

## How to add an entry
```
| 2026-06-21 | <what broke / error message> | <why> | <the fix> | <which file/check now catches it> |
```

If a bug slipped past `qa_check.ps1` entirely (not a Flet API issue, not a layer
violation, not a missing test) — note that explicitly here too, and consider whether
`qa_check.ps1` needs a new step rather than just a new test.