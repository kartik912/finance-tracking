"""Notes list screen — Phase 5.2 (simplified).

Shows all notes inside a specific notebook.
FAB creates a new unified note immediately and navigates to the editor.
Long-press a note to delete it.
"""
from __future__ import annotations

import flet as ft

from services.note_service import NoteService
from services.notebook_service import NotebookService


def build(page: ft.Page, notebook_id: int) -> ft.View:
    """Build and return the notes-list view for a specific notebook."""
    nb_svc = NotebookService.instance()
    note_svc = NoteService.instance()

    notebook = nb_svc.get_by_id(notebook_id)
    nb_name = notebook.name if notebook else "Notebook"
    nb_emoji = (notebook.emoji or "\U0001f4d3") if notebook else "\U0001f4d3"

    # ------------------------------------------------------------------ #
    # List state
    # ------------------------------------------------------------------ #
    list_col = ft.Column(spacing=8, expand=True)

    empty_hint = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.NOTE_OUTLINED, size=64, color=ft.Colors.OUTLINE),
                ft.Text(
                    "No notes yet",
                    size=16,
                    color=ft.Colors.OUTLINE,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    "Tap + to add your first note",
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

    def _open_note(note_id: int, note_type: str) -> None:
        page.run_task(page.push_route, f"/note_editor/{notebook_id}/{note_id}")

    def _delete_note(note_id: int) -> None:
        def _do_delete(dlg: ft.AlertDialog) -> None:
            note_svc.delete_note(note_id)
            _close_dlg(dlg)
            _refresh()

        dlg = ft.AlertDialog(
            title=ft.Text("Delete note?"),
            content=ft.Text("This note will be permanently deleted."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close_dlg(dlg)),
                ft.FilledButton(
                    "Delete",
                    on_click=lambda e: _do_delete(dlg),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        dlg.on_dismiss = _on_dlg_dismiss(dlg)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _close_dlg(dlg: ft.AlertDialog) -> None:
        dlg.open = False
        page.update()

    def _on_dlg_dismiss(d: ft.AlertDialog):
        def handler(e: ft.ControlEvent) -> None:
            if d in page.overlay:
                page.overlay.remove(d)
            page.update()
        return handler

    def _type_icon(note_type: str) -> str:
        return ft.Icons.ARTICLE_OUTLINED if note_type in ("text", "unified") else ft.Icons.NOTE_OUTLINED

    def _format_date(iso: str) -> str:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%d %b %Y")
        except Exception:
            return iso

    def _refresh() -> None:
        notes = note_svc.get_notes_for_notebook(notebook_id)
        list_col.controls.clear()
        for note in notes:
            preview = (note.content_text or "")[:80]
            if len(note.content_text or "") > 80:
                preview += "..."
            tile = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(_type_icon(note.note_type), size=22, color=ft.Colors.PRIMARY),
                        ft.Column(
                            [
                                ft.Text(
                                    note.title or "Untitled",
                                    size=14,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    preview if preview else f"({note.note_type} note)",
                                    size=12,
                                    color=ft.Colors.OUTLINE,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    _format_date(note.created_at),
                                    size=11,
                                    color=ft.Colors.OUTLINE,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border_radius=12,
                on_click=lambda e, nid=note.id, nt=note.note_type: _open_note(nid, nt),
                on_long_press=lambda e, nid=note.id: _delete_note(nid),
            )
            list_col.controls.append(tile)

        empty_hint.visible = len(notes) == 0
        list_col.visible = len(notes) > 0
        page.update()

    # ------------------------------------------------------------------ #
    # FAB: create a unified note immediately
    # ------------------------------------------------------------------ #
    def _create_note() -> None:
        note = note_svc.create_note(notebook_id, "unified")
        page.run_task(page.push_route, f"/note_editor/{notebook_id}/{note.id}")

    # ------------------------------------------------------------------ #
    # Initial load
    # ------------------------------------------------------------------ #
    _refresh()

    return ft.View(
        route=f"/notes_list/{notebook_id}",
        appbar=ft.AppBar(
            title=ft.Text(f"{nb_emoji} {nb_name}"),
            center_title=False,
            bgcolor=ft.Colors.SURFACE,
        ),
        controls=[
            ft.Stack(
                [
                    ft.Column(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [list_col, empty_hint],
                                    expand=True,
                                ),
                                expand=True,
                                padding=16,
                            ),
                        ],
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    ft.Container(
                        content=ft.FloatingActionButton(
                            icon=ft.Icons.ADD,
                            on_click=lambda e: _create_note(),
                            tooltip="New note",
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
