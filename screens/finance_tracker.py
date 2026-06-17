"""Finance Tracker screen — Phase 2.1 + 2.2.





Displays transactions for the selected month grouped by category.


Each category group is expandable/collapsible. Groups only appear when


they have at least one transaction. Supports month navigation,


swipe-to-delete, and an add/edit modal.





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


    from components.transaction_card import build_transaction_card


    from services.finance_service import FinanceService





    svc = FinanceService.instance()


    today = date.today()





    state: dict = {


        "year": today.year,


        "month": today.month,


        # set of category_ids (or None for uncategorised) that are expanded


        "expanded": set(),


    }





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





    def _delete_tx(tid: int) -> None:


        try:


            svc.delete_transaction(tid)


        except ValueError:


            pass


        _refresh()





    def _toggle_group(key: int | None) -> None:


        if key in state["expanded"]:


            state["expanded"].discard(key)


        else:


            state["expanded"].add(key)


        _refresh()





    def _build_category_group(


        cat_id: int | None,


        cat_name: str,


        cat_icon: str | None,


        cat_color: str | None,


        txs: list[Transaction],


    ) -> None:


        """Append a collapsible category group (header + optional rows) to tx_list."""


        is_expanded = cat_id in state["expanded"]


        group_total = sum(t.amount for t in txs)


        tx_type = txs[0].transaction_type if txs else "expense"


        amount_color = ft.Colors.GREEN_700 if tx_type == "income" else ft.Colors.RED_700


        # If mixed types in group, use neutral


        if len({t.transaction_type for t in txs}) > 1:


            amount_color = ft.Colors.ON_SURFACE_VARIANT





        icon_bg = cat_color or "#9E9E9E"





        # ── Group header ──────────────────────────────────────────────


        header = ft.Container(


            content=ft.Row(


                controls=[


                    # Category icon bubble


                    ft.Container(


                        content=ft.Icon(


                            cat_icon or "category",


                            color=ft.Colors.WHITE,


                            size=18,


                        ),


                        bgcolor=icon_bg,


                        border_radius=10,


                        width=38,


                        height=38,


                        alignment=ft.Alignment(0, 0),


                    ),


                    # Name + count


                    ft.Column(


                        controls=[


                            ft.Text(


                                cat_name,


                                size=14,


                                weight=ft.FontWeight.W_600,


                            ),


                            ft.Text(


                                f"{len(txs)} transaction{'s' if len(txs) != 1 else ''}",


                                size=11,


                                color=ft.Colors.ON_SURFACE_VARIANT,


                            ),


                        ],


                        spacing=1,


                        expand=True,


                    ),


                    # Total amount


                    ft.Text(


                        f"₹{group_total:,.0f}",


                        size=14,


                        weight=ft.FontWeight.W_600,


                        color=amount_color,


                    ),


                    # Expand/collapse chevron


                    ft.Icon(


                        ft.Icons.EXPAND_LESS if is_expanded else ft.Icons.EXPAND_MORE,


                        color=ft.Colors.ON_SURFACE_VARIANT,


                        size=20,


                    ),


                ],


                spacing=12,


                vertical_alignment=ft.CrossAxisAlignment.CENTER,


            ),


            padding=ft.Padding(left=16, right=12, top=10, bottom=10),


            bgcolor=ft.Colors.SURFACE_CONTAINER if is_expanded else ft.Colors.SURFACE,


            on_click=lambda e, k=cat_id: _toggle_group(k),


        )


        tx_list.controls.append(header)


        tx_list.controls.append(ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT))





        # ── Transaction rows (only when expanded) ─────────────────────


        if is_expanded:


            from models.category import Category as _Cat


            cat_obj: _Cat | None = None


            for c in svc.get_all_categories():


                if c.id == cat_id:


                    cat_obj = c


                    break





            for tx in txs:


                card = build_transaction_card(


                    tx, cat_obj, on_edit=lambda t=tx: _open_dialog(t)


                )


                tx_list.controls.append(


                    ft.Dismissible(


                        content=ft.Container(


                            content=card,


                            # Indent slightly to visually nest under group header


                            padding=ft.Padding(left=8, right=0, top=0, bottom=0),


                        ),


                        on_dismiss=lambda e, tid=tx.id: _delete_tx(tid),


                        dismiss_direction=ft.DismissDirection.HORIZONTAL,


                        background=ft.Container(


                            bgcolor=ft.Colors.RED_400,


                            alignment=ft.Alignment(-1, 0),


                            padding=ft.Padding(left=28),


                            content=ft.Row(


                                [


                                    ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=18),


                                    ft.Text("Delete", color=ft.Colors.WHITE, size=12),


                                ],


                                spacing=4,


                            ),


                        ),


                        secondary_background=ft.Container(


                            bgcolor=ft.Colors.RED_400,


                            alignment=ft.Alignment(1, 0),


                            padding=ft.Padding(right=28),


                            content=ft.Row(


                                [


                                    ft.Text("Delete", color=ft.Colors.WHITE, size=12),


                                    ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=18),


                                ],


                                spacing=4,


                            ),


                        ),


                    )


                )


            tx_list.controls.append(


                ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT)


            )





    def _refresh() -> None:


        """Rebuild the category-grouped transaction list and summary totals."""


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


            # Group by category_id (preserve insertion order → sort by cat name)


            grouped: dict[int | None, list[Transaction]] = {}


            for tx in txs:


                grouped.setdefault(tx.category_id, []).append(tx)





            # Sort: named categories alphabetically, then uncategorised last


            def _sort_key(cid: int | None) -> tuple:


                if cid is None:


                    return (1, "")


                cat = cats.get(cid)


                return (0, cat.name.lower() if cat else "")





            for cat_id in sorted(grouped.keys(), key=_sort_key):


                cat = cats.get(cat_id) if cat_id is not None else None


                _build_category_group(


                    cat_id=cat_id,


                    cat_name=cat.name if cat else "Uncategorised",


                    cat_icon=cat.icon if cat else None,


                    cat_color=cat.color if cat else None,


                    txs=grouped[cat_id],


                )





        page.update()





    # ── Month navigation ─────────────────────────────────────────────





    def _prev_month(e: ft.ControlEvent) -> None:


        state["expanded"].clear()


        if state["month"] == 1:


            state["month"] = 12


            state["year"] -= 1


        else:


            state["month"] -= 1


        _refresh()





    def _next_month(e: ft.ControlEvent) -> None:


        state["expanded"].clear()


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


        all_cats = svc.get_all_categories()


        cat_chips: list[ft.Chip] = []





        def _select_cat(cid: int) -> None:


            form["category_id"] = cid


            for chip in cat_chips:


                chip.selected = chip.data == cid


            page.update()





        for cat in all_cats:


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


            # Auto-expand the saved transaction's category group


            state["expanded"].add(form["category_id"])


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


        appbar=ft.AppBar(
            title=ft.Text("Finance"),
            center_title=False,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.RECEIPT_LONG,
                    tooltip="Bill Splits",
                    on_click=lambda e: page.run_task(page.push_route, "/splits"),
                ),
            ],
        ),


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





