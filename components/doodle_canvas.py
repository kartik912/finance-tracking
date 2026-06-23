"""Doodle canvas component — OneNote-style.

Provides ``DoodleBoard``: a self-contained drawing widget with variable pen
sizes, variable eraser sizes, 8 pen colours, and PNG export via Pillow.

Usage::

    board = DoodleBoard()
    # board.widget  — the Flet control tree to embed in a View
    # board.export_png()  — returns abs path of a temp PNG (or None)
    # board.clear()  — wipes all strokes
    # board.has_content()  — True if any strokes exist
"""
from __future__ import annotations

import tempfile

import flet as ft
import flet.canvas as cv

# ---------------------------------------------------------------------------
# Drawing constants
# ---------------------------------------------------------------------------
_PALETTE: list[str] = [
    "#212121",  # near-black (default)
    "#F44336",  # red
    "#2196F3",  # blue
    "#4CAF50",  # green
    "#FF9800",  # orange
    "#9C27B0",  # purple
    "#795548",  # brown
    "#FFFFFF",  # white
]
_PEN_SIZES: list[int] = [2, 5, 10, 20, 40]
_ERASER_SIZES: list[int] = [15, 30, 60, 90]

# Canvas logical pixel dimensions
_CANVAS_W = 380
_CANVAS_H = 560

# Background colour used both on screen and in the exported PNG
_CANVAS_BG_HEX = "#FAFAFA"
_CANVAS_BG_RGB = (250, 250, 250)


