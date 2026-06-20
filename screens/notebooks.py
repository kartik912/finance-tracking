"""Notebooks grid screen — Phase 5.1.

Shows a 2-column grid of notebooks with emoji, name, color and note count.
Long-press opens a rename/delete bottom sheet. FAB creates a new notebook.
"""
from __future__ import annotations

import flet as ft

from services.notebook_service import NotebookService

# 8 palette colors for notebook creation
_PALETTE = [
    "#1E88E5", "#43A047", "#E53935", "#FB8C00",
    "#8E24AA", "#00ACC1", "#F4511E", "#6D4C41",
]
_DEFAULT_EMOJIS = [
    "\U0001f4d3", "\U0001f4d5", "\U0001f4d7", "\U0001f4d8",
    "\U0001f4d9", "\u2728", "\U0001f31f", "\U0001f4a1",
]


def build(page: ft.Page) -> ft.View:
    """Build and return the Notebooks grid view."""
    svc = NotebookService.instance()

    # ------------------------------------------------------------------ #
    # Grid state
    # ------------------------------------------------------------------ #
    grid = ft.GridView(
        runs_count=2,
        max_extent=220,
        child_aspect_ratio=1.0,
        spacing=12,
        run_spacing=12,
        expand=True,
    )

    empty_hint = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.BOOK_OUTLINED, size=64, color=ft.Colors.OUTLINE),
                ft.Text(
                    "No notebooks yet",
                    size=16,
                    color=ft.Colors.OUTLINE,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    "Tap + to create your first notebook",
                    size=13,
                    color=ft.Colors.OUTLINE,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.Alignment(0, 0),
        expand=True,
        visible=False,
    )

    def _open_notebook(notebook_id: int) -> None:
        page.run_task(page.push_route, f"/notes_list/{notebook_id}")

    def _refresh() -> None:
        notebooks = svc.get_all()
        grid.controls.clear()
        for nb in notebooks:
            count = svc.get_note_count(nb.id)
            grid.controls.append(_build_card(nb.id, nb.name, nb.emoji or "\U0001f4d3",
                                             nb.color or "#1E88E5", count))
        empty_hint.visible = len(notebooks) == 0
        grid.visible = len(notebooks) > 0
        page.update()

    def _build_card(
        nb_id: int, name: str, emoji: str, color: str, count: int
    ) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(emoji, size=36),
                    ft.Text(
                        name,
                        size=14,
                        weight=ft.FontWeight.W_600,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Text(
                        f"{count} note{'s' if count != 1 else ''}",
                        size=11,
                        color=ft.Colors.WHITE_70,
                    ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=color,
            border_radius=16,
            padding=16,
            alignment=ft.Alignment(0, 0),
            on_click=lambda e, nid=nb_id: _open_notebook(nid),
            on_long_press=lambda e, nid=nb_id, nm=name, em=emoji, cl=color: _show_options(nid, nm, em, cl),
        )

    # ------------------------------------------------------------------ #
    # Create notebook dialog
    # ------------------------------------------------------------------ #
    selected_color: list[str] = [_PALETTE[0]]
    selected_emoji: list[str] = [_DEFAULT_EMOJIS[0]]

    color_row: list[ft.Row] = [None]  # type: ignore[list-item]
    emoji_row: list[ft.Row] = [None]  # type: ignore[list-item]

    def _make_color_row(dlg: ft.AlertDialog) -> ft.Row:
        dots: list[ft.Container] = []
        for c in _PALETTE:
            is_sel = c == selected_color[0]
            dot = ft.Container(
                bgcolor=c,
                width=32,
                height=32,
                border_radius=16,
                border=ft.Border(
                    left=ft.BorderSide(3, ft.Colors.WHITE),
                    top=ft.BorderSide(3, ft.Colors.WHITE),
                    right=ft.BorderSide(3, ft.Colors.WHITE),
                    bottom=ft.BorderSide(3, ft.Colors.WHITE),
                ) if is_sel else None,
                on_click=lambda e, color=c: _select_color(color, dlg),
            )
            dots.append(dot)
        return ft.Row(dots, wrap=True, spacing=8)

    def _make_emoji_row(dlg: ft.AlertDialog) -> ft.Row:
        chips: list[ft.Container] = []
        for em in _DEFAULT_EMOJIS:
            is_sel = em == selected_emoji[0]
            chip = ft.Container(
                content=ft.Text(em, size=22),
                width=44,
                height=44,
                border_radius=22,
                alignment=ft.Alignment(0, 0),
                bgcolor=ft.Colors.SURFACE_CONTAINER if is_sel else ft.Colors.SURFACE,
                on_click=lambda e, emj=em: _select_emoji(emj, dlg),
            )
            chips.append(chip)
        return ft.Row(chips, wrap=True, spacing=6)

    def _select_color(color: str, dlg: ft.AlertDialog) -> None:
        selected_color[0] = color
        color_row[0].controls = _make_color_row(dlg).controls
        page.update()

    def _select_emoji(emj: str, dlg: ft.AlertDialog) -> None:
        selected_emoji[0] = emj
        emoji_row[0].controls = _make_emoji_row(dlg).controls
        page.update()

    def _show_create_dialog() -> None:
        selected_color[0] = _PALETTE[0]
        selected_emoji[0] = _DEFAULT_EMOJIS[0]
        name_field = ft.TextField(label="Notebook name", autofocus=True, max_length=200)
        err_text = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        dlg = ft.AlertDialog(
            title=ft.Text("New Notebook"),
            content=ft.Column(
                [
                    name_field,
                    ft.Text("Emoji", size=12, weight=ft.FontWeight.W_500),
                    ft.Container(height=0),  # placeholder, filled below
                    ft.Text("Color", size=12, weight=ft.FontWeight.W_500),
                    ft.Container(height=0),  # placeholder, filled below
                    err_text,
                ],
                spacing=10,
                tight=True,
                width=300,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close_dlg(dlg)),
                ft.FilledButton("Create", on_click=lambda e: _do_create(dlg, name_field, err_text)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        e_row = _make_emoji_row(dlg)
        c_row = _make_color_row(dlg)
        emoji_row[0] = e_row
        color_row[0] = c_row
        # replace the placeholder containers
        dlg.content.controls[2] = e_row
        dlg.content.controls[4] = c_row

        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _close_dlg(dlg: ft.AlertDialog) -> None:
        dlg.open = False
        page.update()
        if dlg in page.overlay:
            page.overlay.remove(dlg)
        page.update()

    def _do_create(dlg: ft.AlertDialog, name_field: ft.TextField, err_text: ft.Text) -> None:
        name = name_field.value or ""
        try:
            svc.add_notebook(name, selected_color[0], selected_emoji[0])
        except ValueError as exc:
            err_text.value = str(exc)
            err_text.visible = True
            page.update()
            return
        dlg.open = False
        page.update()
        if dlg in page.overlay:
            page.overlay.remove(dlg)
        page.update()
        _refresh()

    # ------------------------------------------------------------------ #
    # Options sheet (rename / delete)
    # ------------------------------------------------------------------ #
    def _show_options(nb_id: int, name: str, emoji: str, color: str) -> None:
        def _do_rename(dlg: ft.AlertDialog, field: ft.TextField, err: ft.Text) -> None:
            new_name = field.value or ""
            try:
                svc.update_notebook(nb_id, new_name, color=color, emoji=emoji)
            except ValueError as exc:
                err.value = str(exc)
                err.visible = True
                page.update()
                return
            _close_dlg(dlg)
            _refresh()

        def _do_delete(confirm_dlg: ft.AlertDialog) -> None:
            svc.delete_notebook(nb_id)
            _close_dlg(confirm_dlg)
            _refresh()

        def _show_delete_confirm(options_dlg: ft.AlertDialog) -> None:
            _close_dlg(options_dlg)
            confirm_dlg = ft.AlertDialog(
                title=ft.Text("Delete notebook?"),
                content=ft.Text(
                    f'"{name}" and all its notes will be permanently deleted.'
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: _close_dlg(confirm_dlg)),
                    ft.FilledButton(
                        "Delete",
                        on_click=lambda e: _do_delete(confirm_dlg),
                        style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(confirm_dlg)
            confirm_dlg.open = True
            page.update()

        field = ft.TextField(label="Rename notebook", value=name, max_length=200, autofocus=True)
        err = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        options_dlg = ft.AlertDialog(
            title=ft.Text(f"{emoji} {name}"),
            content=ft.Column([field, err], spacing=8, tight=True, width=280),
            actions=[
                ft.TextButton("Delete", on_click=lambda e: _show_delete_confirm(options_dlg),
                              style=ft.ButtonStyle(color=ft.Colors.ERROR)),
                ft.TextButton("Cancel", on_click=lambda e: _close_dlg(options_dlg)),
                ft.FilledButton("Save", on_click=lambda e: _do_rename(options_dlg, field, err)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(options_dlg)
        options_dlg.open = True
        page.update()

    # ------------------------------------------------------------------ #
    # Initial load
    # ------------------------------------------------------------------ #
    _refresh()

    return ft.View(
        route="/notes",
        appbar=ft.AppBar(
            title=ft.Text("Notebooks"),
            center_title=False,
            bgcolor=ft.Colors.SURFACE,
        ),
        controls=[
            ft.Stack(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Container(content=grid, expand=True, padding=ft.Padding.all(16)),
                                empty_hint,
                            ],
                            expand=True,
                        ),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.FloatingActionButton(
                            icon=ft.Icons.ADD,
                            on_click=lambda e: _show_create_dialog(),
                            tooltip="New notebook",
                        ),
                        right=16,
                        bottom=16,
                    ),
                ],
                expand=True,
            )
        ],
        padding=0,
    )
