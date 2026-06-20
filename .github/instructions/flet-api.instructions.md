---
applyTo: "**/*.py"
description: >
  Flet 0.85.x API reference for the Finance Tracking App.
  Consult this file whenever writing any Flet UI code — controls, layout,
  dialogs, navigation, theming. Covers all breaking changes from older Flet
  versions (0.21–0.79) so wrong API names are never used.
---

# Flet 0.85.x API Reference

> Flet version in this project: **0.85.3**
> Python: 3.13 · Target: Android (flet build apk) + Desktop dev
>
> ⚠️ If you bump the `flet` version in `requirements.txt`, this entire file needs a
> re-audit before the next commit — these are not stylistic preferences, they're API
> calls that raise at runtime in this specific version.

## Grep List — used verbatim by `scripts/qa_check.ps1` Step 3

Any of these patterns in `screens/`, `components/`, or `main.py` is an automatic QA BLOCK:

| Forbidden pattern | Why |
|---|---|
| `ft.border.all(` | doesn't exist in 0.85.x — see §0 |
| `page.go(` | deprecated, never use — see §8 |
| `page.open(` | doesn't exist — see §4 |
| `page.show_dialog(` | unreliable — see §4 |
| `ft.ElevatedButton(` / `ft.OutlinedButton(` | removed — see §6 |
| `text="` on `TextButton`/`FilledButton` | wrong kwarg, use `content=` or positional — see §6 |
| `name="` on `ft.Icon(` | wrong kwarg, icon name is positional — see §3 |
| `prefix_text=` / `suffix_text=` | removed — see §7 |
| `ScrollMode.DISABLED` | doesn't exist — see §13 |
| `ft.colors.` / `ft.icons.` (lowercase) | deprecated namespace — see §11, §12 |

If this list and the detailed sections below ever disagree, the detailed section wins —
update this table to match.

---

## 0. Border

`ft.border.all()` does **not exist** in 0.85.x. Construct `ft.Border` explicitly:

```python
# ❌ Wrong — raises AttributeError
border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)

# ✅ Correct
border=ft.Border(
    left=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
    top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
    right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
    bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
)
```

---

## 1. Padding


| ❌ Old (removed) | ✅ 0.85.x |
|---|---|
| `ft.padding.only(left=x, top=y)` | `ft.Padding(left=x, top=y, right=0, bottom=0)` |
| `ft.padding.symmetric(horizontal=x, vertical=y)` | `ft.Padding(left=x, right=x, top=y, bottom=y)` |
| `ft.padding.all(x)` | `ft.Padding(left=x, right=x, top=x, bottom=x)` |

`ft.Padding` constructor: `ft.Padding(left=0, top=0, right=0, bottom=0)` — all args optional, default 0.

---

## 2. Alignment

| ❌ Old (removed) | ✅ 0.85.x |
|---|---|
| `ft.alignment.center` | `ft.Alignment(0, 0)` |
| `ft.alignment.center_left` | `ft.Alignment(-1, 0)` |
| `ft.alignment.center_right` | `ft.Alignment(1, 0)` |
| `ft.alignment.top_center` | `ft.Alignment(0, -1)` |
| `ft.alignment.bottom_center` | `ft.Alignment(0, 1)` |
| `ft.alignment.top_left` | `ft.Alignment(-1, -1)` |
| `ft.alignment.top_right` | `ft.Alignment(1, -1)` |
| `ft.alignment.bottom_left` | `ft.Alignment(-1, 1)` |
| `ft.alignment.bottom_right` | `ft.Alignment(1, 1)` |

`ft.Alignment(x, y)` — x/y range from -1.0 to 1.0.

---

## 3. ft.Icon

| ❌ Old | ✅ 0.85.x |
|---|---|
| `ft.Icon(name="settings", color=..., size=...)` | `ft.Icon("settings", color=..., size=...)` |

Icon name is the **first positional argument** — never use `name=` keyword.

```python
# Correct
ft.Icon(ft.Icons.HOME, color=ft.Colors.BLUE, size=24)
ft.Icon("home", color=ft.Colors.BLUE, size=24)

# Wrong — raises TypeError
ft.Icon(name="home", ...)
```

---

## 4. Dialogs (AlertDialog, BottomSheet)

`page.open()`, `page.close()`, and `page.show_dialog()` do **not exist** in 0.85.x (or are unreliable). Always use `page.overlay`:

```python
# Open a dialog
def _close_dlg(dlg: ft.AlertDialog) -> None:
    dlg.open = False
    page.update()
    if dlg in page.overlay:
        page.overlay.remove(dlg)
    page.update()

dlg = ft.AlertDialog(
    title=ft.Text("Title"),
    content=...,
    actions=[
        ft.TextButton("Cancel", on_click=lambda e: _close_dlg(dlg)),
        ft.FilledButton("OK", on_click=lambda e: _save()),
    ],
)

page.overlay.append(dlg)
dlg.open = True
page.update()
```

**Rules:**
- Always `page.overlay.append(dlg)` → `dlg.open = True` → `page.update()` to open
- Always `dlg.open = False` → `page.update()` → `page.overlay.remove(dlg)` → `page.update()` to close
- **Never** call `page.open(dlg)` — raises `AttributeError: 'Page' object has no attribute 'open'`
- **Never** call `page.show_dialog(dlg)` — unreliable across Flet versions
- Define `_close_dlg` **before** creating the dialog (it's referenced in `actions`)

---

## 5. DatePicker

```python
dp = ft.DatePicker(
    value=date.today(),
    on_change=_on_date_change,
)
page.overlay.append(dp)
dp.open = True
page.update()
```

`on_change` receives `e: ft.ControlEvent`; the selected date is `e.control.value` (a `datetime.datetime` object — use `.date()` or `.strftime("%Y-%m-%d")`).

---

## 6. Buttons

| ❌ Deprecated / wrong | ✅ 0.85.x |
|---|---|
| `ft.ElevatedButton(...)` | `ft.Button(...)` |
| `ft.OutlinedButton(...)` | `ft.Button(style=ft.ButtonStyle(side=ft.BorderSide(...)))` |
| `ft.TextButton(text="Label", ...)` | `ft.TextButton(content="Label", ...)` or `ft.TextButton("Label", ...)` |
| `ft.FilledButton(text="Label", ...)` | `ft.FilledButton(content="Label", ...)` or `ft.FilledButton("Label", ...)` |

`ft.TextButton`, `ft.FilledButton`, and `ft.Button` all take `content` as the **first positional argument** — NOT `text=`.

```python
# ✅ Correct
ft.TextButton("Cancel", on_click=lambda e: _close())
ft.TextButton(content="Cancel", on_click=lambda e: _close())
ft.FilledButton("Save", on_click=lambda e: _save())

# ❌ Wrong — raises TypeError
ft.TextButton(text="Cancel", ...)
ft.FilledButton(text="Save", ...)
```

---

## 7. TextField

| ❌ Old kwarg | ✅ 0.85.x replacement |
|---|---|
| `prefix_text="₹ "` | `prefix=ft.Text("₹ ")` |
| `suffix_text="kg"` | `suffix=ft.Text("kg")` |

```python
ft.TextField(
    label="Amount",
    prefix=ft.Text("₹ "),       # ← correct
    keyboard_type=ft.KeyboardType.NUMBER,
    border_radius=8,
)
```

---

## 8. Navigation & Routing

**`page.go()` is deprecated and must NEVER be used.** Use `push_route` instead.

| ❌ Wrong | ✅ 0.85.x |
|---|---|
| `page.go("/finance")` | `page.run_task(page.push_route, "/finance")` (from sync context) |
| `page.go("/finance")` | `await page.push_route("/finance")` (from async context) |

```python
# From a sync on_click / on_tap handler — use run_task:
def _navigate(e: ft.ControlEvent) -> None:
    page.run_task(page.push_route, "/finance")

# From an async handler — await directly:
async def on_change(e: ft.ControlEvent) -> None:
    await page.push_route("/finance")

# Route change handler must be sync (not async) in 0.85.x
def _route_change(e: ft.RouteChangeEvent) -> None:
    ...
page.on_route_change = _route_change

# View pop handler
async def _view_pop(e: ft.ViewPopEvent) -> None:
    if len(page.views) > 1:
        page.views.pop()
        await page.push_route(page.views[-1].route)
    else:
        await page.push_route("/")
```

---

## 9. App Entry Point

```python
# ft.app() is deprecated
# ✅ correct:
async def main(page: ft.Page) -> None:
    ...

if __name__ == "__main__":
    ft.run(main)
```

`main` must be `async def`. `ft.run()` is the replacement for `ft.app()`.

---

## 10. Page Attributes

```python
# app_data_dir may not exist on desktop — always use getattr
app_data = getattr(page, "app_data_dir", None)
db_path = os.path.join(app_data if app_data else "database", "finance.db")
```

---

## 11. Colors

Use `ft.Colors.*` (capital C) — the old `ft.colors.*` namespace still works but is deprecated.

```python
ft.Colors.GREEN_700      # ✅
ft.Colors.RED_400
ft.Colors.ON_SURFACE_VARIANT
ft.Colors.SURFACE
ft.Colors.OUTLINE_VARIANT
ft.Colors.ERROR
ft.Colors.WHITE
```

**Alpha-suffixed colors use an underscore separator:**

| ❌ Wrong (raises DeprecationWarning) | ✅ Correct |
|---|---|
| `ft.Colors.WHITE70` | `ft.Colors.WHITE_70` |
| `ft.Colors.BLACK54` | `ft.Colors.BLACK_54` |
| `ft.Colors.BLACK87` | `ft.Colors.BLACK_87` |

Always separate the alpha number with `_` (e.g. `WHITE_70`, not `WHITE70`).

---

## 12. Icons

Use `ft.Icons.*` (capital I) — the old `ft.icons.*` namespace still works but is deprecated.

```python
ft.Icons.ADD
ft.Icons.DELETE
ft.Icons.CHEVRON_LEFT
ft.Icons.CHEVRON_RIGHT
ft.Icons.CALENDAR_MONTH
ft.Icons.RECEIPT_LONG_OUTLINED
ft.Icons.ARROW_UPWARD
ft.Icons.ARROW_DOWNWARD
```

---

## 13. ScrollMode

```python
ft.ScrollMode.AUTO      # show scrollbar only when needed
ft.ScrollMode.ALWAYS    # always show scrollbar
ft.ScrollMode.HIDDEN    # scrollable but no scrollbar
ft.ScrollMode.ADAPTIVE  # platform-appropriate behaviour
```

`ft.ScrollMode.DISABLED` does **not exist** — raises `AttributeError`. Use `ft.ScrollMode.HIDDEN` when you want scrolling without a visible scrollbar.

Used in: `ft.Row(scroll=ft.ScrollMode.AUTO)`, `ft.Column(scroll=...)`, `ft.ListView`.

---

## 14. Dismissible (swipe-to-delete)

```python
ft.Dismissible(
    content=card_widget,
    dismiss_direction=ft.DismissDirection.HORIZONTAL,
    on_dismiss=lambda e, tid=item.id: _delete(tid),
    background=ft.Container(
        bgcolor=ft.Colors.RED_400,
        alignment=ft.Alignment(-1, 0),          # center_left
        padding=ft.Padding(left=20),
        content=ft.Row([
            ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
            ft.Text("Delete", color=ft.Colors.WHITE),
        ], spacing=6),
    ),
    secondary_background=ft.Container(
        bgcolor=ft.Colors.RED_400,
        alignment=ft.Alignment(1, 0),           # center_right
        padding=ft.Padding(right=20),
        content=ft.Row([
            ft.Text("Delete", color=ft.Colors.WHITE),
            ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
        ], spacing=6),
    ),
)
```

---

## 15. Chip

```python
chip = ft.Chip(
    label=ft.Text("Food", size=12),
    leading=ft.Icon(ft.Icons.RESTAURANT, size=14),
    selected=True,
    data=category_id,           # arbitrary payload, not a Flet prop — use to carry IDs
)
chip.on_select = lambda e, cid=cat.id: _select(cid)
```

Use `on_select` (not `on_click`) for selection state changes.

---

## 16. Bytecode Cache Pitfall

After editing `.py` files, old `.pyc` in `__pycache__` can mask fixes — tracebacks will point to wrong line numbers. Always clear before testing:

```powershell
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
```

---

## 17. ButtonStyle

```python
ft.ButtonStyle(
    bgcolor=ft.Colors.RED_100,
    color=ft.Colors.RED_700,
    # padding, shape, side, overlay_color, elevation, animation_duration also accepted
)
```

Pass `None` for `bgcolor`/`color` to use theme defaults.

---

## 18. AppBar

```python
ft.AppBar(
    title=ft.Text("Screen Title"),
    center_title=False,
    # bgcolor, leading, actions, toolbar_height
)
```

Attach to `ft.View(appbar=...)`, not inside `controls`.

---

## 19. FloatingActionButton

```python
ft.FloatingActionButton(
    icon=ft.Icons.ADD,
    on_click=lambda e: _open_dialog(),
    tooltip="Add item",
)
```

Attach to `ft.View(floating_action_button=...)`.

---

## 20. ft.View

```python
ft.View(
    route="/finance",
    padding=0,                          # or ft.Padding(...)
    appbar=ft.AppBar(...),
    controls=[...],
    floating_action_button=ft.FloatingActionButton(...),
    navigation_bar=nav_bar,             # set on all views for bottom nav to persist
)
```
