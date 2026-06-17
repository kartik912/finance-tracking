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

`page.open()` and `page.close()` do **not exist** in 0.85.x. Use `page.overlay`:

```python
# Open a dialog
def _close_dlg() -> None:
    dlg.open = False
    page.update()

def _on_dismiss(e: ft.ControlEvent) -> None:
    if dlg in page.overlay:
        page.overlay.remove(dlg)

dlg = ft.AlertDialog(
    title=ft.Text("Title"),
    on_dismiss=_on_dismiss,   # ← fires after close animation; remove from overlay here
    content=...,
    actions=[
        ft.TextButton("Cancel", on_click=lambda e: _close_dlg()),
        ft.FilledButton("OK", on_click=lambda e: _save()),
    ],
)

page.overlay.append(dlg)
dlg.open = True
page.update()
```

**Rules:**
- `_close_dlg` must be defined **before** `dlg` (referenced in actions)
- Only set `dlg.open = False` + `page.update()` to close — do NOT remove from overlay here
- Remove from overlay only in `on_dismiss` (fires after the animation completes)
- Never call `page.overlay.remove(dlg)` before `page.update()` — it tears the control mid-animation and Flet ignores the close

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

| ❌ Deprecated (since 0.80, removed in 1.0) | ✅ 0.85.x replacement |
|---|---|
| `ft.ElevatedButton(...)` | `ft.Button(...)` |
| `ft.OutlinedButton(...)` | `ft.Button(style=ft.ButtonStyle(side=ft.BorderSide(...)))` |

`ft.TextButton` and `ft.FilledButton` still work in 0.85.x.

```python
# Type toggle example
ft.Button(
    "Expense",
    icon=ft.Icons.ARROW_DOWNWARD,
    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_100, color=ft.Colors.RED_700),
    expand=True,
    on_click=_set_expense,
)
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

```python
# page.go() is deprecated — use push_route (must be awaited)
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
```

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