class DoodleBoard:
    """Manages the doodle canvas widget and all drawing state.

    Attributes:
        widget: The Flet control tree to embed in a ``ft.View``.
    """

    def __init__(self) -> None:
        self._shapes: list[cv.Line] = []
        self._last_x: float | None = None
        self._last_y: float | None = None
        self._color: str = _PALETTE[0]
        self._pen_size: int = _PEN_SIZES[1]     # 5 px
        self._eraser_size: int = _ERASER_SIZES[1]  # 30 px
        self._is_eraser: bool = False

        self._canvas = cv.Canvas(
            shapes=self._shapes,
            width=_CANVAS_W,
            height=_CANVAS_H,
        )
        self._color_row = ft.Row(
            controls=[self._make_color_dot(c) for c in _PALETTE],
            spacing=6,
            wrap=False,
            scroll=ft.ScrollMode.AUTO,
        )
        sizes = _PEN_SIZES  # pen is default mode
        self._size_row = ft.Row(
            controls=[self._make_size_dot(s) for s in sizes],
            spacing=8,
            wrap=False,
            scroll=ft.ScrollMode.AUTO,
        )

        self.widget = self._build_widget()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Wipe all strokes from the canvas."""
        self._shapes.clear()
        try:
            if self._canvas.page:
                self._canvas.update()
        except RuntimeError:
            pass  # Canvas not yet added to a page — safe to ignore

    def has_content(self) -> bool:
        """Return True if at least one stroke has been drawn."""
        return len(self._shapes) > 0

    def export_png(self) -> str | None:
        """Render all strokes to a PNG and return the absolute temp-file path.

        Returns ``None`` if Pillow is not installed.
        """
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return None

        img = Image.new("RGB", (_CANVAS_W, _CANVAS_H), color=_CANVAS_BG_RGB)
        draw = ImageDraw.Draw(img)
        for shape in self._shapes:
            if isinstance(shape, cv.Line) and shape.paint:
                r, g, b = _hex_to_rgb(shape.paint.color or "#000000")
                width = max(1, int(shape.paint.stroke_width or 1))
                draw.line(
                    [(shape.x1, shape.y1), (shape.x2, shape.y2)],
                    fill=(r, g, b),
                    width=width,
                )

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        img.save(tmp.name)
        return tmp.name

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_widget(self) -> ft.Column:
        gesture = ft.GestureDetector(
            content=ft.Container(
                content=self._canvas,
                bgcolor=_CANVAS_BG_HEX,
                border_radius=8,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                width=_CANVAS_W,
                height=_CANVAS_H,
            ),
            on_pan_start=self._on_pan_start,
            on_pan_update=self._on_pan_update,
            on_pan_end=self._on_pan_end,
            drag_interval=8,
        )

        pen_btn = ft.IconButton(
            icon=ft.Icons.EDIT_OUTLINED,
            tooltip="Pen",
            selected=True,
            selected_icon=ft.Icons.EDIT,
            on_click=self._pick_pen,
        )
        eraser_btn = ft.IconButton(
            icon=ft.Icons.AUTO_FIX_NORMAL,
            tooltip="Eraser",
            on_click=self._pick_eraser,
        )
        clear_btn = ft.IconButton(
            icon=ft.Icons.DELETE_SWEEP_OUTLINED,
            tooltip="Clear canvas",
            on_click=lambda e: self.clear(),
        )

        self._pen_btn = pen_btn
        self._eraser_btn = eraser_btn

        toolbar = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Colour:", size=12, color=ft.Colors.OUTLINE),
                        self._color_row,
                        ft.Container(expand=True),
                        pen_btn,
                        eraser_btn,
                        clear_btn,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.Text("Size:", size=12, color=ft.Colors.OUTLINE),
                        self._size_row,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
            ],
            spacing=4,
        )

        return ft.Column(
            [
                ft.Container(
                    content=gesture,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Divider(height=1),
                ft.Container(content=toolbar, padding=ft.Padding.symmetric(horizontal=12, vertical=6)),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # ------------------------------------------------------------------
    # Toolbar state management
    # ------------------------------------------------------------------

    def _refresh_toolbar(self) -> None:
        """Rebuild toolbar rows to reflect current selection (only when on a page)."""
        self._color_row.controls = [self._make_color_dot(c) for c in _PALETTE]
        sizes = _ERASER_SIZES if self._is_eraser else _PEN_SIZES
        self._size_row.controls = [self._make_size_dot(s) for s in sizes]
        try:
            if self._color_row.page:
                self._color_row.update()
                self._size_row.update()
        except RuntimeError:
            pass

    def _make_color_dot(self, color: str) -> ft.Container:
        selected = (color == self._color) and not self._is_eraser
        border = ft.Border(
            left=ft.BorderSide(2, ft.Colors.PRIMARY),
            top=ft.BorderSide(2, ft.Colors.PRIMARY),
            right=ft.BorderSide(2, ft.Colors.PRIMARY),
            bottom=ft.BorderSide(2, ft.Colors.PRIMARY),
        ) if selected else None
        return ft.Container(
            bgcolor=color,
            width=26,
            height=26,
            border_radius=13,
            border=border,
            on_click=lambda e, c=color: self._pick_color(c),
        )

    def _make_size_dot(self, size: int) -> ft.Container:
        if self._is_eraser:
            selected = size == self._eraser_size
        else:
            selected = size == self._pen_size
        dim = min(size * 2, 48)  # cap display size
        return ft.Container(
            bgcolor=ft.Colors.ON_SURFACE if not self._is_eraser else ft.Colors.OUTLINE,
            width=dim,
            height=dim,
            border_radius=dim // 2,
            border=ft.Border(
                left=ft.BorderSide(2, ft.Colors.PRIMARY),
                top=ft.BorderSide(2, ft.Colors.PRIMARY),
                right=ft.BorderSide(2, ft.Colors.PRIMARY),
                bottom=ft.BorderSide(2, ft.Colors.PRIMARY),
            ) if selected else None,
            on_click=lambda e, s=size: self._pick_size(s),
        )

    def _pick_color(self, color: str) -> None:
        self._color = color
        self._is_eraser = False
        self._sync_mode_buttons()
        self._refresh_toolbar()

    def _pick_size(self, size: int) -> None:
        if self._is_eraser:
            self._eraser_size = size
        else:
            self._pen_size = size
        self._refresh_toolbar()

    def _pick_pen(self, e: ft.ControlEvent) -> None:
        self._is_eraser = False
        self._sync_mode_buttons()
        self._refresh_toolbar()

    def _pick_eraser(self, e: ft.ControlEvent) -> None:
        self._is_eraser = True
        self._sync_mode_buttons()
        self._refresh_toolbar()

    def _sync_mode_buttons(self) -> None:
        if not hasattr(self, "_pen_btn"):
            return
        self._pen_btn.icon = ft.Icons.EDIT if not self._is_eraser else ft.Icons.EDIT_OUTLINED
        self._eraser_btn.icon = ft.Icons.AUTO_FIX_HIGH if self._is_eraser else ft.Icons.AUTO_FIX_NORMAL
        try:
            if self._pen_btn.page:
                self._pen_btn.update()
            if self._eraser_btn.page:
                self._eraser_btn.update()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------
    # Pan gesture handlers
    # ------------------------------------------------------------------

    def _on_pan_start(self, e: ft.DragStartEvent) -> None:
        # DragStartEvent has no position in Flet 0.85.x — reset to let
        # the first pan_update set the initial point without drawing a line.
        self._last_x = None
        self._last_y = None

    def _on_pan_update(self, e: ft.DragUpdateEvent) -> None:
        x2: float = e.local_position.x
        y2: float = e.local_position.y
        if self._last_x is not None and self._last_y is not None:
            color = _CANVAS_BG_HEX if self._is_eraser else self._color
            size = float(self._eraser_size if self._is_eraser else self._pen_size)
            self._shapes.append(cv.Line(
                x1=self._last_x, y1=self._last_y,
                x2=x2, y2=y2,
                paint=ft.Paint(
                    color=color,
                    stroke_width=size,
                    style=ft.PaintingStyle.STROKE,
                    stroke_cap=ft.StrokeCap.ROUND,
                ),
            ))
            try:
                if self._canvas.page:
                    self._canvas.update()
            except RuntimeError:
                pass
        self._last_x = x2
        self._last_y = y2

    def _on_pan_end(self, e: ft.DragEndEvent) -> None:
        self._last_x = None
        self._last_y = None


# ---------------------------------------------------------------------------
# Legacy functional wrapper kept for any callers that used the old API
# ---------------------------------------------------------------------------

def build_doodle_canvas(
    on_save=None,  # type: ignore[no-untyped-def]
) -> ft.Column:
    """Deprecated wrapper — use ``DoodleBoard`` directly."""
    board = DoodleBoard()
    return board.widget  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a CSS hex color string to an (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
