"""AI Chat screen — Phase 6.3.

Route: /chat

A full-screen conversational interface powered by GeminiService. Messages are
persisted in SQLite so history survives app restarts. The send action is run via
page.run_task so the UI never blocks during the network call.
"""
from __future__ import annotations

from datetime import datetime

import flet as ft

from services.gemini_service import GeminiError, GeminiService

# ── visual constants ─────────────────────────────────────────────────────────
_USER_BG    = ft.Colors.PRIMARY_CONTAINER
_MODEL_BG   = ft.Colors.SURFACE_CONTAINER
_BUBBLE_RADIUS = 16


def _build_bubble(role: str, content: str, timestamp: str) -> ft.Container:
    """Return a single chat bubble container."""
    is_user = role == "user"

    # Format timestamp for display
    try:
        ts = datetime.fromisoformat(timestamp).strftime("%H:%M")
    except (ValueError, TypeError):
        ts = ""

    bubble = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    content,
                    size=15,
                    selectable=True,
                    color=ft.Colors.ON_PRIMARY_CONTAINER if is_user
                          else ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Text(
                    ts,
                    size=11,
                    color=ft.Colors.ON_PRIMARY_CONTAINER if is_user
                          else ft.Colors.OUTLINE,
                ),
            ],
            spacing=2,
            tight=True,
        ),
        bgcolor=_USER_BG if is_user else _MODEL_BG,
        border_radius=ft.BorderRadius(
            top_left=_BUBBLE_RADIUS,
            top_right=_BUBBLE_RADIUS,
            bottom_left=4 if is_user else _BUBBLE_RADIUS,
            bottom_right=_BUBBLE_RADIUS if is_user else 4,
        ),
        padding=ft.Padding(left=14, top=10, right=14, bottom=10),
        # Max ~75 % of screen width — enforced by the Row layout below.
    )

    return ft.Row(
        [
            ft.Container(expand=True) if is_user else ft.Container(width=0),
            ft.Container(content=bubble, expand=3),
            ft.Container(width=0) if is_user else ft.Container(expand=True),
        ],
        spacing=0,
    )


