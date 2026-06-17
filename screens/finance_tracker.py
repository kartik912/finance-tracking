"""Finance Tracker screen — Phase 2.1 + 2.2.

Displays transactions for the selected month grouped by date.
Supports month navigation, swipe-to-delete, and an add/edit modal.

Layer rule: this screen only imports from ``services`` — never repositories directly.
"""
from __future__ import annotations

from datetime import date

import flet as ft

from models.transaction import Transaction

_MONTH_NAMES = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December",
]


def build(page: ft.Page) -> ft.View:
    """Return the Finance Tracker view."""
    # Lazy imports — respect the screens -> services layer rule
    from components.transaction_card import build_transaction_card
    from services.finance_service import FinanceService

    svc = FinanceService.instance()
    today = date.today()

    # ── Mutable state stored in a dict so closures can mutate it ─────
    state: dict = {"year": today.year, "month": today.month}

    # ── Refreshable controls ─────────────────────────────────────────
    month_label = ft.Text(
        "", size=16, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER
    )
    income_text = ft.Text(
        "+₹0", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.GREEN_700
    )
    expense_text = ft.Text(
        "-₹0", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.RED_700
    )
    tx_list = ft.ListView(
        expand=True, spacing=0, padding=ft.Padding(bottom=88)
    )

    # ── Helpers ───────────────────────────────────────────────────────

    def _fmt_date_header(date_str: str) -> str:
        try:
            d = date.fromisoformat(date_str)
            if d == today:
                return "Today"
            if (today - d).days == 1:
                return "Yesterday"
            return d.strftime("%d %b %Y")
        except ValueError:
            return date_str

    def _delete_tx(tid: int) -> None:
        try:
            svc.delete_transaction(tid)
        except ValueError:
            pass
        _refresh()

    def _refresh() -> None:
        """Rebuild the transaction list and summary totals."""
        yr, mo = state["year"], state["month"]
        month_label.value = f"{_MONTH_NAMES[mo - 1]} {yr}"

        txs = svc.get_transactions_for_month(yr, mo)
        cats = {c.id: c for c in svc.get_all_categories()}

        income = svc.get_monthly_total(yr, mo, "income")
        expense = svc.get_monthly_total(yr, mo, "expense")
        income_text.value = f"+₹{income:,.0f}"
        expense_text.value = f"-₹{expense:,.0f}"

        tx_list.controls.clear()

        if not txs:
            tx_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.RECEIPT_LONG_OUTLINED,
                                size=56,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "No transactions this month",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=14,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(top=64),
                )
            )
        else:
            grouped: dict[str, list[Transaction]] = {}
            for tx in txs:
                grouped.setdefault(tx.date, []).append(tx)

            for date_str, date_txs in grouped.items():
                tx_list.controls.append(
                    ft.Container(
                        content=ft.Text(
                            _fmt_date_header(date_str),
                            size=11,
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        padding=ft.Padding(left=16, right=16, top=12, bottom=4),
                    )
                )
                for tx in date_txs:
                    cat = cats.get(tx.category_id)
                    card = build_transaction_card(
                        tx, cat, on_edit=lambda t=tx: _open_dialog(t)
                    )
                    tx_list.controls.append(
                        ft.Dismissible(
                            content=card,
                            on_dismiss=lambda e, tid=tx.id: _delete_tx(tid),
                            dismiss_direction=ft.DismissDirection.HORIZONTAL,
                            background=ft.Container(
                                bgcolor=ft.Colors.RED_400,
                                alignment=ft.Alignment(-1, 0),
                                padding=ft.Padding(left=20),
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
                                        ft.Text("Delete", color=ft.Colors.WHITE, size=13),
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
                                        ft.Text("Delete", color=ft.Colors.WHITE, size=13),
                                        ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
                                    ],
                                    spacing=6,
                                ),
                            ),
                        )
                    )

        page.update()

    # ── Month navigation ─────────────────────────────────────────────

    def _prev_month(e: ft.ControlEvent) -> None:
        if state["month"] == 1:
            state["month"] = 12
            state["year"] -= 1
        else:
            state["month"] -= 1
        _refresh()

    def _next_month(e: ft.ControlEvent) -> None:
        if state["month"] == 12:
            state["month"] = 1
            state["year"] += 1
        else:
            state["month"] += 1
        if state["year"] > today.year or (
            state["year"] == today.year and state["month"] > today.month
        ):
            state["year"] = today.year
            state["month"] = today.month
        _refresh()

    # ── Add / Edit dialog (Phase 2.2) ────────────────────────────────

    def _open_dialog(tx_to_edit: Transaction | None = None) -> None:
        """Open the Add/Edit Transaction modal dialog."""
        is_edit = tx_to_edit is not None

        form: dict = {
            "type": tx_to_edit.transaction_type if is_edit else "expense",
            "category_id": tx_to_edit.category_id if is_edit else None,
            "date": tx_to_edit.date if is_edit else today.isoformat(),
        }

        amount_field = ft.TextField(
            label="Amount",
            value=str(tx_to_edit.amount) if is_edit else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("₹ "),
            autofocus=not is_edit,
            border_radius=8,
        )
        desc_field = ft.TextField(
            label="Description (optional)",
            value=(tx_to_edit.description or "") if is_edit else "",
            max_length=500,
            border_radius=8,
        )
        date_field = ft.TextField(
            label="Date",
            value=form["date"],
            read_only=True,
            expand=True,
            border_radius=8,
        )
        error_text = ft.Text("", color=ft.Colors.ERROR, size=12)

        # ── Type toggle ───────────────────────────────────────────────
        def _expense_style(active: bool) -> ft.ButtonStyle:
            return ft.ButtonStyle(
                bgcolor=ft.Colors.RED_100 if active else None,
                color=ft.Colors.RED_700 if active else None,
            )

        def _income_style(active: bool) -> ft.ButtonStyle:
            return ft.ButtonStyle(
                bgcolor=ft.Colors.GREEN_100 if active else None,
                color=ft.Colors.GREEN_700 if active else None,
            )

        expense_btn = ft.Button(
            "Expense",
            icon=ft.Icons.ARROW_DOWNWARD,
            style=_expense_style(form["type"] == "expense"),
            expand=True,
        )
        income_btn = ft.Button(
            "Income",
            icon=ft.Icons.ARROW_UPWARD,
            style=_income_style(form["type"] == "income"),
            expand=True,
        )

        def _set_expense(e: ft.ControlEvent) -> None:
            form["type"] = "expense"
            expense_btn.style = _expense_style(True)
            income_btn.style = _income_style(False)
            page.update()

        def _set_income(e: ft.ControlEvent) -> None:
            form["type"] = "income"
            expense_btn.style = _expense_style(False)
            income_btn.style = _income_style(True)
            page.update()

        expense_btn.on_click = _set_expense
        income_btn.on_click = _set_income

        # ── Category chips ────────────────────────────────────────────
        cats = svc.get_all_categories()
        cat_chips: list[ft.Chip] = []

        def _select_cat(cid: int) -> None:
            form["category_id"] = cid
            for chip in cat_chips:
                chip.selected = chip.data == cid
            page.update()

        for cat in cats:
            chip = ft.Chip(
                label=ft.Text(cat.name, size=12),
                leading=(
                    ft.Icon(cat.icon, size=14, color=cat.color) if cat.icon else None
                ),
                selected=cat.id == form["category_id"],
                data=cat.id,
            )
            chip.on_select = lambda e, cid=cat.id: _select_cat(cid)
            cat_chips.append(chip)

        cat_row = ft.Row(controls=cat_chips, scroll=ft.ScrollMode.AUTO, spacing=6)

        # ── Date picker ───────────────────────────────────────────────
        def _on_date_change(e: ft.ControlEvent) -> None:
            val = e.control.value
            if val:
                iso = val.strftime("%Y-%m-%d") if hasattr(val, "strftime") else str(val)[:10]
                form["date"] = iso
                date_field.value = iso
                page.update()

        def _pick_date(e: ft.ControlEvent) -> None:
            dp = ft.DatePicker(
                value=date.fromisoformat(form["date"]),
                on_change=_on_date_change,
            )
            page.overlay.append(dp)
            dp.open = True
            page.update()

        date_row = ft.Row(
            controls=[
                date_field,
                ft.IconButton(
                    icon=ft.Icons.CALENDAR_MONTH,
                    on_click=_pick_date,
                    tooltip="Pick date",
                ),
            ],
            spacing=4,
        )

        # ── Dialog assembly ───────────────────────────────────────────
        def _close_dlg() -> None:
            dlg.open = False
            page.update()

        def _on_dismiss(e: ft.ControlEvent) -> None:
            if dlg in page.overlay:
                page.overlay.remove(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("Edit Transaction" if is_edit else "Add Transaction"),
            on_dismiss=_on_dismiss,
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row([expense_btn, income_btn], spacing=8),
                        amount_field,
                        desc_field,
                        ft.Text(
                            "Category",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        cat_row,
                        date_row,
                        error_text,
                    ],
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
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

        def _save() -> None:
            error_text.value = ""
            raw = (
                amount_field.value.strip()
                .replace(",", "")
                .replace("₹", "")
                .strip()
            )
            try:
                amount = float(raw)
            except ValueError:
                error_text.value = "Please enter a valid amount."
                page.update()
                return
            try:
                if is_edit:
                    svc.update_transaction(
                        transaction_id=tx_to_edit.id,
                        tx_date=form["date"],
                        amount=amount,
                        category_id=form["category_id"],
                        description=desc_field.value.strip(),
                        transaction_type=form["type"],
                    )
                else:
                    svc.add_transaction(
                        tx_date=form["date"],
                        amount=amount,
                        category_id=form["category_id"],
                        description=desc_field.value.strip(),
                        transaction_type=form["type"],
                    )
            except ValueError as exc:
                error_text.value = str(exc)
                page.update()
                return
            _close_dlg()
            _refresh()

        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Initial load ─────────────────────────────────────────────────
    _refresh()

    # ── Static layout ─────────────────────────────────────────────────
    month_selector = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    on_click=_prev_month,
                    tooltip="Previous month",
                ),
                ft.Container(
                    content=month_label,
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    on_click=_next_month,
                    tooltip="Next month",
                ),
            ],
        ),
        padding=ft.Padding(left=8, right=8, top=4, bottom=4),
    )

    totals_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Income", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            income_text,
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    expand=True,
                    padding=12,
                    bgcolor=ft.Colors.GREEN_100,
                    border_radius=8,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Expenses", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            expense_text,
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    expand=True,
                    padding=12,
                    bgcolor=ft.Colors.RED_100,
                    border_radius=8,
                ),
            ],
            spacing=8,
        ),
        padding=ft.Padding(left=16, right=16, top=8, bottom=8),
    )

    return ft.View(
        route="/finance",
        padding=0,
        appbar=ft.AppBar(title=ft.Text("Finance"), center_title=False),
        controls=[
            ft.Column(
                controls=[
                    month_selector,
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    totals_row,
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    tx_list,
                ],
                expand=True,
                spacing=0,
            )
        ],
        floating_action_button=ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=lambda e: _open_dialog(),
            tooltip="Add transaction",
        ),
    )

