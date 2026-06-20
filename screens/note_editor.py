"""Note editor screen — Phase 5.3 (text) + 5.4 (image).

Routes to this screen: /note_editor/{notebook_id}/{note_id}/{note_type}

Behaviour:
- Text notes: title field + full-screen content area, debounced auto-save (500ms).
- Image notes: ``ft.FilePicker`` for gallery, multi-image horizontal strip.
- Doodle notes: DoodleCanvas component; Save button persists the PNG.
"""
from __future__ import annotations

import threading
from pathlib import Path

import flet as ft

from components import doodle_canvas as dc
from services.note_service import NoteService


def build(page: ft.Page, notebook_id: int, note_id: int, note_type: str) -> ft.View:
    """Build and return the note-editor view."""
    svc = NoteService.instance()
    note = svc.get_note_by_id(note_id)

    if note is None:
        # Fallback if note was deleted
        return ft.View(
            route=f"/note_editor/{notebook_id}/{note_id}/{note_type}",
            appbar=ft.AppBar(title=ft.Text("Note not found")),
            controls=[ft.Text("This note no longer exists.")],
        )

    # ------------------------------------------------------------------ #
    # Choose editor by type
    # ------------------------------------------------------------------ #
    if note_type == "text":
        content = _build_text_editor(page, svc, note, note_id)
    elif note_type == "image":
        content = _build_image_editor(page, svc, note_id)
    elif note_type == "doodle":
        content = _build_doodle_editor(page, svc, notebook_id, note_id)
    else:
        content = ft.Text("Unknown note type.")

    return ft.View(
        route=f"/note_editor/{notebook_id}/{note_id}/{note_type}",
        appbar=ft.AppBar(
            title=ft.Text(
                {"text": "Text Note", "image": "Image Note", "doodle": "Doodle"}.get(
                    note_type, "Note"
                )
            ),
            center_title=False,
            bgcolor=ft.Colors.SURFACE,
        ),
        controls=[content],
        padding=0,
        scroll=ft.ScrollMode.AUTO if note_type != "doodle" else ft.ScrollMode.HIDDEN,
    )


# ---------------------------------------------------------------------------
# Text editor (Phase 5.3)
# ---------------------------------------------------------------------------

def _build_text_editor(
    page: ft.Page,
    svc: NoteService,
    note: object,
    note_id: int,
) -> ft.Container:
    """Full-screen text editor with debounced auto-save."""

    _timer: list[threading.Timer | None] = [None]
    saved_indicator = ft.Text("", size=11, color=ft.Colors.OUTLINE)

    title_field = ft.TextField(
        value=getattr(note, "title", "") or "",
        hint_text="Title",
        border=ft.InputBorder.NONE,
        text_size=22,
        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
        max_length=500,
        expand=True,
    )

    content_field = ft.TextField(
        value=getattr(note, "content_text", "") or "",
        hint_text="Start typing...",
        border=ft.InputBorder.NONE,
        multiline=True,
        expand=True,
        min_lines=20,
        text_size=15,
        max_length=50_000,
    )

    def _save_now() -> None:
        try:
            svc.update_note_text(
                note_id,
                title_field.value or "",
                content_field.value or "",
            )
            saved_indicator.value = "Saved"
        except ValueError:
            saved_indicator.value = "Too long"
        saved_indicator.update()

    def _schedule_save(_: ft.ControlEvent) -> None:
        if _timer[0] is not None:
            _timer[0].cancel()
        saved_indicator.value = "..."
        saved_indicator.update()
        _timer[0] = threading.Timer(0.5, _save_now)
        _timer[0].start()

    title_field.on_change = _schedule_save
    content_field.on_change = _schedule_save

    # Toolbar: Bold / Italic / Checklist shortcuts
    def _insert(snippet: str) -> None:
        current = content_field.value or ""
        content_field.value = current + snippet
        content_field.update()
        _schedule_save(None)  # type: ignore[arg-type]

    toolbar = ft.Row(
        [
            ft.IconButton(
                icon=ft.Icons.FORMAT_BOLD,
                tooltip="Bold",
                on_click=lambda e: _insert("**bold**"),
            ),
            ft.IconButton(
                icon=ft.Icons.FORMAT_ITALIC,
                tooltip="Italic",
                on_click=lambda e: _insert("_italic_"),
            ),
            ft.IconButton(
                icon=ft.Icons.CHECKLIST,
                tooltip="Checklist item",
                on_click=lambda e: _insert("\n- [ ] "),
            ),
            ft.Container(expand=True),
            saved_indicator,
        ],
        spacing=4,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(content=toolbar, padding=ft.Padding.symmetric(horizontal=8, vertical=4)),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column(
                        [
                            title_field,
                            ft.Divider(height=1),
                            content_field,
                        ],
                        spacing=0,
                    ),
                    padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Image editor (Phase 5.4)
# ---------------------------------------------------------------------------

def _build_image_editor(
    page: ft.Page,
    svc: NoteService,
    note_id: int,
) -> ft.Container:
    """Displays existing images and allows adding new ones via FilePicker."""

    images_row = ft.Row(
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        height=220,
    )

    def _refresh_images() -> None:
        images_row.controls.clear()
        imgs = svc.get_images_for_note(note_id)
        for img_rec in imgs:
            abs_path = svc.resolve_image_path(img_rec.image_path)
            if Path(abs_path).is_file():
                thumb = ft.Container(
                    content=ft.Stack(
                        [
                            ft.Image(
                                src=abs_path,
                                width=200,
                                height=200,
                                fit=ft.BoxFit.COVER,
                                border_radius=12,
                            ),
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.WHITE,
                                    icon_size=20,
                                    on_click=lambda e, iid=img_rec.id: _delete_img(iid),
                                    tooltip="Remove",
                                ),
                                right=4,
                                top=4,
                            ),
                        ]
                    ),
                    width=200,
                    height=200,
                    border_radius=12,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                )
                images_row.controls.append(thumb)
        if images_row.page:
            images_row.update()

    def _delete_img(image_id: int) -> None:
        svc.delete_image(image_id)
        _refresh_images()

    async def _pick_images(_: ft.ControlEvent) -> None:
        files = await page.run_task(
            file_picker.pick_files,
            dialog_title="Select images",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=True,
        )
        if not files:
            return
        for f in files:
            if f.path:
                try:
                    svc.add_image(note_id, f.path)
                except (ValueError, OSError):
                    pass
        _refresh_images()

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)
    page.update()
    # Populate images_row.controls during build (no .update() call needed yet —
    # the control isn't on the page yet, but controls list is set before render).
    _refresh_images()

    empty_hint = ft.Text(
        "Tap the button below to add images from your gallery.",
        size=14,
        color=ft.Colors.OUTLINE,
        text_align=ft.TextAlign.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.IMAGE_OUTLINED, size=48, color=ft.Colors.OUTLINE),
                            empty_hint,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=24,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(
                    content=images_row,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                ),
                ft.Container(
                    content=ft.ElevatedButton(
                        "Add Images",
                        icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
                        on_click=_pick_images,
                    ),
                    padding=16,
                    alignment=ft.Alignment(0, 0),
                ),
            ],
            spacing=0,
        ),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Doodle editor (Phase 5.5 integration)
