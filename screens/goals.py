"""Goals screen — Phase 3."""
from __future__ import annotations

import flet as ft


def build(page: ft.Page) -> ft.View:
    """Return the Goals view (placeholder — implemented in Phase 3)."""
    return ft.View(
        route="/goals",
        controls=[
            ft.AppBar(title=ft.Text("Goals"), center_title=False),
            ft.Container(
                content=ft.Text("Goals — coming in Phase 3", size=16),
                padding=24,
            ),
        ],
    )
