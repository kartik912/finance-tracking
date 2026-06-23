"""Bill Splits screen — Phase 2.6.

Shows a history of all bill splits (swipe to delete) and provides a
modal to create a new split with inline members and equal/custom share
calculation.

Layer rule: imports only from ``services`` — never from repositories directly.
"""
from __future__ import annotations

from datetime import date

import flet as ft

from models.split import Split


def build(page: ft.Page) -> ft.View:
    """Return the Bill Splits view."""
    from services.split_service import SplitService

    svc = SplitService.instance()
    today = date.today()

    splits_list = ft.ListView(
        expand=True,
        spacing=8,
        padding=ft.Padding(left=16, right=16, top=12, bottom=88),
    )

    # ── Delete ────────────────────────────────────────────────────────

    def _delete_split(sid: int) -> None:
        try:
            svc.delete_split(sid)
        except ValueError:
            pass
        _refresh()

    # ── Refresh list ──────────────────────────────────────────────────

    def _refresh() -> None:
        splits = svc.get_all_splits()
        splits_list.controls.clear()

        if not splits:
            splits_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.RECEIPT_LONG_OUTLINED,
                                size=56,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "No bill splits yet",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=14,
                            ),
                            ft.Text(
                                "Tap + to record a shared expense",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=12,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(top=64),
                )
            )
        else:
            for split in splits:
                members = svc.parse_members(split)
                member_chips = [
                    ft.Container(
                        content=ft.Text(m["name"], size=11),
                        bgcolor=ft.Colors.SECONDARY_CONTAINER,
                        border_radius=12,
                        padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                    )
                    for m in members
                ]
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Column(
                                            [
                                                ft.Text(
                                                    split.description,
                                                    size=15,
                                                    weight=ft.FontWeight.W_600,
                                                ),
                                                ft.Text(
                                                    split.date,
                                                    size=11,
                                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                                ),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(
                                                    f"\u20b9{split.total_amount:,.0f}",
                                                    size=15,
                                                    weight=ft.FontWeight.W_600,
                                                ),
                                                ft.Text(
                                                    f"My share: \u20b9{split.my_share:,.0f}",
                                                    size=11,
                                                    color=ft.Colors.GREEN_700,
                                                    weight=ft.FontWeight.W_500,
                                                ),
                                            ],
                                            spacing=2,
                                            horizontal_alignment=ft.CrossAxisAlignment.END,
                                        ),
                                    ],
                                ),
                                ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                                ft.Row(
                                    controls=member_chips,
                                    wrap=True,
                                    spacing=4,
                                    run_spacing=4,
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=ft.Padding(left=16, right=16, top=12, bottom=12),
                    ),
                    elevation=1,
                )
                splits_list.controls.append(
                    ft.Dismissible(
                        content=card,
                        dismiss_direction=ft.DismissDirection.HORIZONTAL,
                        on_dismiss=lambda e, sid=split.id: _delete_split(sid),
                        background=ft.Container(
                            bgcolor=ft.Colors.RED_400,
                            alignment=ft.Alignment(-1, 0),
                            padding=ft.Padding(left=20),
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
                                    ft.Text("Delete", color=ft.Colors.WHITE),
                                ],
                                spacing=6,
                            ),
                        ),
                        secondary_background=ft.Container(
                            bgcolor=ft.Colors.RED_400,
                            alignment=ft.Alignment(1, 0),
                            padding=ft.Padding(right=20),
                            content=ft.Row(
                                [
                                    ft.Text("Delete", color=ft.Colors.WHITE),
                                    ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
                                ],
                                spacing=6,
                            ),
                        ),
                    )
                )
        page.update()

    # ── Add split dialog ──────────────────────────────────────────────

    def _open_add_dialog() -> None:
        """Open the Add Bill Split modal."""
        # member_rows: list of (name_TextField, share_TextField) tuples
        member_rows: list[tuple[ft.TextField, ft.TextField]] = []
        members_col = ft.Column(spacing=8)
        _ready = [False]  # flag: True once the dialog is open

        desc_field = ft.TextField(
            label="Description (e.g. Dinner at Pizza Hut)",
            border_radius=8,
            autofocus=True,
            max_length=500,
        )
        total_field = ft.TextField(
            label="Total Amount",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("\u20b9 "),
            border_radius=8,
        )
        date_field = ft.TextField(
            label="Date",
            value=today.isoformat(),
            read_only=True,
            expand=True,
            border_radius=8,
        )
        my_share_field = ft.TextField(
            label="My Share",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("\u20b9 "),
            border_radius=8,
            hint_text="Tap 'Split Equally' to auto-fill",
        )
        error_text = ft.Text("", color=ft.Colors.ERROR, size=12)
        remaining_text = ft.Text("", size=12, weight=ft.FontWeight.W_500)

        def _parse_amount(raw: str) -> float:
            """Parse a raw string to float, return 0.0 on failure."""
            try:
                return float(raw.replace(",", "").replace("\u20b9", "").strip())
            except ValueError:
                return 0.0

        def _update_remaining(*_: object) -> None:
            """Recalculate and display how much of the total is still unassigned."""
            if not _ready[0]:
                return
            total = _parse_amount(total_field.value or "")
            my = _parse_amount(my_share_field.value or "")
            member_sum = sum(_parse_amount(share_tf.value or "") for _, share_tf in member_rows)
            assigned = round(my + member_sum, 2)
            remaining = round(total - assigned, 2)
            if total == 0:
                remaining_text.value = ""
                remaining_text.color = ft.Colors.ON_SURFACE_VARIANT
            elif abs(remaining) < 0.01:
                remaining_text.value = "\u2713 Shares balance exactly"
                remaining_text.color = ft.Colors.GREEN_700
            elif remaining > 0:
                remaining_text.value = f"\u20b9{remaining:,.2f} still unassigned"
                remaining_text.color = ft.Colors.ON_SURFACE_VARIANT
            else:
                remaining_text.value = f"\u20b9{abs(remaining):,.2f} over the total"
                remaining_text.color = ft.Colors.ERROR
            page.update()

        # Wire live updates to total and my_share fields
        total_field.on_change = _update_remaining
        my_share_field.on_change = _update_remaining

        # ── Member rows ───────────────────────────────────────────────

        def _rebuild_members() -> None:
            """Rebuild members_col from current member_rows state."""
            members_col.controls.clear()
            for i, (name_tf, share_tf) in enumerate(member_rows):
                idx = i
                members_col.controls.append(
                    ft.Row(
                        [
                            name_tf,
                            share_tf,
                            ft.IconButton(
                                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                tooltip="Remove",
                                on_click=lambda e, i=idx: _remove_member(i),
                            ),
                        ],
                        spacing=4,
                    )
                )
            if _ready[0]:
                page.update()

        def _add_member(e: ft.ControlEvent | None = None) -> None:
            name_tf = ft.TextField(
                label=f"Member {len(member_rows) + 1} name",
                expand=2,
                border_radius=8,
            )
            share_tf = ft.TextField(
                label="Share",
                keyboard_type=ft.KeyboardType.NUMBER,
                prefix=ft.Text("\u20b9"),
                expand=1,
                border_radius=8,
            )
            share_tf.on_change = _update_remaining
            member_rows.append((name_tf, share_tf))
            _rebuild_members()

        def _remove_member(idx: int) -> None:
            if 0 <= idx < len(member_rows):
                member_rows.pop(idx)
                _rebuild_members()

        def _split_equally(e: ft.ControlEvent) -> None:
            """Distribute total equally among all members + me."""
            raw = total_field.value.replace(",", "").replace("\u20b9", "").strip()
            try:
                total = float(raw)
            except ValueError:
                return
            n = len(member_rows) + 1  # other members + me
            if n > 0 and total > 0:
                share = round(total / n, 2)
                for _, share_tf in member_rows:
                    share_tf.value = str(share)
                my_share_field.value = str(share)
                page.update()

        # ── Date picker ───────────────────────────────────────────────

        def _on_date_change(e: ft.ControlEvent) -> None:
            val = e.control.value
            if val:
                iso = (
                    val.strftime("%Y-%m-%d")
                    if hasattr(val, "strftime")
                    else str(val)[:10]
                )
                date_field.value = iso
                page.update()

        def _pick_date(e: ft.ControlEvent) -> None:
            dp = ft.DatePicker(
                value=date.fromisoformat(date_field.value),
                on_change=_on_date_change,
            )
            page.overlay.append(dp)
            dp.open = True
            page.update()

        # ── Dialog close / save ───────────────────────────────────────

        def _close_dlg() -> None:
            dlg.open = False
            page.update()

        def _on_dismiss(e: ft.ControlEvent) -> None:
            if dlg in page.overlay:
                page.overlay.remove(dlg)
            page.update()

        def _save() -> None:
            error_text.value = ""

            def _clean_amount(raw: str) -> str:
                return raw.replace(",", "").replace("\u20b9", "").strip()

            members_data = []
            for name_tf, share_tf in member_rows:
                members_data.append(
                    {
                        "name": name_tf.value or "",
                        "share": _clean_amount(share_tf.value or "0") or "0",
                    }
                )
            # Convert share strings to float before service validation
            for m in members_data:
                try:
                    m["share"] = float(m["share"])
                except ValueError:
                    m["share"] = 0.0

            raw_total = _clean_amount(total_field.value or "")
            raw_my_share = _clean_amount(my_share_field.value or "")

            try:
                svc.add_split(
                    description=desc_field.value or "",
                    total_amount=float(raw_total) if raw_total else 0,
                    split_date=date_field.value,
                    members=members_data,
                    my_share=float(raw_my_share) if raw_my_share else 0,
                )
            except ValueError as exc:
                error_text.value = str(exc)
                page.update()
                return

            _close_dlg()
            _refresh()

        # Seed with one member before the dialog opens
        _add_member()

        dlg = ft.AlertDialog(
            title=ft.Text("Add Bill Split"),
            on_dismiss=_on_dismiss,
            content=ft.Container(
                content=ft.Column(
                    [
                        desc_field,
                        ft.Row(
                            [
                                date_field,
                                ft.IconButton(
                                    icon=ft.Icons.CALENDAR_MONTH,
                                    tooltip="Pick date",
                                    on_click=_pick_date,
                                ),
                            ],
                            spacing=4,
                        ),
                        total_field,
                        ft.Row(
                            [
                                ft.Text(
                                    "Members",
                                    size=13,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    expand=True,
                                ),
                                ft.TextButton(
                                    "Split Equally",
                                    icon=ft.Icons.BALANCE,
                                    on_click=_split_equally,
                                ),
                            ],
                        ),
                        members_col,
                        ft.TextButton(
                            "+ Add Member",
                            icon=ft.Icons.PERSON_ADD,
                            on_click=_add_member,
                        ),
                        my_share_field,
                        remaining_text,
                        error_text,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=420,
                height=480,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: _close_dlg()),
                ft.FilledButton("Save", on_click=lambda e: _save()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        _ready[0] = True
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Initial load ──────────────────────────────────────────────────
    _refresh()

    return ft.View(
        route="/splits",
        padding=0,
        appbar=ft.AppBar(
            title=ft.Text("Bill Splits"),
            center_title=False,
        ),
        controls=[splits_list],
        floating_action_button=ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=lambda e: _open_add_dialog(),
            tooltip="Add bill split",
        ),
    )
