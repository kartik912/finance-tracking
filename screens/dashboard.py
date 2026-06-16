"""Dashboard screen — Phase 4."""
from __future__ import annotations

import flet as ft


def build(page: ft.Page) -> ft.View:
    """Return the Dashboard view (placeholder — implemented in Phase 4)."""
    return ft.View(
        route="/",
        controls=[
            ft.AppBar(title=ft.Text("Dashboard"), center_title=False),
            ft.Container(
                content=ft.Text("Dashboard — coming in Phase 4", size=16),
                padding=24,
            ),
        ],
    )
