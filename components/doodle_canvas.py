"""Doodle canvas component — Phase 5.5.

A drawing surface built with ``ft.GestureDetector`` + ``flet.canvas.Canvas``.
Draws ``cv.Line`` segments on pan events. Toolbar: 8 colors, 3 brush sizes,
eraser, and clear. Export to PNG via Pillow.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

import flet as ft
import flet.canvas as cv

# 8 drawing colours
PALETTE = [
    "#212121",  # near-black
    "#F44336",  # red
    "#2196F3",  # blue
    "#4CAF50",  # green
    "#FF9800",  # orange
    "#9C27B0",  # purple
    "#FFFFFF",  # white (eraser colour when bg is dark)
    "#795548",  # brown
]

BRUSH_SIZES = [3, 7, 14]

# Doodle canvas dimensions (logical pixels)
CANVAS_W = 340
CANVAS_H = 420


def build_doodle_canvas(
    on_save: Callable[[str], None],
) -> ft.Column:
    """Return a Column containing the doodle canvas and its toolbar.

    Args:
        on_save: Called with the absolute path of the exported PNG after
                 the user taps the Save button.
    """

    # ------------------------------------------------------------------ #
    # Mutable drawing state (lists used as mutable cells)
    # ------------------------------------------------------------------ #
    current_color: list[str] = [PALETTE[0]]
    current_size: list[float] = [float(BRUSH_SIZES[0])]
    is_eraser: list[bool] = [False]
    last_x: list[float | None] = [None]
    last_y: list[float | None] = [None]

    # All drawn shapes
    shapes: list[cv.Line] = []

    canvas = cv.Canvas(
        shapes=shapes,
        width=CANVAS_W,
        height=CANVAS_H,
    )

    # ------------------------------------------------------------------ #
    # Pan handlers
    # ------------------------------------------------------------------ #
    def _on_pan_start(e: ft.DragStartEvent) -> None:
        last_x[0] = e.local_x
        last_y[0] = e.local_y

    def _on_pan_update(e: ft.DragUpdateEvent) -> None:
        x1 = last_x[0]
        y1 = last_y[0]
        if x1 is None or y1 is None:
            return
        x2 = e.local_x
        y2 = e.local_y
        color = "#F5F5F5" if is_eraser[0] else current_color[0]
        line = cv.Line(
            x1=x1, y1=y1, x2=x2, y2=y2,
            paint=ft.Paint(
                color=color,
                stroke_width=current_size[0] * (4 if is_eraser[0] else 1),
                style=ft.PaintingStyle.STROKE,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        )
        canvas.shapes.append(line)
        canvas.update()
        last_x[0] = x2
        last_y[0] = y2

    def _on_pan_end(e: ft.DragEndEvent) -> None:
        last_x[0] = None
        last_y[0] = None

    gesture = ft.GestureDetector(
        content=ft.Container(
            content=canvas,
            bgcolor=ft.Colors.GREY_100,
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            width=CANVAS_W,
            height=CANVAS_H,
        ),
        on_pan_start=_on_pan_start,
        on_pan_update=_on_pan_update,
        on_pan_end=_on_pan_end,
        drag_interval=10,
    )

    # ------------------------------------------------------------------ #
    # Toolbar state widgets (refs updated on selection)
    # ------------------------------------------------------------------ #
    color_dots: list[ft.Container] = []
    size_dots: list[ft.Container] = []

    def _color_dot(color: str) -> ft.Container:
        selected = color == current_color[0] and not is_eraser[0]
        return ft.Container(
            bgcolor=color,
            width=28,
            height=28,
            border_radius=14,
            border=ft.Border(
                left=ft.BorderSide(2, ft.Colors.PRIMARY),
                top=ft.BorderSide(2, ft.Colors.PRIMARY),
                right=ft.BorderSide(2, ft.Colors.PRIMARY),
                bottom=ft.BorderSide(2, ft.Colors.PRIMARY),
            ) if selected else None,
            on_click=lambda e, c=color: _pick_color(c),
        )

    def _size_dot(size: int) -> ft.Container:
        selected = size == int(current_size[0]) and not is_eraser[0]
        dim = size * 2
        return ft.Container(
            bgcolor=ft.Colors.ON_SURFACE if selected else ft.Colors.OUTLINE,
            width=dim,
            height=dim,
            border_radius=dim // 2,
            on_click=lambda e, s=size: _pick_size(s),
        )

    def _rebuild_toolbar(row_colors: ft.Row, row_sizes: ft.Row) -> None:
        row_colors.controls = [_color_dot(c) for c in PALETTE]
        row_sizes.controls = [_size_dot(s) for s in BRUSH_SIZES]
        row_colors.update()
        row_sizes.update()

    # We store the Row references so we can update them
    row_colors = ft.Row(spacing=8, wrap=False, scroll=ft.ScrollMode.AUTO)
    row_sizes = ft.Row(spacing=12, wrap=False)

    # Initial fill
    row_colors.controls = [_color_dot(c) for c in PALETTE]
    row_sizes.controls = [_size_dot(s) for s in BRUSH_SIZES]

    def _pick_color(color: str) -> None:
        current_color[0] = color
        is_eraser[0] = False
        _rebuild_toolbar(row_colors, row_sizes)

    def _pick_size(size: int) -> None:
        current_size[0] = float(size)
        _rebuild_toolbar(row_colors, row_sizes)

    def _toggle_eraser(e: ft.ControlEvent) -> None:
        is_eraser[0] = not is_eraser[0]
        eraser_btn.icon = ft.Icons.AUTO_FIX_OFF if is_eraser[0] else ft.Icons.AUTO_FIX_NORMAL
        eraser_btn.tooltip = "Drawing" if is_eraser[0] else "Eraser"
        eraser_btn.update()
        _rebuild_toolbar(row_colors, row_sizes)

    def _clear_canvas(e: ft.ControlEvent) -> None:
        canvas.shapes.clear()
        canvas.update()

    def _save_canvas(e: ft.ControlEvent) -> None:
        """Render the canvas shapes to a PNG via Pillow and call on_save."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return

        img = Image.new("RGB", (CANVAS_W, CANVAS_H), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)

        for shape in canvas.shapes:
            if isinstance(shape, cv.Line):
                paint = shape.paint
                color_str = paint.color if paint else "#000000"
                width = int(paint.stroke_width) if paint else 3
                # Convert hex to RGB tuple
                r_val, g_val, b_val = _hex_to_rgb(color_str)
                draw.line(
                    [(shape.x1, shape.y1), (shape.x2, shape.y2)],
                    fill=(r_val, g_val, b_val),
                    width=width,
                )

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        img.save(tmp.name)
        on_save(tmp.name)

    eraser_btn = ft.IconButton(
        icon=ft.Icons.AUTO_FIX_NORMAL,
        tooltip="Eraser",
        on_click=_toggle_eraser,
    )

    toolbar = ft.Column(
        [
            row_colors,
            ft.Row(
                [
                    ft.Text("Size:", size=12, color=ft.Colors.OUTLINE),
                    row_sizes,
                    ft.Container(expand=True),
                    eraser_btn,
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip="Clear canvas",
                        on_click=_clear_canvas,
                    ),
                    ft.FilledButton(
                        "Save",
                        icon=ft.Icons.SAVE_OUTLINED,
                        on_click=_save_canvas,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=8,
    )

    return ft.Column(
        [
            gesture,
            ft.Divider(height=1),
            toolbar,
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a CSS hex color string to an (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