def build(page: ft.Page) -> ft.View:
    """Build and return the chat view."""
    svc = GeminiService.instance()

    # ------------------------------------------------------------------ #
    # Message list
    # ------------------------------------------------------------------ #
    messages_list = ft.ListView(
        expand=True,
        spacing=10,
        padding=ft.Padding(left=12, top=12, right=12, bottom=12),
        auto_scroll=True,
    )

    def _load_history() -> None:
        messages_list.controls.clear()
        for msg in svc.get_history():
            messages_list.controls.append(
                _build_bubble(msg.role, msg.content, msg.timestamp)
            )

    _load_history()

    # ------------------------------------------------------------------ #
    # Input row
    # ------------------------------------------------------------------ #
    input_field = ft.TextField(
        hint_text="Ask anything about your finances\u2026",
        border_radius=24,
        border=ft.InputBorder.OUTLINE,
        multiline=True,
        min_lines=1,
        max_lines=4,
        expand=True,
        text_size=15,
        on_submit=lambda e: _send(e),
    )

    send_btn = ft.IconButton(
        ft.Icons.SEND_ROUNDED,
        icon_color=ft.Colors.PRIMARY,
        tooltip="Send",
        on_click=lambda e: _send(e),
    )

    loading_indicator = ft.Container(
        content=ft.ProgressRing(width=24, height=24, stroke_width=2),
        width=48,
        height=48,
        visible=False,
    )

    def _set_loading(state: bool) -> None:
        send_btn.visible = not state
        loading_indicator.visible = state
        input_field.disabled = state
        try:
            if send_btn.page:
                send_btn.update()
                loading_indicator.update()
                input_field.update()
        except RuntimeError:
            pass

    def _append_bubble(role: str, content: str, ts: str) -> None:
        messages_list.controls.append(_build_bubble(role, content, ts))
        try:
            if messages_list.page:
                messages_list.update()
        except RuntimeError:
            pass

    def _show_error(message: str) -> None:
        snack = ft.SnackBar(
            ft.Text(message),
            bgcolor=ft.Colors.ERROR_CONTAINER,
            duration=4000,
        )
        page.overlay.append(snack)
        snack.open = True
        try:
            page.update()
        except RuntimeError:
            pass

    async def _do_send(text: str) -> None:
        """Async task: call GeminiService and update the UI."""
        _set_loading(True)
        ts_user = datetime.now().isoformat(timespec="seconds")
        _append_bubble("user", text, ts_user)
        try:
            reply = svc.send_message(text)
            ts_model = datetime.now().isoformat(timespec="seconds")
            _append_bubble("model", reply, ts_model)
        except GeminiError as exc:
            _show_error(str(exc))
        except ValueError as exc:
            _show_error(str(exc))
        except Exception as exc:  # noqa: BLE001
            _show_error(f"Unexpected error: {exc}")
        finally:
            _set_loading(False)

    def _send(e: ft.ControlEvent) -> None:  # noqa: ARG001
        text = (input_field.value or "").strip()
        if not text:
            return
        if not svc.is_configured():
            _show_error("No API key configured. Tap the settings icon to add one.")
            return
        input_field.value = ""
        try:
            if input_field.page:
                input_field.update()
        except RuntimeError:
            pass
        page.run_task(_do_send, text)

    # ------------------------------------------------------------------ #
    # Empty state (shown when API key is missing and history is empty)
    # ------------------------------------------------------------------ #
    empty_state = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=64, color=ft.Colors.OUTLINE),
                ft.Text(
                    "AI Assistant",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    "Ask questions about budgeting, investments, or\n"
                    "financial planning. Your conversation is saved locally.",
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.FilledButton(
                    "Configure API Key",
                    on_click=lambda e: page.run_task(page.push_route, "/settings/api_key"),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        expand=True,
        padding=ft.Padding(left=32, top=0, right=32, bottom=0),
        alignment=ft.Alignment(0, 0),
        visible=not svc.is_configured() and not svc.get_history(),
    )

    # Hide empty state once history exists or key is configured
    if svc.is_configured() or svc.get_history():
        empty_state.visible = False

    # ------------------------------------------------------------------ #
    # Clear-history dialog
    # ------------------------------------------------------------------ #
    def _on_clear_dismiss(dlg: ft.AlertDialog):
        def handler(e: ft.ControlEvent) -> None:  # noqa: ARG001
            if dlg in page.overlay:
                page.overlay.remove(dlg)
            page.update()
        return handler

    def _close_dlg(dlg: ft.AlertDialog) -> None:
        dlg.open = False
        page.update()

    def _confirm_clear(e: ft.ControlEvent) -> None:  # noqa: ARG001
        dlg = ft.AlertDialog(
            title=ft.Text("Clear conversation?"),
            content=ft.Text("All messages will be deleted. This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close_dlg(dlg)),
                ft.FilledButton(
                    "Clear",
                    on_click=lambda e: _do_clear(dlg),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR),
                ),
            ],
        )
        dlg.on_dismiss = _on_clear_dismiss(dlg)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _do_clear(dlg: ft.AlertDialog) -> None:
        _close_dlg(dlg)
        svc.clear_history()
        messages_list.controls.clear()
        empty_state.visible = not svc.is_configured()
        try:
            if messages_list.page:
                messages_list.update()
                empty_state.update()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ #
    # View assembly
    # ------------------------------------------------------------------ #
    return ft.View(
        route="/chat",
        appbar=ft.AppBar(
            title=ft.Text("AI Assistant"),
            bgcolor=ft.Colors.SURFACE,
            actions=[
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE,
                    tooltip="Clear conversation",
                    on_click=_confirm_clear,
                ),
                ft.IconButton(
                    ft.Icons.SETTINGS_OUTLINED,
                    tooltip="API key settings",
                    on_click=lambda e: page.run_task(
                        page.push_route, "/settings/api_key"
                    ),
                ),
            ],
        ),
        controls=[
            ft.Column(
                [
                    ft.Stack(
                        [messages_list, empty_state],
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                input_field,
                                ft.Stack(
                                    [send_btn, loading_indicator],
                                    width=48,
                                    height=48,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        padding=ft.Padding(left=12, top=8, right=12, bottom=12),
                    ),
                ],
                spacing=0,
                expand=True,
            ),
        ],
        padding=0,
    )
