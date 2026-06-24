"""API key configuration screen — Phase 6.2.

Route: /settings/api_key

Lets the user enter and save their Gemini API key. The key is stored in
config.json (git-ignored), never hardcoded.
"""
from __future__ import annotations

import flet as ft

from config.settings import load as load_config, save as save_config
from services.gemini_service import GeminiService


def build(page: ft.Page) -> ft.View:
    """Build and return the API key config view."""

    cfg = load_config()
    current_key = cfg.gemini_api_key or ""

    # ------------------------------------------------------------------ #
    # Controls
    # ------------------------------------------------------------------ #
    key_field = ft.TextField(
        label="Gemini API Key",
        value=current_key,
        password=True,
        can_reveal_password=True,
        hint_text="Paste your API key here",
        border_radius=12,
        expand=True,
    )

    status_text = ft.Text("", size=13, color=ft.Colors.GREEN_700)

    def _show_snack(message: str, error: bool = False) -> None:
        snack = ft.SnackBar(
            ft.Text(message),
            bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
        )
        page.overlay.append(snack)
        snack.open = True
        try:
            page.update()
        except RuntimeError:
            pass

    def _save(e: ft.ControlEvent) -> None:  # noqa: ARG001
        key = (key_field.value or "").strip()
        cfg = load_config()
        cfg.gemini_api_key = key
        try:
            save_config(cfg)
            GeminiService.reset()   # force session rebuild with new key
            status_text.value = "Key saved \u2713"
            status_text.color = ft.Colors.GREEN_700
            _show_snack("API key saved successfully.")
        except Exception as exc:  # noqa: BLE001
            status_text.value = f"Error: {exc}"
            status_text.color = ft.Colors.ERROR
            _show_snack(f"Failed to save: {exc}", error=True)
        try:
            if status_text.page:
                status_text.update()
        except RuntimeError:
            pass

    def _back(e: ft.ControlEvent) -> None:  # noqa: ARG001
        if len(page.views) > 1:
            page.views.pop()
            top = page.views[-1]
            page.run_task(page.push_route, top.route)
        else:
            page.run_task(page.push_route, "/chat")

    # ------------------------------------------------------------------ #
    # View
    # ------------------------------------------------------------------ #
    return ft.View(
        route="/settings/api_key",
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK,
                on_click=_back,
                tooltip="Back",
            ),
            title=ft.Text("AI Settings"),
            bgcolor=ft.Colors.SURFACE,
        ),
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Gemini API Key",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "The AI assistant uses Google Gemini. Your key is stored "
                            "locally on this device and never sent anywhere except "
                            "directly to Google\u2019s API.",
                            size=14,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.TextButton(
                            "Get a free API key at aistudio.google.com",
                            on_click=lambda e: None,  # deep-link handled by OS on Android
                            style=ft.ButtonStyle(
                                color=ft.Colors.PRIMARY,
                            ),
                        ),
                        ft.Divider(height=8),
                        ft.Row([key_field], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Row(
                            [
                                ft.FilledButton("Save", on_click=_save),
                                ft.Container(width=8),
                                status_text,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=8),
                        ft.Text(
                            "Your key is stored in config.json on this device.",
                            size=12,
                            color=ft.Colors.OUTLINE,
                        ),
                    ],
                    spacing=12,
                ),
                padding=ft.Padding(left=20, top=20, right=20, bottom=20),
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        padding=0,
    )
