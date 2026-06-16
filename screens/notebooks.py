"""Notebooks screen — Phase 5."""
from __future__ import annotations

import flet as ft


def build(page: ft.Page) -> ft.View:
    """Return the Notebooks view (placeholder — implemented in Phase 5)."""
    return ft.View(
        route="/notes",
        controls=[
            ft.AppBar(title=ft.Text("Notes"), center_title=False),
            ft.Container(
                content=ft.Text("Notes — coming in Phase 5", size=16),
                padding=24,
            ),
        ],
    )
