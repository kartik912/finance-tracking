"""Dashboard screen — Phase 4.

Phase 4.1: Summary cards — horizontally scrollable row.
Phase 4.2: Recent transactions — last 5 with shared TransactionCard, "See all" link.
Phase 4.3: Category donut chart — top 4 spend categories for current month on ft.Canvas.
Phase 4.4: Speed-dial FAB — quick-add expense / income / split from the dashboard.

Refresh strategy: all data-dependent sections live inside _refresh(), which rebuilds
scroll_body.controls. Called on initial build and after every quick-add save, so the
dashboard never shows stale totals.
"""
from __future__ import annotations

import math
from datetime import date

import flet as ft
import flet.canvas as cv

from components.transaction_card import build_transaction_card


# ── Card accent colours ───────────────────────────────────────────────
_SPEND_COLOR  = "#E53935"   # red
_INCOME_COLOR = "#43A047"   # green
_PORTF_COLOR  = "#1E88E5"   # blue
_GOALS_COLOR  = "#8E24AA"   # purple
_ARC_COLORS   = ["#1E88E5", "#E53935", "#43A047", "#FB8C00"]


def build(page: ft.Page) -> ft.View:
    """Return the Dashboard view."""
    from services.finance_service import FinanceService
    from services.goal_service import GoalService
    from services.investment_service import InvestmentService

    fin_svc  = FinanceService.instance()
    inv_svc  = InvestmentService.instance()
    goal_svc = GoalService.instance()

    # ── Scrollable body (rebuilt on every _refresh) ───────────────────
    scroll_body = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )

    # ── Pure UI helpers (no data fetching) ────────────────────────────

    def _summary_card(
        icon: str,
        label: str,
        value: str,
        sub: str,
        accent: str,
        route: str,
    ) -> ft.Control:
        """Return a single tappable summary card."""
        return ft.Container(
            width=168,
            height=118,
            border_radius=16,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border(
                left=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ),
            padding=ft.Padding(left=16, top=14, right=16, bottom=14),
            on_click=lambda e, r=route: page.run_task(page.push_route, r),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=32,
                                height=32,
                                border_radius=8,
                                bgcolor=accent,
                                content=ft.Icon(icon, size=18, color=ft.Colors.WHITE),
                                alignment=ft.Alignment(0, 0),
                            ),
                            ft.Text(
                                label,
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                expand=True,
                                text_align=ft.TextAlign.RIGHT,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(
                        value,
                        size=20,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.ON_SURFACE,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                    ft.Text(
                        sub,
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                ],
                spacing=6,
                expand=True,
            ),
        )

    def _build_donut(breakdown: list) -> ft.Control:
        """Return the donut chart + legend, or an empty-state placeholder."""
        if not breakdown:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.PIE_CHART_OUTLINE,
                            size=40,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "No expense data this month",
                            size=13,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                alignment=ft.Alignment(0, 0),
                padding=ft.Padding(top=16, bottom=16, left=0, right=0),
            )

        total_spend   = sum(amt for _, amt in breakdown)
        size          = 180.0
        cx = cy       = size / 2
        r_outer       = size / 2 - 10
        r_inner       = r_outer * 0.55
        gap_deg       = 2.5
        shapes: list[cv.Shape] = []
        current_angle = -90.0

        for idx, (cat, amt) in enumerate(breakdown):
            pct       = amt / total_spend
            sweep_deg = pct * 360.0 - gap_deg
            color     = _ARC_COLORS[idx % len(_ARC_COLORS)]
            shapes.append(
                cv.Arc(
                    x=cx - r_outer,
                    y=cy - r_outer,
                    width=r_outer * 2,
                    height=r_outer * 2,
                    start_angle=math.radians(current_angle),
                    sweep_angle=math.radians(sweep_deg),
                    use_center=False,
                    paint=ft.Paint(
                        color=color,
                        stroke_width=r_outer - r_inner,
                        style=ft.PaintingStyle.STROKE,
                        stroke_cap=ft.StrokeCap.BUTT,
                    ),
                )
            )
            current_angle += pct * 360.0

        legend_items: list[ft.Control] = [
            ft.Row(
                [
                    ft.Container(
                        width=10, height=10,
                        bgcolor=_ARC_COLORS[i % len(_ARC_COLORS)],
                        border_radius=5,
                    ),
                    ft.Text(
                        cat.name, size=12,
                        color=ft.Colors.ON_SURFACE,
                        expand=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                    ft.Text(
                        f"{round(amt / total_spend * 100, 1)}%",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for i, (cat, amt) in enumerate(breakdown)
        ]

        return ft.Row(
            [
                cv.Canvas(shapes=shapes, width=size, height=size),
                ft.Column(legend_items, spacing=8, expand=True),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        )

    # ── Refresh — rebuilds all data-driven sections ───────────────────

    def _refresh() -> None:
        today       = date.today()
        year, month = today.year, today.month
        month_name  = today.strftime("%b %Y")

        spend  = fin_svc.get_monthly_total(year, month, "expense")
        income = fin_svc.get_monthly_total(year, month, "income")

        inv_summary = inv_svc.get_summary()
        portf_value = inv_summary["total_current"]
        portf_pnl   = inv_summary["pnl"]
        portf_sign  = "+" if portf_pnl >= 0 else ""

        goals = goal_svc.get_all_goals()
        if goals:
            total_target = sum(g.target_amount  for g in goals)
            total_saved  = sum(g.current_amount for g in goals)
            goals_pct    = round(total_saved / total_target * 100, 1) if total_target > 0 else 0.0
            goals_value  = f"\u20b9{total_saved:,.0f}"
            goals_sub    = (
                f"{goals_pct}% of \u20b9{total_target:,.0f}"
                f"  \u00b7  {len(goals)} goal{'s' if len(goals) != 1 else ''}"
            )
        else:
            goals_value = "\u20b90"
            goals_sub   = "No goals yet"

        recent_txs = fin_svc.get_recent_transactions(limit=5)
        all_cats   = {c.id: c for c in fin_svc.get_all_categories()}

        # ─ Cards row ──────────────────────────────────────────────────
        cards_row = ft.Row(
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            height=130,
            controls=[
                _summary_card(
                    ft.Icons.ARROW_DOWNWARD, "Spent this month",
                    f"\u20b9{spend:,.0f}", month_name, _SPEND_COLOR, "/finance",
                ),
                _summary_card(
                    ft.Icons.ARROW_UPWARD, "Earned this month",
                    f"\u20b9{income:,.0f}", month_name, _INCOME_COLOR, "/finance",
                ),
                _summary_card(
                    ft.Icons.SHOW_CHART, "Portfolio value",
                    f"\u20b9{portf_value:,.0f}",
                    f"P&L {portf_sign}\u20b9{abs(portf_pnl):,.0f}",
                    _PORTF_COLOR, "/investments",
                ),
                _summary_card(
                    ft.Icons.FLAG_OUTLINED, "Goals saved",
                    goals_value, goals_sub, _GOALS_COLOR, "/goals",
                ),
            ],
        )

        # ─ Recent transactions ─────────────────────────────────────────
        if recent_txs:
            tx_controls: list[ft.Control] = [
                build_transaction_card(tx, all_cats.get(tx.category_id))
                for tx in recent_txs
            ]
        else:
            tx_controls = [
                ft.Container(
                    content=ft.Text(
                        "No transactions yet",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(top=16, bottom=16, left=0, right=0),
                )
            ]

        recent_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Recent Transactions",
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.ON_SURFACE,
                                expand=True,
                            ),
                            ft.TextButton(
                                "See all",
                                on_click=lambda e: page.run_task(
                                    page.push_route, "/finance"
                                ),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    *tx_controls,
                ],
                spacing=4,
            ),
            padding=ft.Padding(left=16, right=16, top=8, bottom=16),
        )

        # ─ Donut chart ─────────────────────────────────────────────────
        breakdown     = fin_svc.get_category_breakdown(year, month)[:4]
        chart_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Spending by Category",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    _build_donut(breakdown),
                ],
                spacing=12,
            ),
            padding=ft.Padding(left=16, right=16, top=8, bottom=100),
        )

        # ─ Swap body contents ──────────────────────────────────────────
        scroll_body.controls = [
            ft.Container(
                content=cards_row,
                padding=ft.Padding(left=16, right=16, top=16, bottom=8),
            ),
            ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
            recent_section,
            ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
            chart_section,
        ]

        # Only update once the control is mounted on the page.
        try:
            if scroll_body.page:
                scroll_body.update()
        except RuntimeError:
            pass  # initial build — not yet mounted

    # ── Speed-dial FAB (Phase 4.4) ────────────────────────────────────

    dial_open: list[bool] = [False]

    _ACTIONS = [
        ("Expense", ft.Icons.REMOVE, "#E53935", "expense"),
        ("Income",  ft.Icons.ADD,    "#43A047", "income"),
        ("Split",   ft.Icons.RECEIPT_LONG, "#1E88E5", None),
    ]

    mini_fabs:   list[ft.Control] = []
    mini_labels: list[ft.Control] = []

    def _close_dial() -> None:
        dial_open[0] = False
        for c in mini_fabs + mini_labels:
            c.visible = False
        main_icon.name = ft.Icons.ADD
        page.update()

    def _quick_add_tx(tx_type: str) -> None:
        """Open a minimal dialog to add an expense or income transaction."""
        _close_dial()
        cats      = fin_svc.get_all_categories()
        today_str = date.today().isoformat()

        amount_field = ft.TextField(
            label="Amount",
            prefix=ft.Text("\u20b9 "),
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
            border_radius=8,
        )
        desc_field = ft.TextField(
            label="Description (optional)",
            border_radius=8,
            max_length=200,
        )
        cat_options = [ft.DropdownOption(c.name) for c in cats]
        cat_dd = ft.Dropdown(
            label="Category",
            options=cat_options,
            value=cats[0].name if cats else None,
            border_radius=8,
        )
        error_text = ft.Text("", color=ft.Colors.ERROR, size=12)

        def _close() -> None:
            dlg.open = False
            page.update()

        def _on_dismiss(e: ft.ControlEvent) -> None:
            if dlg in page.overlay:
                page.overlay.remove(dlg)
            page.update()

        def _save() -> None:
            error_text.value = ""
            raw = (amount_field.value or "").strip()
            try:
                amount = float(raw)
            except ValueError:
                error_text.value = "Enter a valid amount."
                page.update()
                return
            cat_name = cat_dd.value or ""
            cat_obj  = next((c for c in cats if c.name == cat_name), None)
            try:
                fin_svc.add_transaction(
                    amount=amount,
                    transaction_type=tx_type,
                    category_id=cat_obj.id if cat_obj else None,
                    description=desc_field.value or "",
                    tx_date=today_str,
                )
            except ValueError as exc:
                error_text.value = str(exc)
                page.update()
                return
            _close()
            _refresh()  # update summary cards + recent list + chart

        dlg = ft.AlertDialog(
            title=ft.Text(f"Add {'Expense' if tx_type == 'expense' else 'Income'}"),
            on_dismiss=_on_dismiss,
            content=ft.Container(
                content=ft.Column(
                    [amount_field, cat_dd if cats else ft.Container(), desc_field, error_text],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=360,
                height=280,
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

    def _on_mini_tap(action_label: str, tx_type: str | None) -> None:
        if tx_type is None:
            _close_dial()
            page.run_task(page.push_route, "/splits")
        else:
            _quick_add_tx(tx_type)

    # Build mini FABs (initially hidden)
    for label, icon, color, tx_type in _ACTIONS:
        _lbl = ft.Container(
            content=ft.Text(label, size=12, color=ft.Colors.ON_SURFACE),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=6,
            padding=ft.Padding(left=8, right=8, top=4, bottom=4),
            visible=False,
            shadow=ft.BoxShadow(
                blur_radius=4,
                color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
            ),
        )
        _btn = ft.FloatingActionButton(
            mini=True,
            bgcolor=color,
            content=ft.Icon(icon, color=ft.Colors.WHITE, size=20),
            on_click=lambda e, lbl=label, t=tx_type: _on_mini_tap(lbl, t),
            visible=False,
        )
        mini_labels.append(_lbl)
        mini_fabs.append(_btn)

    def _toggle_dial(e: ft.ControlEvent) -> None:
        dial_open[0] = not dial_open[0]
        for c in mini_fabs + mini_labels:
            c.visible = dial_open[0]
        main_icon.name = ft.Icons.CLOSE if dial_open[0] else ft.Icons.ADD
        page.update()

    main_icon = ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE)
    main_fab  = ft.FloatingActionButton(
        bgcolor=ft.Colors.INDIGO,
        content=main_icon,
        on_click=_toggle_dial,
    )

    def _dial_row(label_ctrl: ft.Control, fab_ctrl: ft.Control) -> ft.Control:
        return ft.Row(
            [label_ctrl, fab_ctrl],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    speed_dial_col = ft.Column(
        [
            _dial_row(mini_labels[2], mini_fabs[2]),
            _dial_row(mini_labels[1], mini_fabs[1]),
            _dial_row(mini_labels[0], mini_fabs[0]),
            main_fab,
        ],
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.END,
    )

    # ── Initial load ──────────────────────────────────────────────────
    _refresh()

    return ft.View(
        route="/",
        padding=0,
        appbar=ft.AppBar(title=ft.Text("Dashboard"), center_title=False),
        controls=[
            ft.Stack(
                [
                    scroll_body,
                    ft.Container(
                        content=speed_dial_col,
                        right=16,
                        bottom=16,
                    ),
                ],
                expand=True,
            ),
        ],
    )