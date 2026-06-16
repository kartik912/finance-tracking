"""Finance Tracker screen — Phase 2."""
from __future__ import annotations

import flet as ft


def build(page: ft.Page) -> ft.View:
    """Return the Finance Tracker view (placeholder — implemented in Phase 2)."""
    return ft.View(
        route="/finance",
        controls=[
            ft.AppBar(title=ft.Text("Finance"), center_title=False),
            ft.Container(
                content=ft.Text("Finance Tracker — coming in Phase 2", size=16),
                padding=24,
            ),
        ],
    )
