"""Goals screen — Phase 3.3 + 3.4.

2-column grid of savings goal cards with progress bars, color themes, deadline
badges, and Add Funds quick-action. FAB opens the Add/Edit goal modal.

Layer rule: imports only from ``services`` — never from repositories directly.
"""
from __future__ import annotations

from datetime import date

import flet as ft

from models.goal import Goal
from services.goal_service import DEFAULT_GOAL_COLOR, GOAL_COLORS, GoalService


def build(page: ft.Page) -> ft.View:
    """Return the Goals view."""
    svc = GoalService.instance()

    # ── Refreshable grid ─────────────────────────────────────────────
    goals_grid = ft.GridView(
        expand=True,
        runs_count=2,
        max_extent=240,
        child_aspect_ratio=0.82,
        spacing=12,
        run_spacing=12,
        padding=ft.Padding(left=16, right=16, top=16, bottom=88),
    )

    # ── Helpers ───────────────────────────────────────────────────────

    def _hex_to_flet_color(hex_color: str) -> str:
        """Return the hex color string as-is (Flet accepts CSS hex colors)."""
        return hex_color

    def _is_light(hex_color: str) -> bool:
        """Return True if the hex background is perceptually light."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return luminance > 186

    # ── Delete ────────────────────────────────────────────────────────

    def _delete(gid: int) -> None:
        try:
            svc.delete_goal(gid)
        except ValueError:
            pass
        _refresh()

    # ── Refresh ───────────────────────────────────────────────────────

    def _refresh() -> None:
        goals = svc.get_all_goals()
        goals_grid.controls.clear()

        if not goals:
            goals_grid.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.FLAG_OUTLINED,
                                size=56,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "No goals yet.\nTap + to add one.",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=14,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                    col={"xs": 2},
                )
            )
        else:
            for g in goals:
                goals_grid.controls.append(_build_card(g))

        page.update()

    # ── Goal card ─────────────────────────────────────────────────────

    def _build_card(goal: Goal) -> ft.Control:
        bg = goal.color or DEFAULT_GOAL_COLOR
        text_color = ft.Colors.BLACK if _is_light(bg) else ft.Colors.WHITE
        pct = svc.progress_pct(goal)
        pct_dec = pct / 100.0
        completed = pct >= 100.0

        # Deadline badge
        deadline_badge: ft.Control
        if goal.deadline:
            try:
                dl = date.fromisoformat(goal.deadline)
                days_left = (dl - date.today()).days
                if days_left < 0:
                    dl_text = "Overdue"
                    dl_color = ft.Colors.RED_200
                elif days_left == 0:
                    dl_text = "Due today"
                    dl_color = ft.Colors.ORANGE_300
                elif days_left <= 7:
                    dl_text = f"{days_left}d left"
                    dl_color = ft.Colors.ORANGE_200
                else:
                    dl_text = dl.strftime("%d %b %Y")
                    dl_color = ft.Colors.with_opacity(0.25, ft.Colors.WHITE)
            except ValueError:
                dl_text = goal.deadline
                dl_color = ft.Colors.with_opacity(0.25, ft.Colors.WHITE)
            deadline_badge = ft.Container(
                content=ft.Text(dl_text, size=9, color=text_color),
                bgcolor=dl_color,
                border_radius=4,
                padding=ft.Padding(left=6, right=6, top=2, bottom=2),
            )
        else:
            deadline_badge = ft.Container()

        # Category label
        cat_label: ft.Control
        if goal.category:
            cat_label = ft.Text(
                goal.category,
                size=10,
                color=text_color,
                opacity=0.75,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            )
        else:
            cat_label = ft.Container(height=0)

        edit_btn = ft.IconButton(
            icon=ft.Icons.EDIT_OUTLINED,
            icon_size=14,
            icon_color=text_color,
            tooltip="Edit goal",
            on_click=lambda e, g=goal: _open_dialog(g),
        )
        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_size=14,
            icon_color=text_color,
            tooltip="Delete goal",
            on_click=lambda e, gid=goal.id: _delete(gid),
        )
        add_funds_btn = ft.TextButton(
            text="Add funds",
            style=ft.ButtonStyle(color=text_color),
            on_click=lambda e, g=goal: _open_add_funds(g),
        )

        return ft.Container(
            bgcolor=bg,
            border_radius=12,
            padding=ft.Padding(left=12, right=8, top=10, bottom=8),
            content=ft.Column(
                [
                    ft.Row(
                        [cat_label, deadline_badge],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        goal.name,
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=text_color,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=2,
                        expand=True,
                    ),
                    ft.ProgressBar(
                        value=pct_dec,
                        bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.BLACK),
                        color=ft.Colors.WHITE if not _is_light(bg) else "#000000",
                        height=5,
                        border_radius=ft.BorderRadius(
                            top_left=3, top_right=3, bottom_left=3, bottom_right=3
                        ),
                    ),
                    ft.Text(
                        f"\u20b9{goal.current_amount:,.0f}"
                        f" of \u20b9{goal.target_amount:,.0f}"
                        f"  ({pct:.0f}%)",
                        size=10,
                        color=text_color,
                        opacity=0.9,
                    ),
                    ft.Row(
                        [
                            add_funds_btn if not completed else ft.Container(),
                            ft.Row([edit_btn, delete_btn], spacing=0),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=5,
                expand=True,
            ),
        )

    # ── Add Funds dialog ──────────────────────────────────────────────

    def _open_add_funds(goal: Goal) -> None:
        amount_field = ft.TextField(
            label="Amount to Add",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("\u20b9 "),
            autofocus=True,
            border_radius=8,
        )
        error_text = ft.Text("", color=ft.Colors.ERROR, size=12)

        def _close() -> None:
            dlg.open = False
            page.update()

        def _on_dismiss(e: ft.ControlEvent) -> None:
            if dlg in page.overlay:
                page.overlay.remove(dlg)

        def _save() -> None:
            error_text.value = ""
            raw = (amount_field.value or "").replace(",", "").strip()
            try:
                amount = float(raw)
            except ValueError:
                error_text.value = "Enter a valid amount."
                page.update()
                return
            try:
                svc.add_funds(goal.id, amount)
            except ValueError as exc:
                error_text.value = str(exc)
                page.update()
                return
            _close()
            _refresh()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Add funds — {goal.name}"),
            on_dismiss=_on_dismiss,
            content=ft.Container(
                content=ft.Column(
                    [amount_field, error_text],
                    spacing=8,
                ),
                width=320,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close()),
                ft.FilledButton("Add", on_click=lambda e: _save()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Add / Edit dialog ─────────────────────────────────────────────

    def _open_dialog(goal_to_edit: Goal | None = None) -> None:
        is_edit = goal_to_edit is not None
        selected_color: list[str] = [
            (goal_to_edit.color if is_edit else DEFAULT_GOAL_COLOR) or DEFAULT_GOAL_COLOR
        ]

        name_field = ft.TextField(
            label="Goal Name",
            value=goal_to_edit.name if is_edit else "",
            border_radius=8,
            autofocus=True,
            max_length=200,
        )
        category_field = ft.TextField(
            label="Category (optional)",
            value=goal_to_edit.category or "" if is_edit else "",
            border_radius=8,
            max_length=100,
        )
        target_field = ft.TextField(
            label="Target Amount",
            value=str(goal_to_edit.target_amount) if is_edit else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("\u20b9 "),
            border_radius=8,
        )
        current_field = ft.TextField(
            label="Starting Amount",
            value=str(goal_to_edit.current_amount) if is_edit else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("\u20b9 "),
            border_radius=8,
        )
        deadline_field = ft.TextField(
            label="Deadline (optional)",
            value=goal_to_edit.deadline or "" if is_edit else "",
            read_only=True,
            expand=True,
            border_radius=8,
            hint_text="YYYY-MM-DD",
        )
        error_text = ft.Text("", color=ft.Colors.ERROR, size=12)

        # ── Color swatches ────────────────────────────────────────────
        swatch_row = ft.Row(spacing=6, wrap=True)

        def _rebuild_swatches() -> None:
            swatch_row.controls.clear()
            for hex_c in GOAL_COLORS:
                is_selected = selected_color[0] == hex_c
                swatch_row.controls.append(
                    ft.GestureDetector(
                        content=ft.Container(
                            width=28,
                            height=28,
                            bgcolor=hex_c,
                            border_radius=14,
                            border=ft.border.all(
                                3, ft.Colors.ON_SURFACE if is_selected else ft.Colors.TRANSPARENT
                            ),
                        ),
                        on_tap=lambda e, c=hex_c: _pick_color(c),
                    )
                )

        def _pick_color(hex_c: str) -> None:
            selected_color[0] = hex_c
            _rebuild_swatches()
            page.update()

        _rebuild_swatches()

        def _on_date_change(e: ft.ControlEvent) -> None:
            val = e.control.value
            if val:
                iso = (
                    val.strftime("%Y-%m-%d")
                    if hasattr(val, "strftime")
                    else str(val)[:10]
                )
                deadline_field.value = iso
                page.update()

        def _pick_date(e: ft.ControlEvent) -> None:
            dp = ft.DatePicker(on_change=_on_date_change)
            page.overlay.append(dp)
            dp.open = True
            page.update()

        def _close() -> None:
            dlg.open = False
            page.update()

        def _on_dismiss(e: ft.ControlEvent) -> None:
            if dlg in page.overlay:
                page.overlay.remove(dlg)

        def _save() -> None:
            error_text.value = ""

            def _c(raw: str) -> str:
                return (raw or "").replace(",", "").replace("\u20b9", "").strip()

            try:
                t_amt = float(_c(target_field.value) or "0")
                c_amt = float(_c(current_field.value) or "0")
            except ValueError:
                error_text.value = "Enter valid amounts."
                page.update()
                return

            deadline_val = deadline_field.value.strip() or None

            try:
                if is_edit:
                    svc.update_goal(
                        goal_id=goal_to_edit.id,
                        name=name_field.value or "",
                        category=category_field.value or None,
                        target_amount=t_amt,
                        current_amount=c_amt,
                        deadline=deadline_val,
                        color=selected_color[0],
                    )
                else:
                    svc.add_goal(
                        name=name_field.value or "",
                        category=category_field.value or None,
                        target_amount=t_amt,
                        current_amount=c_amt,
                        deadline=deadline_val,
                        color=selected_color[0],
                    )
            except ValueError as exc:
                error_text.value = str(exc)
                page.update()
                return
            _close()
            _refresh()

        dlg = ft.AlertDialog(
            title=ft.Text("Edit Goal" if is_edit else "New Goal"),
            on_dismiss=_on_dismiss,
            content=ft.Container(
                content=ft.Column(
                    [
                        name_field,
                        category_field,
                        target_field,
                        current_field,
                        ft.Row(
                            [
                                deadline_field,
                                ft.IconButton(
                                    icon=ft.Icons.CALENDAR_MONTH,
                                    tooltip="Pick deadline",
                                    on_click=_pick_date,
                                ),
                            ],
                            spacing=4,
                        ),
                        ft.Text("Color", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        swatch_row,
                        error_text,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
                height=460,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close()),
                ft.FilledButton(
                    "Save" if is_edit else "Create",
                    on_click=lambda e: _save(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Initial load ──────────────────────────────────────────────────
    _refresh()

    return ft.View(
        route="/goals",
        padding=0,
        appbar=ft.AppBar(title=ft.Text("Goals"), center_title=False),
        controls=[goals_grid],
        floating_action_button=ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=lambda e: _open_dialog(),
            tooltip="Add goal",
        ),
    )

