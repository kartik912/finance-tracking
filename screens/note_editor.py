"""Unified note editor — write and draw on the same surface.

Route: /note_editor/{notebook_id}/{note_id}

Layout
------
  AppBar  [title]                           [draw/write toggle]
  ─────────────────────────────────────────────────────────────
  [B] [I] [U̲]                   …  [saved]  ← format bar (write mode)
  [●●●  colours  ●●●] [○○ sizes] [clear]   ← draw bar   (draw mode)
  ─────────────────────────────────────────────────────────────
  ft.Stack (expand)
    ├─ text layer  (title, date, content — Calibri)
    └─ transparent canvas overlay (visible only in draw mode)

The canvas has no background colour so text stays visible while drawing
directly on top of it — OneNote style.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime

import flet as ft
import flet.canvas as cv

from services.note_service import NoteService

# ── drawing constants ────────────────────────────────────────────────────────
_PALETTE: list[str] = [
    "#F44336",  # red
    "#212121",  # near-black
    "#2196F3",  # blue
    "#4CAF50",  # green
    "#FF9800",  # orange
    "#9C27B0",  # purple
    "#795548",  # brown
    "#FFFFFF",  # white
]
_PEN_SIZES: list[int] = [3, 6, 14]


def apply_text_format(
    text: str,
    start: int,
    end: int,
    open_tag: str,
    close_tag: str,
    placeholder: str,
) -> str:
    """Return *text* with formatting tags applied.

    Rules
    -----
    * ``0 <= start < end``  →  wrap ``text[start:end]`` between the tags.
    * otherwise             →  insert ``open_tag + placeholder + close_tag``
                               at position *start* (or appended if start < 0).

    This is a pure function — no Flet dependency — so it can be unit-tested
    without a running page.
    """
    if 0 <= start < end:
        return text[:start] + open_tag + text[start:end] + close_tag + text[end:]
    pos = start if start >= 0 else len(text)
    return text[:pos] + open_tag + placeholder + close_tag + text[pos:]


def parse_markdown_spans(text: str) -> list[ft.TextSpan]:
    """Convert **bold**, _italic_, <u>underline</u> markers into a TextSpan list.

    This is a pure function — no Flet page required — so it can be unit-tested
    directly alongside apply_text_format.
    """
    spans: list[ft.TextSpan] = []
    pattern = r"(\*\*(.*?)\*\*|_(.*?)_|<u>(.*?)</u>)"
    last_end = 0
    for match in re.finditer(pattern, text, re.DOTALL):
        start, end = match.span()
        if start > last_end:
            spans.append(ft.TextSpan(text[last_end:start]))
        bold_content = match.group(2)
        italic_content = match.group(3)
        underline_content = match.group(4)
        if bold_content is not None:
            spans.append(ft.TextSpan(bold_content, ft.TextStyle(weight=ft.FontWeight.BOLD)))
        elif italic_content is not None:
            spans.append(ft.TextSpan(italic_content, ft.TextStyle(italic=True)))
        elif underline_content is not None:
            spans.append(ft.TextSpan(underline_content, ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)))
        last_end = end
    if last_end < len(text):
        spans.append(ft.TextSpan(text[last_end:]))
    return spans if spans else [ft.TextSpan(text)]


def build(
    page: ft.Page,
    notebook_id: int,
    note_id: int,
    note_type: str = "unified",
) -> ft.View:
    """Build and return the unified note-editor view."""
    svc = NoteService.instance()
    note = svc.get_note_by_id(note_id)

    if note is None:
        return ft.View(
            route=f"/note_editor/{notebook_id}/{note_id}",
            appbar=ft.AppBar(title=ft.Text("Note not found")),
            controls=[ft.Text("This note no longer exists.")],
        )

    # ------------------------------------------------------------------ #
    # Shared state
    # ------------------------------------------------------------------ #
    mode: list[str] = ["write"]                       # "write" | "draw"
    _timer: list[threading.Timer | None] = [None]

    # Drawing state — inline so the canvas can be truly transparent
    _shapes: list[cv.Line] = []
    _last_x: list[float | None] = [None]
    _last_y: list[float | None] = [None]
    _draw_color: list[str] = [_PALETTE[0]]
    _draw_size: list[float] = [float(_PEN_SIZES[0])]
    _preview: list[bool] = [False]            # write=edit, True=preview
    # Selection saved on TextField blur — tapping a B/I/U button unfocuses
    # the field before on_click fires, so we capture here and use it there.
    _saved_selection: list[tuple[int, int]] = [(-1, -1)]

    # Load any previously saved strokes
    if note.content_strokes:
        try:
            for d in json.loads(note.content_strokes):
                _shapes.append(
                    cv.Line(
                        x1=d["x1"], y1=d["y1"], x2=d["x2"], y2=d["y2"],
                        paint=ft.Paint(
                            color=d["color"],
                            stroke_width=d["size"],
                            style=ft.PaintingStyle.STROKE,
                            stroke_cap=ft.StrokeCap.ROUND,
                        ),
                    )
                )
        except Exception:  # noqa: BLE001
            pass  # corrupt stroke data — start fresh

    # ------------------------------------------------------------------ #
    # Text fields — Calibri font
    # ------------------------------------------------------------------ #
    saved_label = ft.Text("", size=11, color=ft.Colors.OUTLINE)

    title_field = ft.TextField(
        value=note.title or "",
        hint_text="Title",
        border=ft.InputBorder.NONE,
        text_size=24,
        text_style=ft.TextStyle(
            weight=ft.FontWeight.BOLD,
            font_family="Calibri",
        ),
        max_length=500,
        expand=True,
    )

    # ------------------------------------------------------------------ #
    # Auto-save (debounced 500 ms)
    # ------------------------------------------------------------------ #
    def _save_text_now() -> None:
        try:
            svc.update_note_text(
                note_id,
                title_field.value or "",
                content_field.value or "",
            )
            saved_label.value = "Saved"
        except ValueError:
            saved_label.value = "Too long"
        try:
            if saved_label.page:
                saved_label.update()
        except RuntimeError:
            pass

    def _save_strokes_now() -> None:
        """Serialise _shapes to JSON and persist to the DB."""
        try:
            data = [
                {
                    "x1": s.x1, "y1": s.y1, "x2": s.x2, "y2": s.y2,
                    "color": s.paint.color,
                    "size": s.paint.stroke_width,
                }
                for s in _shapes
            ]
            svc.update_note_strokes(note_id, json.dumps(data))
        except Exception:  # noqa: BLE001
            pass  # don't interrupt the drawing experience on DB error

    def _schedule_save(_: ft.ControlEvent | None) -> None:
        if _timer[0] is not None:
            _timer[0].cancel()
        saved_label.value = "\u2026"
        try:
            if saved_label.page:
                saved_label.update()
        except RuntimeError:
            pass
        _timer[0] = threading.Timer(0.5, _save_text_now)
        _timer[0].start()

    def _capture_selection(e: ft.ControlEvent) -> None:  # noqa: ARG001
        """Keep _saved_selection in sync with the live text selection.

        Wired to on_selection_change so the offsets are captured while the
        selection is still active — on_blur fires after Flutter clears it,
        which caused the 'world**bold**' bug (selection always read as empty).
        """
        try:
            sel = content_field.selection
            lo = min(sel.base_offset, sel.extent_offset)
            hi = max(sel.base_offset, sel.extent_offset)
            _saved_selection[0] = (lo, hi)
        except Exception:  # noqa: BLE001
            _saved_selection[0] = (-1, -1)

    content_field = ft.TextField(
        value=note.content_text or "",
        hint_text="Start writing\u2026",
        border=ft.InputBorder.NONE,
        multiline=True,
        min_lines=18,
        text_size=16,
        text_style=ft.TextStyle(font_family="Calibri"),
        max_length=50_000,
        expand=True,
        on_change=_schedule_save,
        on_selection_change=_capture_selection,
    )

    # Preview layer — renders rich text visually
    content_richtext = ft.Text(
        spans=[],
        expand=True,
    )
    content_preview_wrap = ft.Container(
        content=content_richtext,
        expand=True,
        visible=False,  # shown only in preview mode
    )
    # Tapping the rendered area exits preview and returns to the TextField.
    # Must also be invisible in edit mode so it doesn't block TextField touches.
    content_preview_gesture = ft.GestureDetector(
        content=content_preview_wrap,
        on_tap=lambda e: _exit_preview(),
        expand=True,
        visible=False,
    )

    title_field.on_change = _schedule_save

    # ------------------------------------------------------------------ #
    # Preview helpers — entered automatically after B/I/U; exited on tap
    # ------------------------------------------------------------------ #
    def _enter_preview() -> None:
        """Render content as RichText. Tap the content area to edit again."""
        if _preview[0]:
            return
        _preview[0] = True
        
        text = content_field.value or ""
        content_richtext.spans = parse_markdown_spans(text)

        content_field.visible = False
        content_preview_wrap.visible = True
        content_preview_gesture.visible = True
        try:
            if content_field.page:
                page.update()
        except RuntimeError:
            pass

    def _exit_preview() -> None:
        """Return to raw-text edit mode (TextField)."""
        if not _preview[0]:
            return
        _preview[0] = False
        _saved_selection[0] = (-1, -1)   # stale — user must re-select in edit mode
        content_field.visible = True
        content_preview_wrap.visible = False
        content_preview_gesture.visible = False
        # Reset the eye button icon whenever preview is exited (button tap OR
        # tapping the preview area via the GestureDetector).
        try:
            preview_btn.icon = ft.Icons.VISIBILITY_OUTLINED
            preview_btn.tooltip = "Preview formatted text"
            if preview_btn.page:
                preview_btn.update()
        except Exception:  # noqa: BLE001
            pass  # preview_btn may not exist yet during initial build
        try:
            if content_field.page:
                page.update()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ #
    # Preview toggle button — declared before format_bar so _toggle_preview
    # can reference it; on_click is wired via lambda (late binding).
    # ------------------------------------------------------------------ #
    preview_btn = ft.IconButton(
        ft.Icons.VISIBILITY_OUTLINED,
        tooltip="Preview formatted text",
        on_click=lambda e: _toggle_preview(),
    )

    def _toggle_preview() -> None:
        """Switch between edit mode (raw markers) and preview (rendered)."""
        if _preview[0]:
            _exit_preview()  # also resets preview_btn icon
        else:
            _enter_preview()
            preview_btn.icon = ft.Icons.EDIT_OUTLINED
            preview_btn.tooltip = "Back to editing"
            try:
                if preview_btn.page:
                    preview_btn.update()
            except RuntimeError:
                pass

    # ------------------------------------------------------------------ #
    # Format bar — B / I / U insert markers; eye button toggles preview
    # ------------------------------------------------------------------ #
    def _apply_format(open_tag: str, close_tag: str, placeholder: str) -> None:
        """Wrap selected text with *open_tag*/*close_tag* and stay in edit mode.

        If currently in preview mode, drops back to edit mode first so the
        user can re-select text before clicking B/I/U again.
        """
        if _preview[0]:
            _exit_preview()
            return
        text = content_field.value or ""
        start, end = _saved_selection[0]
        _saved_selection[0] = (-1, -1)  # consume — reset after each use
        content_field.value = apply_text_format(
            text, start, end, open_tag, close_tag, placeholder
        )
        try:
            if content_field.page:
                content_field.update()
        except RuntimeError:
            pass
        _schedule_save(None)
        # Stay in edit mode — **text** / _text_ markers remain visible.
        # Tap the eye button to render the preview.

    format_bar = ft.Row(
        [
            ft.IconButton(
                ft.Icons.FORMAT_BOLD,
                tooltip="Bold \u2014 select text, then tap",
                on_click=lambda e: _apply_format("**", "**", "bold"),
            ),
            ft.IconButton(
                ft.Icons.FORMAT_ITALIC,
                tooltip="Italic \u2014 select text, then tap",
                on_click=lambda e: _apply_format("_", "_", "italic"),
            ),
            ft.IconButton(
                ft.Icons.FORMAT_UNDERLINED,
                tooltip="Underline \u2014 select text, then tap",
                on_click=lambda e: _apply_format("<u>", "</u>", "underline"),
            ),
            ft.VerticalDivider(width=1),
            preview_btn,
            ft.Container(expand=True),
            saved_label,
        ],
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ------------------------------------------------------------------ #
    # Transparent canvas overlay
    # No bgcolor on the parent Container → text layer shows through
    # ------------------------------------------------------------------ #
    _canvas = cv.Canvas(shapes=_shapes, expand=True)

    def _pan_start(e: ft.DragStartEvent) -> None:
        # DragStartEvent has no local_position in Flet 0.85.x — reset
        # so the first pan_update only anchors, never draws a lone dot.
        _last_x[0] = None
        _last_y[0] = None

    def _pan_update(e: ft.DragUpdateEvent) -> None:
        x2: float = e.local_position.x
        y2: float = e.local_position.y
        if _last_x[0] is not None and _last_y[0] is not None:
            _shapes.append(
                cv.Line(
                    x1=_last_x[0],
                    y1=_last_y[0],
                    x2=x2,
                    y2=y2,
                    paint=ft.Paint(
                        color=_draw_color[0],
                        stroke_width=_draw_size[0],
                        style=ft.PaintingStyle.STROKE,
                        stroke_cap=ft.StrokeCap.ROUND,
                    ),
                )
            )
            try:
                if _canvas.page:
                    _canvas.update()
            except RuntimeError:
                pass
        _last_x[0] = x2
        _last_y[0] = y2

    def _pan_end(e: ft.DragEndEvent) -> None:
        _last_x[0] = None
        _last_y[0] = None
        _save_strokes_now()  # persist each completed stroke immediately

    # canvas_layer is ALWAYS visible so strokes persist when in write mode.
    # gesture_catcher is a transparent overlay that intercepts touch only in
    # draw mode — hiding it gives text fields back their input focus.
    canvas_layer = ft.Container(content=_canvas, expand=True)
    gesture_catcher = ft.GestureDetector(
        content=ft.Container(expand=True),  # transparent — no canvas here
        on_pan_start=_pan_start,
        on_pan_update=_pan_update,
        on_pan_end=_pan_end,
        drag_interval=8,
        expand=True,
        visible=False,  # shown only in draw mode
    )

    # ------------------------------------------------------------------ #
    # Draw toolbar — colour palette + size selector + clear
    # ------------------------------------------------------------------ #
    # Forward-declare so _refresh_draw_bar can reference them
    _color_row: ft.Row
    _size_row: ft.Row

    def _color_dot(c: str) -> ft.Container:
        selected = c == _draw_color[0]
        return ft.Container(
            bgcolor=c,
            width=22,
            height=22,
            border_radius=11,
            border=ft.Border(
                left=ft.BorderSide(2, ft.Colors.PRIMARY),
                top=ft.BorderSide(2, ft.Colors.PRIMARY),
                right=ft.BorderSide(2, ft.Colors.PRIMARY),
                bottom=ft.BorderSide(2, ft.Colors.PRIMARY),
            )
            if selected
            else None,
            on_click=lambda e, col=c: _set_color(col),
        )

    def _size_dot(s: int) -> ft.Container:
        selected = s == int(_draw_size[0])
        dim = min(s * 3, 28)
        return ft.Container(
            bgcolor=ft.Colors.ON_SURFACE,
            width=dim,
            height=dim,
            border_radius=dim // 2,
            border=ft.Border(
                left=ft.BorderSide(2, ft.Colors.PRIMARY),
                top=ft.BorderSide(2, ft.Colors.PRIMARY),
                right=ft.BorderSide(2, ft.Colors.PRIMARY),
                bottom=ft.BorderSide(2, ft.Colors.PRIMARY),
            )
            if selected
            else None,
            on_click=lambda e, sz=s: _set_size(sz),
        )

    def _refresh_draw_bar() -> None:
        _color_row.controls = [_color_dot(c) for c in _PALETTE]
        _size_row.controls = [_size_dot(s) for s in _PEN_SIZES]
        try:
            if _color_row.page:
                _color_row.update()
                _size_row.update()
        except RuntimeError:
            pass

    def _set_color(c: str) -> None:
        _draw_color[0] = c
        _refresh_draw_bar()

    def _set_size(s: int) -> None:
        _draw_size[0] = float(s)
        _refresh_draw_bar()

    def _clear_canvas() -> None:
        _shapes.clear()
        try:
            if _canvas.page:
                _canvas.update()
        except RuntimeError:
            pass

    _color_row = ft.Row(
        controls=[_color_dot(c) for c in _PALETTE],
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
    )
    _size_row = ft.Row(
        controls=[_size_dot(s) for s in _PEN_SIZES],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    draw_bar = ft.Row(
        [
            _color_row,
            ft.VerticalDivider(width=1),
            _size_row,
            ft.Container(expand=True),
            ft.IconButton(
                ft.Icons.DELETE_SWEEP_OUTLINED,
                tooltip="Clear drawing",
                on_click=lambda e: _clear_canvas(),
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        visible=False,
    )

    # ------------------------------------------------------------------ #
    # Mode toggle (AppBar action)
    # ------------------------------------------------------------------ #
    mode_btn = ft.IconButton(
        icon=ft.Icons.BRUSH_OUTLINED,
        tooltip="Draw mode",
    )

    def _toggle_mode(e: ft.ControlEvent) -> None:
        if mode[0] == "write":
            if _timer[0] is not None:
                _timer[0].cancel()
            _save_text_now()
            mode[0] = "draw"
            gesture_catcher.visible = True   # enable touch capture
            format_bar.visible = False
            draw_bar.visible = True
            mode_btn.icon = ft.Icons.EDIT_OUTLINED
            mode_btn.tooltip = "Write mode"
        else:
            mode[0] = "write"
            _save_strokes_now()          # persist doodles before releasing keyboard
            gesture_catcher.visible = False  # release touch to text fields
            format_bar.visible = True
            draw_bar.visible = False
            mode_btn.icon = ft.Icons.BRUSH_OUTLINED
            mode_btn.tooltip = "Draw mode"
            _exit_preview()              # always land in TextField after leaving draw
            # canvas_layer stays visible — strokes are preserved
        try:
            if mode_btn.page:
                mode_btn.update()
        except RuntimeError:
            pass
        page.update()

    mode_btn.on_click = _toggle_mode

    # ------------------------------------------------------------------ #
    # Date / time display
    # ------------------------------------------------------------------ #
    _created = note.created_at
    if isinstance(_created, str):
        try:
            _created = datetime.fromisoformat(_created)
        except ValueError:
            _created = datetime.now()
    dt = _created or datetime.now()
    date_str = f"{dt.day} {dt.strftime('%B %Y')}   {dt.strftime('%H:%M')}"

    # ------------------------------------------------------------------ #
    # Main stack: text layer (bottom) + transparent canvas (top)
    # ------------------------------------------------------------------ #
    text_layer = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=title_field,
                    padding=ft.Padding(left=16, top=8, right=16, bottom=0),
                ),
                ft.Container(
                    content=ft.Text(
                        date_str,
                        size=12,
                        color=ft.Colors.OUTLINE,
                        font_family="Calibri",
                    ),
                    padding=ft.Padding(left=16, top=2, right=16, bottom=4),
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Stack(
                        [content_field, content_preview_gesture],
                        expand=True,
                    ),
                    padding=ft.Padding(left=16, top=8, right=16, bottom=16),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
        expand=True,
    )

    main_stack = ft.Stack(
        # canvas_layer is bottom (strokes visible but non-interactive).
        # text_layer is middle (text fields receive focus in write mode).
        # gesture_catcher is top and only shown in draw mode — when visible
        # it intercepts all touches for drawing; when hidden it lets
        # text_layer below it handle focus normally.
        controls=[canvas_layer, text_layer, gesture_catcher],
        expand=True,
    )

    # ------------------------------------------------------------------ #
    # View assembly
    # ------------------------------------------------------------------ #
    display_title = (note.title or "Untitled")[:40]

    return ft.View(
        route=f"/note_editor/{notebook_id}/{note_id}",
        appbar=ft.AppBar(
            title=ft.Text(display_title),
            center_title=False,
            bgcolor=ft.Colors.SURFACE,
            actions=[mode_btn],
        ),
        controls=[
            ft.Column(
                [
                    ft.Container(
                        content=format_bar,
                        padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                    ),
                    ft.Container(
                        content=draw_bar,
                        padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                    ),
                    ft.Divider(height=1),
                    main_stack,
                ],
                spacing=0,
                expand=True,
            )
        ],
        padding=0,
    )
