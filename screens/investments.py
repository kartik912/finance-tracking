"""Investments screen — Phase 3.1 + 3.2.

Summary bar (total invested / current value / P&L), filter chips by type,
scrollable card list, swipe-to-delete, and an Add/Edit modal.

Layer rule: imports only from ``services`` — never from repositories directly.
"""
from __future__ import annotations

from datetime import date

import flet as ft

from models.investment import Investment
from services.investment_service import INVESTMENT_TYPES


# ── Type badge colours ────────────────────────────────────────────────
_TYPE_COLOR: dict[str, str] = {
    "Stocks":        "#1565C0",
    "Mutual Funds":  "#6A1B9A",
    "Crypto":        "#E65100",
    "Gold":          "#F9A825",
    "Fixed Deposit": "#2E7D32",
    "Other":         "#546E7A",
}


def build(page: ft.Page) -> ft.View:
    """Return the Investments view."""
    from services.investment_service import InvestmentService

    svc = InvestmentService.instance()
    today = date.today()

    state: dict = {"filter": None}  # None = All

    # ── Refreshable controls ──────────────────────────────────────────
    summary_invested = ft.Text("\u20b90", size=16, weight=ft.FontWeight.W_700)
    summary_current  = ft.Text("\u20b90", size=16, weight=ft.FontWeight.W_700)
    summary_pnl      = ft.Text("\u20b90  (0.00%)", size=14, weight=ft.FontWeight.W_600)
    inv_list = ft.ListView(
        expand=True,
        spacing=8,
        padding=ft.Padding(left=16, right=16, top=12, bottom=88),
    )
    filter_chips_row = ft.Row(
        scroll=ft.ScrollMode.AUTO,
        spacing=6,
        controls=[],
    )

    # ── Delete ────────────────────────────────────────────────────────

    def _delete(iid: int) -> None:
        try:
            svc.delete_investment(iid)
        except ValueError:
            pass
        _refresh()

    # ── Refresh ───────────────────────────────────────────────────────

    def _refresh() -> None:
        # Fetch all investments once (single cache read)
        all_investments = svc.get_all_investments(None)
        populated_types = {inv.investment_type for inv in all_investments}

        # If the active filter no longer has data (e.g. last item deleted), reset to All
        if state["filter"] is not None and state["filter"] not in populated_types:
            state["filter"] = None

        # Filtered list for the card section
        investments = (
            all_investments
            if state["filter"] is None
            else [i for i in all_investments if i.investment_type == state["filter"]]
        )

        # Compute summary from the VISIBLE investments so numbers match the cards
        visible_invested = sum(i.amount_invested for i in investments)
        visible_current  = sum(i.current_value   for i in investments)
        visible_pnl      = round(visible_current - visible_invested, 2)
        visible_pnl_pct  = (
            round(visible_pnl / visible_invested * 100, 2)
            if visible_invested > 0 else 0.0
        )
        summary_invested.value = f"\u20b9{visible_invested:,.0f}"
        summary_current.value  = f"\u20b9{visible_current:,.0f}"
        sign = "+" if visible_pnl >= 0 else ""
        summary_pnl.value = f"{sign}\u20b9{visible_pnl:,.0f}  ({sign}{visible_pnl_pct:.2f}%)"
        summary_pnl.color = ft.Colors.GREEN_700 if visible_pnl >= 0 else ft.Colors.RED_700

        # Rebuild filter chips — only show types that have at least one investment
        filter_chips_row.controls.clear()
        chip_labels = ["All"] + [t for t in INVESTMENT_TYPES if t in populated_types]
        for label in chip_labels:
            active = (state["filter"] is None and label == "All") or state["filter"] == label
            chip = ft.Chip(
                label=ft.Text(label, size=12),
                selected=active,
                on_select=lambda e, lbl=label: _set_filter(lbl),
            )
            filter_chips_row.controls.append(chip)

        # Rebuild list
        inv_list.controls.clear()
        if not investments:
            if state["filter"] is None:
                # Truly empty — no data at all
                empty_msg = "Do your first investment"
                empty_sub = "Tap + below to get started"
            else:
                empty_msg = f"No {state['filter']} investments yet"
                empty_sub = "Tap + to add one"
            inv_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.SHOW_CHART,
                                size=56,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                empty_msg,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=15,
                                weight=ft.FontWeight.W_600,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                empty_sub,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=12,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(top=48),
                )
            )
        elif state["filter"] is None:
            # Group by type — only render groups that have data
            from collections import defaultdict
            groups: dict[str, list] = defaultdict(list)
            for inv in investments:
                groups[inv.investment_type].append(inv)
            for type_name in INVESTMENT_TYPES:
                if type_name not in groups:
                    continue
                inv_list.controls.append(_build_group_header(type_name))
                for inv in groups[type_name]:
                    inv_list.controls.append(_build_card(inv))
        else:
            # Filtered view — cards only (chip already shows the type)
            for inv in investments:
                inv_list.controls.append(_build_card(inv))

        page.update()

    def _set_filter(label: str) -> None:
        state["filter"] = None if label == "All" else label
        _refresh()

    # ── Group header ──────────────────────────────────────────────────

    def _build_group_header(type_name: str) -> ft.Control:
        color = _TYPE_COLOR.get(type_name, "#546E7A")
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=10,
                        height=10,
                        bgcolor=color,
                        border_radius=5,
                    ),
                    ft.Text(
                        type_name,
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=4, right=4, top=12, bottom=4),
        )

    # ── Investment card ───────────────────────────────────────────────

    def _build_card(inv: Investment) -> ft.Control:
        pnl     = svc.pnl(inv)
        pnl_pct = svc.pnl_pct(inv)
        is_gain = pnl >= 0
        pnl_color  = ft.Colors.GREEN_700 if is_gain else ft.Colors.RED_700
        pnl_icon   = ft.Icons.ARROW_UPWARD if is_gain else ft.Icons.ARROW_DOWNWARD
        sign       = "+" if is_gain else ""
        badge_color = _TYPE_COLOR.get(inv.investment_type, "#546E7A")

        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            inv.name,
                                            size=15,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                inv.investment_type,
                                                size=10,
                                                color=ft.Colors.WHITE,
                                                weight=ft.FontWeight.W_500,
                                            ),
                                            bgcolor=badge_color,
                                            border_radius=4,
                                            padding=ft.Padding(
                                                left=8, right=8, top=2, bottom=2
                                            ),
                                        ),
                                    ],
                                    spacing=4,
                                    expand=True,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"\u20b9{inv.current_value:,.0f}",
                                            size=15,
                                            weight=ft.FontWeight.W_700,
                                        ),
                                        ft.Row(
                                            [
                                                ft.Icon(
                                                    pnl_icon,
                                                    size=12,
                                                    color=pnl_color,
                                                ),
                                                ft.Text(
                                                    f"{sign}\u20b9{abs(pnl):,.0f}"
                                                    f" ({sign}{pnl_pct:.1f}%)",
                                                    size=11,
                                                    color=pnl_color,
                                                    weight=ft.FontWeight.W_500,
                                                ),
                                            ],
                                            spacing=2,
                                        ),
                                    ],
                                    spacing=2,
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                ),
                            ],
                        ),
                        ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                        ft.Row(
                            [
                                ft.Text(
                                    f"Invested: \u20b9{inv.amount_invested:,.0f}",
                                    size=11,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    expand=True,
                                ),
                                ft.Text(
                                    inv.date,
                                    size=11,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_size=16,
                                    tooltip="Edit",
                                    on_click=lambda e, i=inv: _open_dialog(i),
                                ),
                            ],
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding(left=16, right=8, top=12, bottom=8),
            ),
            elevation=1,
        )

        return ft.Dismissible(
            content=card,
            dismiss_direction=ft.DismissDirection.HORIZONTAL,
            on_dismiss=lambda e, iid=inv.id: _delete(iid),
            background=ft.Container(
                bgcolor=ft.Colors.RED_400,
                alignment=ft.Alignment(-1, 0),
                padding=ft.Padding(left=20),
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
                        ft.Text("Delete", color=ft.Colors.WHITE),
                    ],
                    spacing=6,
                ),
            ),
            secondary_background=ft.Container(
                bgcolor=ft.Colors.RED_400,
                alignment=ft.Alignment(1, 0),
                padding=ft.Padding(right=20),
                content=ft.Row(
                    [
                        ft.Text("Delete", color=ft.Colors.WHITE),
                        ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
                    ],
                    spacing=6,
                ),
            ),
        )

    # ── Add / Edit dialog (Phase 3.2) ─────────────────────────────────

    def _open_dialog(
        inv_to_edit: Investment | None = None,
        preset_type: str | None = None,
    ) -> None:
        is_edit = inv_to_edit is not None
        # Type is locked when adding with a specific filter active (not when editing)
        locked_type = bool(preset_type) and not is_edit

        if is_edit:
            init_type = inv_to_edit.investment_type
        elif preset_type:
            init_type = preset_type
        else:
            init_type = INVESTMENT_TYPES[0]

        selected_type: list[str] = [init_type]  # mutable container for closure

        name_field = ft.TextField(
            label="Investment Name",
            value=inv_to_edit.name if is_edit else "",
            border_radius=8,
            autofocus=not is_edit,
            max_length=200,
        )

        if locked_type:
            badge_color = _TYPE_COLOR.get(init_type, "#546E7A")
            type_control: ft.Control = ft.Container(
                content=ft.Row(
                    [
                        ft.Text("Type:", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Container(
                            content=ft.Text(
                                init_type,
                                size=12,
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.W_500,
                            ),
                            bgcolor=badge_color,
                            border_radius=4,
                            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(top=2, bottom=2),
            )
        else:
            type_dd = ft.Dropdown(
                label="Type",
                options=[ft.DropdownOption(t) for t in INVESTMENT_TYPES],
                value=init_type,
                border_radius=8,
            )
            type_dd.on_change = lambda e: selected_type.__setitem__(
                0, e.control.value or INVESTMENT_TYPES[0]
            )
            type_control = type_dd
        invested_field = ft.TextField(
            label="Amount Invested",
            value=str(inv_to_edit.amount_invested) if is_edit else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("\u20b9 "),
            border_radius=8,
        )
        current_field = ft.TextField(
            label="Current Value",
            value=str(inv_to_edit.current_value) if is_edit else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("\u20b9 "),
            border_radius=8,
        )
        date_field = ft.TextField(
            label="Date",
            value=inv_to_edit.date if is_edit else today.isoformat(),
            read_only=True,
            expand=True,
            border_radius=8,
        )
        pnl_preview = ft.Text("", size=12, weight=ft.FontWeight.W_500)
        error_text  = ft.Text("", color=ft.Colors.ERROR, size=12)

        def _update_pnl(*_: object) -> None:
            try:
                def _c(raw: str) -> float:
                    return float(
                        (raw or "0").replace(",", "").replace("\u20b9", "").strip()
                    )
                pnl = round(_c(current_field.value) - _c(invested_field.value), 2)
                inv_val = _c(invested_field.value)
                sign = "+" if pnl >= 0 else ""
                pct = round(pnl / inv_val * 100, 2) if inv_val > 0 else 0.0
                pnl_preview.value = (
                    f"P&L: {sign}\u20b9{pnl:,.2f}  ({sign}{pct:.2f}%)"
                )
                pnl_preview.color = (
                    ft.Colors.GREEN_700 if pnl >= 0 else ft.Colors.RED_700
                )
            except ValueError:
                pnl_preview.value = ""
            page.update()

        invested_field.on_change = _update_pnl
        current_field.on_change  = _update_pnl

        def _on_date_change(e: ft.ControlEvent) -> None:
            val = e.control.value
            if val:
                iso = (
                    val.strftime("%Y-%m-%d")
                    if hasattr(val, "strftime")
                    else str(val)[:10]
                )
                date_field.value = iso
                page.update()

        def _pick_date(e: ft.ControlEvent) -> None:
            dp = ft.DatePicker(
                value=date.fromisoformat(date_field.value),
                on_change=_on_date_change,
            )
            page.overlay.append(dp)
            dp.open = True
            page.update()

        def _close_dlg() -> None:
            dlg.open = False
            page.update()

        def _on_dismiss(e: ft.ControlEvent) -> None:
            if dlg in page.overlay:
                page.overlay.remove(dlg)

        def _save() -> None:
            error_text.value = ""

            def _c(raw: str) -> str:
                return (raw or "").replace(",", "").replace("\u20b9", "").strip()

            # Read type from dropdown directly (most reliable) or fall back to init_type
            if locked_type:
                inv_type = init_type
            else:
                inv_type = getattr(type_control, "value", None) or init_type

            try:
                if is_edit:
                    svc.update_investment(
                        investment_id=inv_to_edit.id,
                        name=name_field.value or "",
                        investment_type=inv_type,
                        amount_invested=float(_c(invested_field.value) or "0"),
                        current_value=float(_c(current_field.value) or "0"),
                        inv_date=date_field.value,
                    )
                else:
                    svc.add_investment(
                        name=name_field.value or "",
                        investment_type=inv_type,
                        amount_invested=float(_c(invested_field.value) or "0"),
                        current_value=float(_c(current_field.value) or "0"),
                        inv_date=date_field.value,
                    )
            except ValueError as exc:
                error_text.value = str(exc)
                page.update()
                return
            _close_dlg()
            _refresh()

        if is_edit:
            dlg_title = "Edit Investment"
        elif preset_type:
            dlg_title = f"Add {preset_type}"
        else:
            dlg_title = "Add Investment"

        dlg = ft.AlertDialog(
            title=ft.Text(dlg_title),
            on_dismiss=_on_dismiss,
            content=ft.Container(
                content=ft.Column(
                    [
                        name_field,
                        type_control,
                        invested_field,
                        current_field,
                        pnl_preview,
                        ft.Row(
                            [
                                date_field,
                                ft.IconButton(
                                    icon=ft.Icons.CALENDAR_MONTH,
                                    tooltip="Pick date",
                                    on_click=_pick_date,
                                ),
                            ],
                            spacing=4,
                        ),
                        error_text,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
                height=420,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close_dlg()),
                ft.FilledButton(
                    "Save" if is_edit else "Add",
                    on_click=lambda e: _save(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if is_edit:
            _update_pnl()

        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Initial load ──────────────────────────────────────────────────
    _refresh()

    # ── Summary bar ───────────────────────────────────────────────────
    summary_bar = ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Invested", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        summary_invested,
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE_VARIANT),
                ft.Column(
                    [
                        ft.Text("Current", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        summary_current,
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE_VARIANT),
                ft.Column(
                    [
                        ft.Text("P&L", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        summary_pnl,
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
        bgcolor=ft.Colors.SURFACE_CONTAINER,
    )

    return ft.View(
        route="/investments",
        padding=0,
        appbar=ft.AppBar(title=ft.Text("Investments"), center_title=False),
        controls=[
            ft.Column(
                controls=[
                    summary_bar,
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    ft.Container(
                        content=filter_chips_row,
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                    ),
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    inv_list,
                ],
                expand=True,
                spacing=0,
            )
        ],
        floating_action_button=ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=lambda e: _open_dialog(preset_type=state["filter"]),
            tooltip="Add investment",
        ),
    )