# ---------------------------------------------------------------------------

def _build_doodle_editor(
    page: ft.Page,
    svc: NoteService,
    notebook_id: int,
    note_id: int,
) -> ft.Container:
    """Displays existing doodle (if any) or a fresh canvas, then saves as PNG."""

    saved_doodle_img = ft.Container(visible=False)
    canvas_container = ft.Container()

    result_text = ft.Text("", size=12, color=ft.Colors.OUTLINE)

    def _on_doodle_save(png_path: str) -> None:
        """Called by doodle_canvas when user taps Save."""
        try:
            doodle_rec = svc.save_doodle(note_id, png_path)
            # Show saved image
            abs_path = svc.resolve_doodle_path(doodle_rec.doodle_path)
            saved_doodle_img.content = ft.Image(
                src=abs_path,
                width=340,
                height=420,
                fit=ft.BoxFit.CONTAIN,
                border_radius=12,
            )
            saved_doodle_img.visible = True
            canvas_container.visible = False
            result_text.value = "Doodle saved!"
            page.update()
        except (ValueError, OSError) as exc:
            result_text.value = f"Save failed: {exc}"
            page.update()

    def _show_canvas(_: ft.ControlEvent) -> None:
        canvas_container.visible = True
        saved_doodle_img.visible = False
        result_text.value = ""
        page.update()

    canvas_widget = dc.build_doodle_canvas(on_save=_on_doodle_save)
    canvas_container.content = canvas_widget

    # Load existing doodle if there is one
    doodles = svc.get_doodles_for_note(note_id)
    if doodles:
        last = doodles[-1]
        abs_path = svc.resolve_doodle_path(last.doodle_path)
        from pathlib import Path as _Path
        if _Path(abs_path).is_file():
            saved_doodle_img.content = ft.Image(
                src=abs_path,
                width=340,
                height=420,
                fit=ft.BoxFit.CONTAIN,
                border_radius=12,
            )
            saved_doodle_img.visible = True
            canvas_container.visible = False
        else:
            canvas_container.visible = True
    else:
        canvas_container.visible = True

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            saved_doodle_img,
                            canvas_container,
                            result_text,
                            ft.Container(
                                content=ft.TextButton(
                                    "Draw new doodle",
                                    icon=ft.Icons.BRUSH_OUTLINED,
                                    on_click=_show_canvas,
                                ),
                                alignment=ft.Alignment(0, 0),
                            ),
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=16,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        expand=True,
    )
