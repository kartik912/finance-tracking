"""Reusable TransactionCard component for the Finance Tracker screen.

Usage::

    from components.transaction_card import build_transaction_card

    card = build_transaction_card(tx, cat, on_edit=lambda t: ...)
"""
from __future__ import annotations

from typing import Callable

import flet as ft

from models.category import Category
from models.transaction import Transaction


def build_transaction_card(
    tx: Transaction,
    cat: Category | None,
    on_edit: Callable[[Transaction], None] | None = None,
) -> ft.Control:
    """Return a single-row transaction card ready for use inside a ListView.

    Parameters
    ----------
    tx:
        The :class:`~models.transaction.Transaction` to display.
    cat:
        The matching :class:`~models.category.Category`, or ``None`` if the
        category has been deleted.
    on_edit:
        Optional callback invoked when the row is tapped.  Receives *tx*.
    """
    icon_name: str = (cat.icon or "category") if cat else "category"
    icon_bg: str = (cat.color or "#9E9E9E") if cat else "#9E9E9E"
    cat_name: str = (cat.name or "Uncategorised") if cat else "Uncategorised"

    is_income = tx.transaction_type == "income"
    amount_color = ft.Colors.GREEN_700 if is_income else ft.Colors.RED_700
    amount_str = f"{'+'  if is_income else '-'}₹{tx.amount:,.0f}"
    desc_text = tx.description if tx.description else cat_name

    return ft.Container(
        content=ft.Row(
            controls=[
                # ── Category icon bubble ──────────────────────────────
                ft.Container(
                    content=ft.Icon(icon_name, color=ft.Colors.WHITE, size=20),
                    bgcolor=icon_bg,
                    border_radius=12,
                    width=44,
                    height=44,
                    alignment=ft.Alignment(0, 0),
                ),
                # ── Description + category label ──────────────────────
                ft.Column(
                    controls=[
                        ft.Text(
                            desc_text,
                            size=14,
                            weight=ft.FontWeight.W_500,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            cat_name,
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=1,
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
                # ── Amount ────────────────────────────────────────────
                ft.Text(
                    amount_str,
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=amount_color,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
        on_click=(lambda e: on_edit(tx)) if on_edit else None,
        bgcolor=ft.Colors.SURFACE,
    )
