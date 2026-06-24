"""App entry point.

Responsibilities
----------------
1. Initialise the database and cache service.
2. Apply the global Material Design 3 theme.
3. Render the 5-tab ``NavigationBar``.
4. Route between screens via ``page.push_route(route)``.

Run locally::

    flet run main.py

Build APK::

    flet build apk
"""
from __future__ import annotations

import os

import flet as ft

from config.database import create_tables, init_db, run_migration
from config.settings import load as load_config
from services.cache_service import CacheService


# ---------------------------------------------------------------------------
# Route → screen builder mapping
# ---------------------------------------------------------------------------
# Each screen module must expose a ``build(page) -> ft.View`` function.
# Screens are imported lazily inside the route handler to keep startup fast.

ROUTES: dict[str, str] = {
    "/":                   "screens.dashboard",
    "/finance":            "screens.finance_tracker",
    "/investments":        "screens.investments",
    "/goals":              "screens.goals",
    "/notes":              "screens.notebooks",
    "/splits":             "screens.bill_splits",
    "/chat":               "screens.chat",
    "/settings/api_key":   "screens.api_key_config",
}

# Tab index → route (matches NavigationBar destination order)
TAB_ROUTES = ["/", "/finance", "/investments", "/goals", "/notes", "/chat"]

# Module-level reference to the NavigationBar, set in main() and read by
# _route_change(). Required because page.navigation_bar reads from views[0]
# in Flet 0.85.x, which raises if the views list has been cleared.
_nav_bar: ft.NavigationBar | None = None


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

def _build_theme() -> ft.Theme:
    """Return the global Material Design 3 light theme."""
    return ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        use_material3=True,
    )


def _build_dark_theme() -> ft.Theme:
    """Return the global Material Design 3 dark theme."""
    return ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        use_material3=True,
    )


# ---------------------------------------------------------------------------
# Navigation bar
# ---------------------------------------------------------------------------

def _build_nav_bar(page: ft.Page) -> ft.NavigationBar:
    """Build the 5-tab bottom NavigationBar."""

    async def on_change(e: ft.ControlEvent) -> None:
        await page.push_route(TAB_ROUTES[int(e.data)])

    return ft.NavigationBar(
        selected_index=0,
        on_change=on_change,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD,
                label="Dashboard",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                label="Finance",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.TRENDING_UP_OUTLINED,
                selected_icon=ft.Icons.TRENDING_UP,
                label="Investments",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.FLAG_OUTLINED,
                selected_icon=ft.Icons.FLAG,
                label="Goals",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.BOOK_OUTLINED,
                selected_icon=ft.Icons.BOOK,
                label="Notes",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SMART_TOY_OUTLINED,
                selected_icon=ft.Icons.SMART_TOY,
                label="AI Chat",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------

def _route_change(e: ft.RouteChangeEvent) -> None:
    """Called by Flet whenever ``page.push_route(route)`` is invoked."""
    page: ft.Page = e.page
    route: str = e.route

    # Sync the NavigationBar selection using the stored reference.
    # Do NOT access page.navigation_bar here — in Flet 0.85.x it reads from
    # views[0] and raises RuntimeError if the views list has been cleared.
    if route in TAB_ROUTES and _nav_bar is not None:
        _nav_bar.selected_index = TAB_ROUTES.index(route)

    # Lazy-import the screen module and call its build() function
    import importlib
    view: ft.View | None = None

    # ----- Parameterised routes ----------------------------------------
    parts = route.split("/")  # e.g. ["", "notes_list", "3"] or ["", "note_editor", "3", "7", "text"]

    if len(parts) >= 3 and parts[1] == "notes_list":
        try:
            notebook_id = int(parts[2])
        except (ValueError, IndexError):
            notebook_id = 0
        module = importlib.import_module("screens.notes_list")
        view = module.build(page, notebook_id)

    elif len(parts) >= 4 and parts[1] == "note_editor":
        try:
            notebook_id = int(parts[2])
            note_id = int(parts[3])
        except (ValueError, IndexError):
            notebook_id = note_id = 0
        module = importlib.import_module("screens.note_editor")
        view = module.build(page, notebook_id, note_id)

    # ----- Static routes -----------------------------------------------
    else:
        module_path = ROUTES.get(route)
        if module_path:
            module = importlib.import_module(module_path)
            view = module.build(page)

    if view is None:
        # 404 fallback
        view = ft.View(
            route=route,
            controls=[
                ft.AppBar(title=ft.Text("Not Found")),
                ft.Text(f"No screen registered for route: {route}"),
            ],
        )

    view.navigation_bar = _nav_bar  # use stored ref, not page.navigation_bar
    page.views.clear()
    page.views.append(view)
    page.update()


async def _view_pop(e: ft.ViewPopEvent) -> None:
    """Handle Android back button — pop view or show exit dialog."""
    page: ft.Page = e.page
    if len(page.views) > 1:
        page.views.pop()
        top = page.views[-1]
        await page.push_route(top.route)
    else:
        await page.push_route("/")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main(page: ft.Page) -> None:
    """Flet app entry point."""
    # ---- Load config -------------------------------------------------------
    cfg = load_config()

    # ---- Initialise database -----------------------------------------------
    # page.app_data_dir is available on Android/iOS at runtime.
    # On desktop (dev mode) it is not set, so fall back to the local database/ folder.
    app_data = getattr(page, "app_data_dir", None)
    db_path = os.path.join(app_data if app_data else "database", "finance.db")
    init_db(db_path)
    create_tables()
    run_migration(3)  # apply any pending schema migrations

    # ---- Initialise cache service ------------------------------------------
    cache = CacheService.instance()
    cache.register_invalidators()

    # ---- Page settings -----------------------------------------------------
    page.title = "Finance Tracker"
    page.theme = _build_theme()
    page.dark_theme = _build_dark_theme()
    page.theme_mode = (
        ft.ThemeMode.DARK   if cfg.theme_mode == "dark"
        else ft.ThemeMode.LIGHT if cfg.theme_mode == "light"
        else ft.ThemeMode.SYSTEM
    )
    page.padding = 0

    # ---- Navigation bar ----------------------------------------------------
    # Store in module-level var so _route_change can reference it without
    # reading from page.navigation_bar (which requires a non-empty views list).
    global _nav_bar
    _nav_bar = _build_nav_bar(page)
    page.navigation_bar = _nav_bar

    # ---- Routing -----------------------------------------------------------
    page.on_route_change = _route_change
    page.on_view_pop = _view_pop

    # ---- Navigate to default route -----------------------------------------
    await page.push_route(page.route or "/")


if __name__ == "__main__":
    ft.run(main)
